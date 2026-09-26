import os
import cv2
import json
import sys
import uuid
import torch
import ollama
import numpy as np
from pathlib import Path
from typing import Optional, Dict, Any, List
from ultralytics import YOLO
from sqlalchemy.orm import Session
from concurrent.futures import ThreadPoolExecutor, as_completed

# Initialize NumPy compat
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import src.numpy_compat

from src.matching import match_book_entity, match_ocr_query
from src.hybrid import hybrid_recommend_shelf

YOLO_MODEL_PATH = r"c:\Users\anshu\Documents\codes\ML\BookRecomendation\runs\detect\train\weights\best.pt"
UPLOADS_DIR = r"c:\Users\anshu\Documents\codes\ML\BookRecomendation\backend\uploads"

os.makedirs(UPLOADS_DIR, exist_ok=True)

# Global caches
_yolo_model = None
_ollama_model_name: Optional[str] = None
_ollama_checked = False
_ollama_is_online = False

def get_yolo_model():
    global _yolo_model
    if _yolo_model is None:
        print("Loading YOLOv8 book spine detector...")
        _yolo_model = YOLO(YOLO_MODEL_PATH)
        if torch.cuda.is_available():
            _yolo_model.to("cuda")
    return _yolo_model

def get_active_ollama_model() -> Optional[str]:
    """
    Detect running Ollama instance and auto-select best available multimodal vision model.
    Checks environment variable OLLAMA_MODEL first, then local models, then falls back gracefully.
    """
    global _ollama_model_name, _ollama_checked, _ollama_is_online
    if _ollama_checked:
        return _ollama_model_name

    _ollama_checked = True
    
    # 1. Environment variable override
    env_override = os.getenv("OLLAMA_MODEL")
    if env_override:
        _ollama_model_name = env_override
        _ollama_is_online = True
        print(f"Using environment OLLAMA_MODEL: {_ollama_model_name}")
        return _ollama_model_name

    # 2. Query Ollama tags
    try:
        model_list = ollama.list()
        available = []
        if hasattr(model_list, "models"):
            available = [m.model for m in model_list.models]
        elif isinstance(model_list, dict):
            available = [m.get("model", m.get("name", "")) for m in model_list.get("models", [])]

        # Prioritize fast local vision models (exclude embedding or cloud models)
        preference = [
            "gemma3:4b",
            "gemma3",
            "llava",
            "llama3.2-vision",
            "minicpm-v",
            "gemma2"
        ]

        # Filter candidates: exclude embedding models and cloud stubs
        filtered_available = [
            m for m in available 
            if "embed" not in m.lower() and "cloud" not in m.lower()
        ]

        for pref in preference:
            for av in filtered_available:
                if av == pref or av.startswith(pref.split(":")[0]):
                    _ollama_model_name = av
                    _ollama_is_online = True
                    print(f"Auto-detected Ollama vision model: {_ollama_model_name}")
                    return _ollama_model_name

        if filtered_available:
            _ollama_model_name = filtered_available[0]
            _ollama_is_online = True
            print(f"Selected available Ollama model: {_ollama_model_name}")
            return _ollama_model_name

    except Exception as e:
        print(f"Ollama is not reachable ({e}). Running in Fast-Path OCR + FAISS vector mode.")
        _ollama_model_name = None
        _ollama_is_online = False

    return _ollama_model_name

def identify_book_with_gemma(image_path: str, ocr_text: str) -> str:
    """
    Query Ollama vision model to identify book title and author from spine image and OCR.
    """
    model_name = get_active_ollama_model()
    if not model_name:
        return "{}"

    ocr_section = f"OCR text extracted from spine:\n{ocr_text}\n" if ocr_text and ocr_text.strip() else "No OCR text extracted.\n"

    prompt = f"""You are an expert book identifier looking at a single cropped book spine photo.
{ocr_section}
Identify the exact book title and author.
Return ONLY valid JSON (no extra markdown or prose):
{{"title":"","author":"","confidence":0}}
If you cannot identify the book, return {{"title":"UNKNOWN","author":"UNKNOWN","confidence":0}}
"""
    try:
        response = ollama.chat(
            model=model_name,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                    "images": [image_path]
                }
            ],
            options={"temperature": 0.1}
        )
        return response["message"]["content"]
    except Exception as e:
        print(f"Ollama vision call error with {model_name}: {e}")
        return "{}"

def parse_gemma_response(text: str) -> dict:
    try:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(text[start:end])
    except Exception as e:
        pass
    return {
        "title": "UNKNOWN",
        "author": "UNKNOWN",
        "confidence": 0
    }

def process_shelf_scan(image_path: str, user_id: int, db: Session) -> dict:
    """
    Enhanced ShelfScan Pipeline:
    1. YOLOv8 locates spines.
    2. PaddleOCR extracts text in isolated subprocess.
    3. Fast-Path matching: Resolves clean OCR text directly in milliseconds.
    4. Ambiguous / unread spines are sent to Ollama multimodal vision model.
    5. Fallback: If Ollama fails, fall back to best-effort OCR text matching.
    6. Recommendation ranking & Heatmap generation.
    """
    yolo = get_yolo_model()

    orig_img = cv2.imread(image_path)
    if orig_img is None:
        raise ValueError(f"Could not load image at {image_path}")

    h_orig, w_orig = orig_img.shape[:2]

    # Step 1: Detect spines
    yolo_device = 0 if torch.cuda.is_available() else "cpu"
    print(f"Running spine detection (YOLO device: {yolo_device}) on {image_path}...")
    results = yolo(image_path, device=yolo_device)
    boxes = results[0].boxes

    crop_info = []
    print(f"Detected {len(boxes)} book spines. Cropping spines...")
    for idx, box in enumerate(boxes.xyxy.cpu().numpy()):
        x1, y1, x2, y2 = map(int, box)
        w_box = x2 - x1
        h_box = y2 - y1
        if h_box < 75 or w_box < 18:
            continue

        crop = orig_img[y1:y2, x1:x2]
        temp_crop_filename = f"crop_{uuid.uuid4().hex}.jpg"
        temp_crop_path = os.path.join(UPLOADS_DIR, temp_crop_filename)
        cv2.imwrite(temp_crop_path, crop)

        crop_info.append({
            "box_idx": idx,
            "box": [x1, y1, x2, y2],
            "temp_path": temp_crop_path,
            "ocr_text": "",
            "ocr_conf": 0.0
        })

    # Step 2: Batch PaddleOCR on CPU in subprocess
    ocr_results = {}
    if crop_info:
        import subprocess

        crop_paths = [c["temp_path"] for c in crop_info]
        input_json_path = os.path.join(UPLOADS_DIR, f"ocr_in_{uuid.uuid4().hex}.json")
        output_json_path = os.path.join(UPLOADS_DIR, f"ocr_out_{uuid.uuid4().hex}.json")

        with open(input_json_path, "w", encoding="utf-8") as f:
            json.dump(crop_paths, f)

        python_exe = sys.executable
        script_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src", "ocr_subprocess.py")
        cmd = [python_exe, script_path, input_json_path, output_json_path]

        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if res.returncode == 0 and os.path.exists(output_json_path):
                with open(output_json_path, "r", encoding="utf-8") as f:
                    ocr_results = json.load(f)
                print(f"OCR Subprocess completed: {len(ocr_results)} crops processed.")
        except Exception as e:
            print(f"OCR execution warning: {e}")
        finally:
            if os.path.exists(input_json_path):
                os.remove(input_json_path)
            if os.path.exists(output_json_path):
                os.remove(output_json_path)

    # Attach OCR text to crop objects
    for c in crop_info:
        item = ocr_results.get(c["temp_path"], {"text": "", "confidence": 0.0})
        c["ocr_text"] = item.get("text", "")
        c["ocr_conf"] = item.get("confidence", 0.0)

    # Step 3: Fast-Path OCR Database Matching
    detected_items = []
    matched_isbns = []
    unresolved_crops = []

    from backend.database import SessionLocal, Book
    db_session = SessionLocal()

    print("Running Fast-Path OCR database matching...")
    for c in crop_info:
        ocr_text = c["ocr_text"].strip()
        matched = False

        if len(ocr_text) >= 4:
            fast_match = match_book_entity(raw_query=ocr_text, db=db_session, fuzzy_threshold=80.0)
            if fast_match and fast_match.get("score", 0) >= 80.0:
                bk = fast_match["book"]
                detected_items.append({
                    "box_idx": c["box_idx"],
                    "box": c["box"],
                    "ocr_text": ocr_text,
                    "gemma_title": bk.title,
                    "gemma_author": bk.author,
                    "isbn": bk.book_id,
                    "title": bk.title,
                    "author": bk.author,
                    "match_stage": f"Fast-Path: {fast_match['stage']}",
                    "match_score": fast_match["score"]
                })
                matched_isbns.append(bk.book_id)
                matched = True

        if not matched:
            unresolved_crops.append(c)

    db_session.close()
    print(f"Fast-Path matched {len(detected_items)} books directly. {len(unresolved_crops)} crops sent for disambiguation.")

    # Step 4: Disambiguation with Ollama Vision + Fallback
    ollama_model = get_active_ollama_model()

    def process_unresolved(c, use_llm=True):
        import re as _re
        import hashlib as _hashlib
        temp_crop_path = c["temp_path"]
        x1, y1, x2, y2 = c["box"]
        idx = c["box_idx"]
        ocr_text = c["ocr_text"].strip()

        thread_db = SessionLocal()
        gemma_title = "UNKNOWN"
        gemma_author = "UNKNOWN"
        gemma_conf = 0

        try:
            # 1. Try Ollama if online and use_llm is True
            if use_llm and ollama_model:
                raw_gemma = identify_book_with_gemma(temp_crop_path, ocr_text)
                gemma_data = parse_gemma_response(raw_gemma)
                gemma_title = gemma_data.get("title", "").strip()
                gemma_author = gemma_data.get("author", "").strip()
                gemma_conf = gemma_data.get("confidence", 0)

            # 2. Check if Gemma resolved a title
            if gemma_title and gemma_title != "UNKNOWN":
                match_res = match_book_entity(title=gemma_title, author=gemma_author, db=thread_db)
                if match_res:
                    bk = match_res["book"]
                    return {
                        "box_idx": idx,
                        "box": [x1, y1, x2, y2],
                        "ocr_text": ocr_text,
                        "gemma_title": gemma_title,
                        "gemma_author": gemma_author,
                        "isbn": bk.book_id,
                        "title": bk.title,
                        "author": bk.author,
                        "match_stage": match_res["stage"],
                        "match_score": match_res["score"]
                    }
                else:
                    # Gemma Auto-Insert
                    norm_t = _re.sub(r"[^a-z0-9\s]", "", gemma_title.lower()).strip()
                    norm_a = _re.sub(r"[^a-z0-9\s]", "", gemma_author.lower()).strip() if gemma_author != "UNKNOWN" else ""
                    book_id = "gemma_" + _hashlib.md5(f"{norm_t}_{norm_a}".encode()).hexdigest()[:12]

                    existing = thread_db.query(Book).filter(Book.book_id == book_id).first()
                    if not existing:
                        try:
                            # Auto-enrich modern book with OpenLibrary metadata (description, genres, cover)
                            from src.enrichment import fetch_openlibrary_metadata
                            meta = fetch_openlibrary_metadata(gemma_title, gemma_author)
                            
                            new_book = Book(
                                book_id=book_id,
                                title=gemma_title,
                                author=gemma_author if gemma_author != "UNKNOWN" else "",
                                description=meta.get("description", ""),
                                genres=meta.get("genres", ""),
                                image_url=meta.get("cover_url", ""),
                                normalized_title=norm_t,
                                normalized_author=norm_a
                            )
                            thread_db.add(new_book)
                            thread_db.commit()
                        except Exception:
                            thread_db.rollback()

                    return {
                        "box_idx": idx,
                        "box": [x1, y1, x2, y2],
                        "ocr_text": ocr_text,
                        "gemma_title": gemma_title,
                        "gemma_author": gemma_author,
                        "isbn": book_id,
                        "title": gemma_title,
                        "author": gemma_author if gemma_author != "UNKNOWN" else None,
                        "match_stage": "Stage 5: Gemma Auto-Insert",
                        "match_score": float(gemma_conf or 70.0)
                    }

            # 3. Fallback: Match raw OCR text in database
            if ocr_text and len(ocr_text) >= 4:
                fallback_res = match_book_entity(raw_query=ocr_text, db=thread_db, fuzzy_threshold=68.0)
                if fallback_res:
                    bk = fallback_res["book"]
                    return {
                        "box_idx": idx,
                        "box": [x1, y1, x2, y2],
                        "ocr_text": ocr_text,
                        "gemma_title": bk.title,
                        "gemma_author": bk.author,
                        "isbn": bk.book_id,
                        "title": bk.title,
                        "author": bk.author,
                        "match_stage": f"OCR Fallback ({fallback_res['stage']})",
                        "match_score": fallback_res["score"]
                    }

            # 4. Unmatched spine
            display_label = ocr_text[:20] if ocr_text else "Unmatched"
            return {
                "box_idx": idx,
                "box": [x1, y1, x2, y2],
                "ocr_text": ocr_text,
                "gemma_title": display_label,
                "gemma_author": None,
                "isbn": None,
                "title": None,
                "author": None,
                "match_stage": "None",
                "match_score": 0
            }

        except Exception as e:
            print(f"Crop {idx} resolution error: {e}")
            return {
                "box_idx": idx,
                "box": [x1, y1, x2, y2],
                "ocr_text": ocr_text,
                "gemma_title": "ERROR",
                "gemma_author": None,
                "isbn": None,
                "title": None,
                "author": None,
                "match_stage": "None",
                "match_score": 0
            }
        finally:
            thread_db.close()
            if os.path.exists(temp_crop_path):
                try:
                    os.remove(temp_crop_path)
                except Exception:
                    pass

    # Process unresolved crops with ThreadPool
    if unresolved_crops:
        # Sort unresolved crops: prioritize those with extracted OCR text and confidence
        sorted_unresolved = sorted(
            unresolved_crops,
            key=lambda c: (len(c.get("ocr_text", "").strip()) >= 3, c.get("ocr_conf", 0.0)),
            reverse=True
        )

        # Cap Ollama vision calls to 12 top crops to ensure fast response latency
        to_process = sorted_unresolved[:12]
        remaining = sorted_unresolved[12:]

        if ollama_model:
            print(f"Submitting {len(to_process)} crops to Ollama vision ({ollama_model}). {len(remaining)} crops routed to fast OCR fallback.")
            with ThreadPoolExecutor(max_workers=3) as executor:
                futures = {executor.submit(process_unresolved, c, True): c for c in to_process}
                for fut in as_completed(futures):
                    res = fut.result()
                    if res:
                        detected_items.append(res)
                        if res.get("isbn"):
                            matched_isbns.append(res["isbn"])
        else:
            remaining = sorted_unresolved

        # For remaining crops, do fast database/OCR fallback (use_llm=False)
        for c in remaining:
            res = process_unresolved(c, use_llm=False)
            if res:
                detected_items.append(res)
                if res.get("isbn"):
                    matched_isbns.append(res["isbn"])

    # Step 5: Recommendations
    recs = []
    unique_isbns = list(set([isbn for isbn in matched_isbns if isbn]))
    if unique_isbns:
        recs = hybrid_recommend_shelf(user_id, unique_isbns, db)

    buy_score_map = {r["book_id"]: r["buy_score"] for r in recs}
    already_read_map = {r["book_id"]: r["already_read"] for r in recs}

    # Step 6: Generate Heatmap
    heatmap_img = orig_img.copy()

    for item in detected_items:
        x1, y1, x2, y2 = item["box"]
        isbn = item["isbn"]

        if isbn is None:
            color = (128, 128, 128)
            label = item["gemma_title"][:14] if item.get("gemma_title") else "Unmatched"
        elif already_read_map.get(isbn, False):
            color = (255, 120, 0)
            label = "Read"
        else:
            buy_score = buy_score_map.get(isbn, 0)
            if buy_score >= 80:
                color = (0, 200, 0)
                label = f"{buy_score}% Fit"
            elif buy_score >= 50:
                color = (0, 220, 220)
                label = f"{buy_score}% Maybe"
            else:
                color = (0, 0, 220)
                label = f"{buy_score}% Low"

        cv2.rectangle(heatmap_img, (x1, y1), (x2, y2), color, 3)
        label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)[0]
        y_text = max(y1 - 8, label_size[1] + 10)
        cv2.putText(heatmap_img, label, (x1, y_text), cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1, cv2.LINE_AA)

    heatmap_filename = f"heatmap_{uuid.uuid4().hex}.jpg"
    heatmap_path = os.path.join(UPLOADS_DIR, heatmap_filename)
    cv2.imwrite(heatmap_path, heatmap_img)

    return {
        "detected_books": detected_items,
        "recommendations": recs,
        "heatmap_image_url": f"/uploads/{heatmap_filename}",
        "heatmap_local_path": heatmap_path
    }
