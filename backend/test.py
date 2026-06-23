"""
CivGuard AI — Floor Plan Compliance Detector
============================================
Uses your Roboflow COCO JSON + original floor plan image as ground truth.
Upload a modified image → detects found vs missing safety elements.

Requirements:
    pip install opencv-python numpy Pillow

Usage:
    python civguard_detector.py --original floor_plan.png --test modified_floor_plan.png --json annotations.json
"""

import cv2
import numpy as np
import json
import argparse
import os
from datetime import datetime


# ─────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────
THRESHOLD        = 0.72   # Template match confidence (lower = more detections, more false positives)
PADDING          = 4      # Extra pixels around each cropped template
SCALE_VARIANTS   = [1.0, 0.95, 0.90]  # Try slight rescales to handle minor size differences

# Colours: BGR format
COLOUR_FOUND   = (34,  197, 94)    # Green
COLOUR_MISSING = (30,  30,  220)   # Red
COLOUR_TEXT_BG = (20,  20,  20)    # Dark bg for labels

# Which classes count as safety-critical (will appear in compliance summary)
SAFETY_CLASSES = {
    "Emergency Exit",
    "Fire Extinguishers",
    "Fire alarm",
    "Fire Extinguishers and alarm"
}


# ─────────────────────────────────────────
# LOAD COCO JSON
# ─────────────────────────────────────────
def load_annotations(json_path: str):
    """Parse Roboflow COCO JSON → returns category map and annotation list."""
    with open(json_path) as f:
        data = json.load(f)

    categories = {c["id"]: c["name"] for c in data["categories"]}

    annotations = []
    for ann in data["annotations"]:
        x, y, w, h = ann["bbox"]
        annotations.append({
            "id":       ann["id"],
            "class_id": ann["category_id"],
            "class":    categories[ann["category_id"]],
            "bbox":     (int(x), int(y), int(w), int(h))   # x, y, width, height (COCO format)
        })

    return categories, annotations


# ─────────────────────────────────────────
# CROP TEMPLATES FROM ORIGINAL
# ─────────────────────────────────────────
def crop_templates(original: np.ndarray, annotations: list, padding: int = PADDING):
    """Crop each annotated symbol from the original image."""
    templates = []
    h_img, w_img = original.shape[:2]

    for ann in annotations:
        x, y, w, h = ann["bbox"]
        # Add padding, clamp to image bounds
        x1 = max(0, x - padding)
        y1 = max(0, y - padding)
        x2 = min(w_img, x + w + padding)
        y2 = min(h_img, y + h + padding)

        crop = original[y1:y2, x1:x2]
        if crop.size == 0:
            continue

        templates.append({
            **ann,
            "template": crop,
            "crop_box": (x1, y1, x2 - x1, y2 - y1)
        })

    return templates


# ─────────────────────────────────────────
# TEMPLATE MATCHING
# ─────────────────────────────────────────
def match_template(test_gray: np.ndarray, template_gray: np.ndarray, threshold: float):
    """
    Try matching at multiple scales. Returns best score and location.
    """
    best_score = 0.0
    best_loc   = (0, 0)
    best_scale = 1.0

    th, tw = template_gray.shape[:2]

    for scale in SCALE_VARIANTS:
        if scale != 1.0:
            new_w = max(1, int(tw * scale))
            new_h = max(1, int(th * scale))
            tpl = cv2.resize(template_gray, (new_w, new_h))
        else:
            tpl = template_gray

        # Template must be smaller than test image
        if tpl.shape[0] >= test_gray.shape[0] or tpl.shape[1] >= test_gray.shape[1]:
            continue

        result = cv2.matchTemplate(test_gray, tpl, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)

        if max_val > best_score:
            best_score = max_val
            best_loc   = max_loc
            best_scale = scale

    found = best_score >= threshold
    return found, best_score, best_loc, best_scale


# ─────────────────────────────────────────
# DRAW RESULTS ON IMAGE
# ─────────────────────────────────────────
def draw_results(image: np.ndarray, found_items: list, missing_items: list) -> np.ndarray:
    output = image.copy()
    font   = cv2.FONT_HERSHEY_SIMPLEX

    # Draw FOUND items — solid green box
    for item in found_items:
        x, y, w, h = item["bbox"]
        label = item["class"]
        score = item.get("score", 0)

        cv2.rectangle(output, (x, y), (x + w, y + h), COLOUR_FOUND, 2)

        # Label background
        text    = f"{label} ({score:.2f})"
        (tw, th), _ = cv2.getTextSize(text, font, 0.38, 1)
        cv2.rectangle(output, (x, y - th - 6), (x + tw + 4, y), COLOUR_FOUND, -1)
        cv2.putText(output, text, (x + 2, y - 3), font, 0.38, (255, 255, 255), 1, cv2.LINE_AA)

    # Draw MISSING items — dashed red box + "MISSING" label
    for item in missing_items:
        x, y, w, h = item["bbox"]
        label = item["class"]

        # Draw dashed rectangle manually
        dash_len = 12
        gap_len  = 6
        pts = [
            ((x, y),         (x + w, y),     True),   # top
            ((x + w, y),     (x + w, y + h), False),  # right
            ((x, y + h),     (x + w, y + h), True),   # bottom
            ((x, y),         (x, y + h),     False),  # left
        ]
        for (x1, y1), (x2, y2), horizontal in pts:
            if horizontal:
                pos = x1
                while pos < x2:
                    end = min(pos + dash_len, x2)
                    cv2.line(output, (pos, y1), (end, y1), COLOUR_MISSING, 2)
                    pos += dash_len + gap_len
            else:
                pos = y1
                while pos < y2:
                    end = min(pos + dash_len, y2)
                    cv2.line(output, (x1, pos), (x1, end), COLOUR_MISSING, 2)
                    pos += dash_len + gap_len

        # "MISSING" label
        text = f"MISSING: {label}"
        (tw, th), _ = cv2.getTextSize(text, font, 0.4, 1)
        cv2.rectangle(output, (x, y - th - 8), (x + tw + 6, y), COLOUR_MISSING, -1)
        cv2.putText(output, text, (x + 3, y - 3), font, 0.4, (255, 255, 255), 1, cv2.LINE_AA)

    return output


# ─────────────────────────────────────────
# COMPLIANCE REPORT
# ─────────────────────────────────────────
def build_report(categories: dict, found_items: list, missing_items: list) -> dict:
    """Build per-class summary."""
    report = {}
    all_class_names = list(set(c for c in categories.values() if c != "inspection-demo"))

    for cls in sorted(all_class_names):
        found_count   = sum(1 for i in found_items   if i["class"] == cls)
        missing_count = sum(1 for i in missing_items if i["class"] == cls)
        total         = found_count + missing_count
        is_safety     = cls in SAFETY_CLASSES

        report[cls] = {
            "expected":  total,
            "found":     found_count,
            "missing":   missing_count,
            "compliant": missing_count == 0,
            "safety_critical": is_safety
        }

    return report


def print_report(report: dict):
    print("\n" + "=" * 58)
    print("  CivGuard AI — Compliance Report")
    print(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 58)

    overall_pass = True

    for cls, data in report.items():
        if data["expected"] == 0:
            continue
        status = "✅ OK     " if data["compliant"] else "❌ MISSING"
        tag    = " [SAFETY]" if data["safety_critical"] else ""
        print(f"  {status}  {cls:<35}{tag}")
        print(f"            Expected: {data['expected']}  |  Found: {data['found']}  |  Missing: {data['missing']}")
        if not data["compliant"] and data["safety_critical"]:
            overall_pass = False

    print("-" * 58)
    verdict = "PASS ✅" if overall_pass else "FAIL ❌ — Safety elements missing"
    print(f"  Overall compliance: {verdict}")
    print("=" * 58 + "\n")

    return overall_pass


# ─────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────
def run(original_path: str, test_path: str, json_path: str, output_path: str):

    # 1. Load images
    print(f"[1/5] Loading images...")
    original = cv2.imread(original_path)
    test_img = cv2.imread(test_path)

    if original is None:
        raise FileNotFoundError(f"Original image not found: {original_path}")
    if test_img is None:
        raise FileNotFoundError(f"Test image not found: {test_path}")

    orig_gray = cv2.cvtColor(original, cv2.COLOR_BGR2GRAY)
    test_gray = cv2.cvtColor(test_img, cv2.COLOR_BGR2GRAY)

    # 2. Load annotations (ground truth)
    print(f"[2/5] Loading {json_path}...")
    categories, annotations = load_annotations(json_path)
    print(f"      → {len(annotations)} annotations across {len(categories)-1} classes")

    # 3. Crop templates
    print(f"[3/5] Cropping symbol templates from original image...")
    templates = crop_templates(original, annotations)

    # 4. Run matching
    print(f"[4/5] Running template matching on test image...")
    found_items   = []
    missing_items = []

    for i, tpl in enumerate(templates):
        template_gray = cv2.cvtColor(tpl["template"], cv2.COLOR_BGR2GRAY)
        found, score, loc, scale = match_template(test_gray, template_gray, THRESHOLD)

        if found:
            found_items.append({**tpl, "score": score, "match_loc": loc})
        else:
            missing_items.append({**tpl, "score": score})

        # Progress
        if (i + 1) % 20 == 0 or (i + 1) == len(templates):
            print(f"      → Processed {i+1}/{len(templates)}", end="\r")

    print()
    print(f"      → Found: {len(found_items)}  |  Missing: {len(missing_items)}")

    # 5. Draw & save output
    print(f"[5/5] Generating annotated output...")
    result_img = draw_results(test_img, found_items, missing_items)
    cv2.imwrite(output_path, result_img)
    print(f"      → Saved to: {output_path}")

    # 6. Print report
    report = build_report(categories, found_items, missing_items)
    print_report(report)

    # Save report as JSON too
    report_path = output_path.replace(".png", "_report.json").replace(".jpg", "_report.json")
    with open(report_path, "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "original":  original_path,
            "test":      test_path,
            "summary":   report,
            "found":     [{"id": i["id"], "class": i["class"], "score": round(i["score"], 3)} for i in found_items],
            "missing":   [{"id": i["id"], "class": i["class"], "bbox": list(i["bbox"])} for i in missing_items]
        }, f, indent=2)
    print(f"      → JSON report saved to: {report_path}")


# ─────────────────────────────────────────
# CLI
# ─────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CivGuard AI — Floor Plan Compliance Detector")
    parser.add_argument("--original", required=True, help="Original floor plan image (with all symbols)")
    parser.add_argument("--test",     required=True, help="Modified floor plan to check (with some symbols removed)")
    parser.add_argument("--json",     required=True, help="Roboflow COCO JSON annotation file")
    parser.add_argument("--output",   default="civguard_result.png", help="Output annotated image path")
    args = parser.parse_args()

    run("floor_plan.png", "modified_floor_plan.png", "/content/train/_annotations.json", "output result.png")