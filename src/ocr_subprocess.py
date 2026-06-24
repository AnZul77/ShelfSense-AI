import os
import sys
import json
import cv2

# Set logging level for paddle to suppress warnings/logs
os.environ["PPOCR_LOG_LEVEL"] = "WARNING"

def run_ocr(ocr_engine, img):
    try:
        # Run OCR on the image
        result = ocr_engine.ocr(img, cls=True)
        if not result or result[0] is None:
            return "", 0.0
        words = []
        confs = []
        for line in result[0]:
            words.append(line[1][0])
            confs.append(line[1][1])
        text = " ".join(words)
        confidence = sum(confs) / len(confs) if confs else 0.0
        return text, confidence
    except Exception as e:
        print(f"Subprocess OCR Error: {e}", file=sys.stderr)
        return "", 0.0

def main():
    if len(sys.argv) < 3:
        print(json.dumps({"error": "Usage: ocr_subprocess.py <input_json_path> <output_json_path>"}))
        sys.exit(1)

    input_json_path = sys.argv[1]
    output_json_path = sys.argv[2]

    # Load list of crop paths
    try:
        with open(input_json_path, "r", encoding="utf-8") as f:
            image_paths = json.load(f)
    except Exception as e:
        print(json.dumps({"error": f"Failed to read input JSON: {e}"}))
        sys.exit(1)

    # Initialize PaddleOCR on CPU (avoids cudnn64_8.dll Windows DLL issues while remaining extremely fast)
    try:
        from paddleocr import PaddleOCR
        ocr_engine = PaddleOCR(
            use_angle_cls=True,
            lang="en",
            use_gpu=False,
            show_log=False
        )
    except Exception as e:
        print(json.dumps({"error": f"Failed to initialize PaddleOCR: {e}"}))
        sys.exit(1)

    results = {}
    total = len(image_paths)
    
    for idx, path in enumerate(image_paths):
        if not os.path.exists(path):
            results[path] = {"text": "", "confidence": 0.0}
            continue

        img = cv2.imread(path)
        if img is None:
            results[path] = {"text": "", "confidence": 0.0}
            continue

        # Run OCR directly (PaddleOCR handles rotated/vertical spines natively with use_angle_cls)
        text, conf = run_ocr(ocr_engine, img)

        results[path] = {
            "text": text.strip().upper(),
            "confidence": conf
        }
        
        # Report progress to stderr
        print(f"Processed crop {idx+1}/{total}", file=sys.stderr)

    # Write output JSON
    try:
        with open(output_json_path, "w", encoding="utf-8") as f:
            json.dump(results, f)
        print("SUCCESS")
    except Exception as e:
        print(json.dumps({"error": f"Failed to write output JSON: {e}"}))
        sys.exit(1)

if __name__ == "__main__":
    main()
