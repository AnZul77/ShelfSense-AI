import os
import cv2
import json
import sys
import uuid
import torch
import ollama
import numpy as np
from pathlib import Path
from ultralytics import YOLO
from sqlalchemy.orm import Session
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.matching import match_ocr_query
from src.hybrid import hybrid_recommend_shelf

YOLO_MODEL_PATH = r"c:\Users\anshu\Documents\codes\ML\BookRecomendation\runs\detect\train\weights\best.pt"
UPLOADS_DIR = r"c:\Users\anshu\Documents\codes\ML\BookRecomendation\backend\uploads"

os.makedirs(UPLOADS_DIR, exist_ok=True)

# Global caches
_yolo_model = None

def get_yolo_model():
    global _yolo_model
    if _yolo_model is None:
        print("Loading YOLOv8 book spine detector...")
        _yolo_model = YOLO(YOLO_MODEL_PATH)
        # Move YOLO model to CUDA if available
        if torch.cuda.is_available():
            _yolo_model.to("cuda")
    return _yolo_model

def identify_book_with_gemma(image_path: str, ocr_text: str) -> str:
    """
    Uses Ollama's local gemma4:31b-cloud multimodal LLM to identify the book
    based on the crop image and OCR text.
    """
    prompt = f"""
You are identifying a book from a bookshelf.

OCR text:

{ocr_text}

The OCR may contain severe mistakes.

Use BOTH:
1. The image
2. The OCR text

Most books belong to fantasy or science fiction authors.

Examples include:
Brandon Sanderson
Terry Pratchett
Anthony Ryan
Peter F. Hamilton
John Gwynne
Guy Gavriel Kay
Jay Kristoff
Andrzej Sapkowski
Ann Leckie
Alastair Reynolds

First reconstruct the likely spine text.

Then identify the exact book.

Return ONLY JSON:

{{
"title":"",
"author":"",
"corrected_spine_text":"",
"reasoning":"",
"confidence":0
}}
"""
    try:
        response = ollama.chat(
            model="gemma4:31b-cloud",
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                    "images": [image_path]
                }
            ]
        )
        return response["message"]["content"]
    except Exception as e:
        print(f"Ollama/Gemma error: {e}")
        return "{}"

def parse_gemma_response(text: str) -> dict:
    try:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(text[start:end])
    except Exception as e:
        print(f"Error parsing Gemma JSON: {e}")
    return {
        "title": "UNKNOWN",
        "author": "UNKNOWN",
        "confidence": 0
    }

def process_shelf_scan(image_path: str, user_id: int, db: Session) -> dict:
    """
    Full CV Pipeline:
    1. YOLOv8 locates book spines (GPU/CUDA accelerated).
    2. Crops are processed in a separate batch process with PaddleOCR-GPU on CUDA.
    3. Multimodal Gemma identifies the top 20 crops by OCR confidence in parallel.
       Spines with very short/no OCR text are skipped to optimize performance.
    4. Database match matches the Gemma output (title/author).
    5. Heatmap overlay draws recommendation-colored bounding boxes.
    """
    yolo = get_yolo_model()
    
    # Load original image
    orig_img = cv2.imread(image_path)
    if orig_img is None:
        raise ValueError(f"Could not load image at {image_path}")
        
    h_orig, w_orig = orig_img.shape[:2]
    
    # Run YOLO detection (CUDA accelerated if GPU is available)
    yolo_device = 0 if torch.cuda.is_available() else "cpu"
    print(f"Running spine detection (YOLO device: {yolo_device}) on {image_path}...")
    results = yolo(image_path, device=yolo_device)
    boxes = results[0].boxes
    
    detected_items = []
    matched_isbns = []
    
    # Step 1: Crop spines and save to temporary files
    crop_info = []
    print(f"Detected {len(boxes)} book spines. Cropping spines for batch OCR...")
    for idx, box in enumerate(boxes.xyxy.cpu().numpy()):
        x1, y1, x2, y2 = map(int, box)
        
        # Enforce minimum spine size constraints
        w_box = x2 - x1
        h_box = y2 - y1
        if h_box < 80 or w_box < 20:
            continue
            
        crop = orig_img[y1:y2, x1:x2]
        
        # Save temporary spine crop to disk for Gemma and PaddleOCR subprocess
        temp_crop_filename = f"crop_{uuid.uuid4().hex}.jpg"
        temp_crop_path = os.path.join(UPLOADS_DIR, temp_crop_filename)
        cv2.imwrite(temp_crop_path, crop)
        
        crop_info.append({
            "box_idx": idx,
            "box": [x1, y1, x2, y2],
            "temp_path": temp_crop_path
        })
        
    # Step 2: Run batch OCR using a separate process (avoids PyTorch/Paddle DLL and namespace clashes)
    ocr_results = {}
    if crop_info:
        import subprocess
        
        crop_paths = [c["temp_path"] for c in crop_info]
        
        # Write paths to temporary JSON input file
        input_json_name = f"ocr_in_{uuid.uuid4().hex}.json"
        input_json_path = os.path.join(UPLOADS_DIR, input_json_name)
        with open(input_json_path, "w", encoding="utf-8") as f:
            json.dump(crop_paths, f)
            
        output_json_name = f"ocr_out_{uuid.uuid4().hex}.json"
        output_json_path = os.path.join(UPLOADS_DIR, output_json_name)
        
        python_exe = sys.executable  # Use virtualenv Python interpreter
        # Resolve path to ocr_subprocess.py
        script_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src", "ocr_subprocess.py")
        
        cmd = [python_exe, script_path, input_json_path, output_json_path]
        print(f"Launching PaddlePaddle OCR Subprocess: {' '.join(cmd)}")
        
        try:
            # Run with a 180-second timeout for large batches
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
            if res.returncode == 0 and os.path.exists(output_json_path):
                with open(output_json_path, "r", encoding="utf-8") as f:
                    ocr_results = json.load(f)
                print(f"OCR Subprocess completed successfully. Processed {len(ocr_results)} crops.")
            else:
                print(f"OCR Subprocess failed with return code {res.returncode}. Stderr: {res.stderr}")
        except subprocess.TimeoutExpired:
            print("OCR Subprocess timed out after 180 seconds.")
        except Exception as e:
            print(f"Error executing OCR Subprocess: {e}")
        finally:
            # Clean up JSON files
            if os.path.exists(input_json_path):
                os.remove(input_json_path)
            if os.path.exists(output_json_path):
                os.remove(output_json_path)
                
    # Step 3: Run Gemma multimodal LLM and search the database
    # Sort crops by OCR confidence to identify the most legible spines first
    for c in crop_info:
        ocr_item = ocr_results.get(c["temp_path"], {"text": "", "confidence": 0.0})
        c["ocr_text"] = ocr_item.get("text", "")
        c["ocr_conf"] = ocr_item.get("confidence", 0.0)
        
    # Filter out crops with short/blank OCR text
    valid_crops = [c for c in crop_info if c["ocr_text"] and len(c["ocr_text"].strip()) >= 3]
    
    # Sort valid crops by OCR confidence in descending order
    valid_crops.sort(key=lambda x: x["ocr_conf"], reverse=True)
    
    # Process top 20 most legible crops to maintain fast execution and avoid overloading local Ollama
    max_crops_to_process = 20
    crops_to_process = valid_crops[:max_crops_to_process]
    crops_to_skip = valid_crops[max_crops_to_process:]
    
    # Clean up and return UNKNOWN for skipped crops (retaining bounding boxes for heatmap rendering)
    for c in crops_to_skip:
        temp_crop_path = c["temp_path"]
        if os.path.exists(temp_crop_path):
            os.remove(temp_crop_path)
        detected_items.append({
            "box_idx": c["box_idx"],
            "box": c["box"],
            "ocr_text": c["ocr_text"],
            "gemma_title": "UNKNOWN",
            "gemma_author": "UNKNOWN",
            "isbn": None,
            "title": None,
            "author": None,
            "match_stage": "None",
            "match_score": 0
        })
        
    # Also clean up and return UNKNOWN for crops that had no valid OCR text
    invalid_crops = [c for c in crop_info if not c["ocr_text"] or len(c["ocr_text"].strip()) < 3]
    for c in invalid_crops:
        temp_crop_path = c["temp_path"]
        if os.path.exists(temp_crop_path):
            os.remove(temp_crop_path)
        detected_items.append({
            "box_idx": c["box_idx"],
            "box": c["box"],
            "ocr_text": c["ocr_text"],
            "gemma_title": "UNKNOWN",
            "gemma_author": "UNKNOWN",
            "isbn": None,
            "title": None,
            "author": None,
            "match_stage": "None",
            "match_score": 0
        })
        
    print(f"Running Gemma Spine Identification and database matching on {len(crops_to_process)} crops in parallel...")
    
    def process_single_crop(c):
        temp_crop_path = c["temp_path"]
        x1, y1, x2, y2 = c["box"]
        idx = c["box_idx"]
        ocr_text = c["ocr_text"]
        
        try:
            # Run Gemma multimodal book identification
            gemma_raw = identify_book_with_gemma(temp_crop_path, ocr_text)
            gemma_book = parse_gemma_response(gemma_raw)
            
            gemma_title = gemma_book.get("title", "").strip()
            gemma_author = gemma_book.get("author", "").strip()
            
            # Open a thread-local SQLite connection
            from backend.database import SessionLocal
            thread_db = SessionLocal()
            
            # Match against seeded database
            match_res = None
            if gemma_title and gemma_title != "UNKNOWN":
                search_query = f"{gemma_title} {gemma_author}"
                match_res = match_ocr_query(search_query, thread_db)
                
            thread_db.close()
            
            if match_res:
                book = match_res["book"]
                return {
                    "box_idx": idx,
                    "box": [x1, y1, x2, y2],
                    "ocr_text": ocr_text,
                    "gemma_title": gemma_title,
                    "gemma_author": gemma_author,
                    "isbn": book.book_id,
                    "title": book.title,
                    "author": book.author,
                    "match_stage": match_res["stage"],
                    "match_score": match_res["score"]
                }
            else:
                return {
                    "box_idx": idx,
                    "box": [x1, y1, x2, y2],
                    "ocr_text": ocr_text,
                    "gemma_title": gemma_title,
                    "gemma_author": gemma_author,
                    "isbn": None,
                    "title": gemma_title if gemma_title != "UNKNOWN" else None,
                    "author": gemma_author if gemma_author != "UNKNOWN" else None,
                    "match_stage": "None",
                    "match_score": 0
                }
        except Exception as e:
            print(f"Error processing spine crop index {idx}: {e}")
            return {
                "box_idx": idx,
                "box": [x1, y1, x2, y2],
                "ocr_text": ocr_text,
                "gemma_title": "ERROR",
                "gemma_author": "ERROR",
                "isbn": None,
                "title": None,
                "author": None,
                "match_stage": "None",
                "match_score": 0
            }
        finally:
            # Clean up temporary spine crop file
            if os.path.exists(temp_crop_path):
                os.remove(temp_crop_path)

    # Execute Gemma calls using ThreadPoolExecutor with 5 workers
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(process_single_crop, c): c for c in crops_to_process}
        for fut in as_completed(futures):
            res = fut.result()
            if res:
                detected_items.append(res)
                if res["isbn"]:
                    matched_isbns.append(res["isbn"])
                    
    # Step 4: Generate recommendations on the matched books present on this shelf
    recs = []
    if matched_isbns:
        # Get hybrid ranking for matched books
        recs = hybrid_recommend_shelf(user_id, list(set(matched_isbns)), db)
        
    # Map buy scores back to boxes for rendering
    buy_score_map = {}
    already_read_map = {}
    for r in recs:
        buy_score_map[r["book_id"]] = r["buy_score"]
        already_read_map[r["book_id"]] = r["already_read"]
        
    # Step 5: Create Heatmap Image
    heatmap_img = orig_img.copy()
    
    # Draw boxes
    for item in detected_items:
        x1, y1, x2, y2 = item["box"]
        isbn = item["isbn"]
        
        if isbn is None:
            # Not matched in local database catalog
            color = (128, 128, 128)
            label = item["gemma_title"][:15] if item["gemma_title"] else "Not Matched"
        elif already_read_map.get(isbn, False):
            # Already Read: Blue box
            color = (255, 120, 0) # BGR Blue
            label = "Read"
        else:
            buy_score = buy_score_map.get(isbn, 0)
            if buy_score >= 80:
                # Highly Recommended: Green
                color = (0, 200, 0)
                label = f"Buy: {buy_score}%"
            elif buy_score >= 50:
                # Maybe: Yellow
                color = (0, 220, 220)
                label = f"Maybe: {buy_score}%"
            else:
                # Low Match: Red
                color = (0, 0, 220)
                label = f"Low: {buy_score}%"
                
        # Draw box rectangle
        cv2.rectangle(heatmap_img, (x1, y1), (x2, y2), color, 3)
        
        # Add label on box
        label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.4, 1)[0]
        y_text = max(y1 - 10, label_size[1] + 10)
        cv2.putText(heatmap_img, label, (x1, y_text), cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1, cv2.LINE_AA)

    # Save heatmap image
    heatmap_filename = f"heatmap_{uuid.uuid4().hex}.jpg"
    heatmap_path = os.path.join(UPLOADS_DIR, heatmap_filename)
    cv2.imwrite(heatmap_path, heatmap_img)
    
    # Compile scan results
    return {
        "detected_books": detected_items,
        "recommendations": recs,
        "heatmap_image_url": f"/uploads/{heatmap_filename}",
        "heatmap_local_path": heatmap_path
    }
