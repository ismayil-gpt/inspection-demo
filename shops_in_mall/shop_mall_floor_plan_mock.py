"""
Standalone mock for Shop-in-Mall floor plan pre-compliance analysis.

Usage:
    python shop_mall_floor_plan_mock.py --image path/to/floor_plan.png --area-sqm 750
    python shop_mall_floor_plan_mock.py --image complete-demo.png --area-sqm 750 --mall-noc-uploaded

This file is intentionally self-contained so it can later be copied into, or called from,
the main backend without depending on the FastAPI app.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
for package_dir in (SCRIPT_DIR / "python_packages", SCRIPT_DIR.parent / "python_packages"):
    if package_dir.exists():
        sys.path.insert(0, str(package_dir))

SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}
MOCK_UPLOAD_ROOT = Path("storage/mock_shop_mall_uploads")


KEYWORD_PATTERNS = {
    "exit_signs": [r"exit sign", r"exit signage", r"\bexit\b"],
    "emergency_lights": [r"emergency light", r"emergency lighting", r"\bel\b"],
    "fire_extinguishers": [r"fire extinguisher", r"\bfe\b", r"extinguisher"],
    "fire_alarms": [r"fire alarm", r"\bfa\b", r"alarm bell", r"sounder"],
    "smoke_detectors": [r"smoke detector", r"\bsd\b", r"detector"],
    "manual_call_points": [r"manual call point", r"\bmcp\b", r"break glass"],
    "sprinklers": [r"sprinkler", r"\bspk\b", r"sprinkler head"],
    "scale_available": [r"scale\s*[:=]", r"1\s*:\s*\d+"],
    "legend_available": [r"legend", r"symbols?", r"abbreviation"],
}


RECOMMENDATIONS = {
    "mall_shop_area_valid": (
        "Confirm the mall shop area is suitable for this demo workflow.",
        "Critical",
    ),
    "exit_signs_available": (
        "Add illuminated exit signage at required exits and update the life-safety drawing.",
        "Critical",
    ),
    "emergency_lights_available": (
        "Add emergency lighting coverage to escape paths and coordinate it with exit signage.",
        "High",
    ),
    "fire_extinguishers_shown": (
        "Show fire extinguisher locations on the plan and include them in the legend.",
        "Critical",
    ),
    "smoke_detector_fire_alarm_points_shown": (
        "Show smoke detector/fire alarm points, including manual call points where applicable.",
        "Critical",
    ),
    "sprinkler_layout_shown": (
        "Add sprinkler head layout or provide the coordinated fire protection drawing.",
        "High",
    ),
    "drawing_scale_available": (
        "Add a readable drawing scale so distances and coverage can be checked.",
        "Medium",
    ),
    "legend_symbols_available": (
        "Add a legend defining all life-safety symbols used in the drawing package.",
        "Medium",
    ),
    "mall_noc_uploaded": (
        "Upload the mall NOC or landlord approval package with the submission set.",
        "High",
    ),
}


CRITICAL_CHECKS = {
    "mall_shop_area_valid",
    "exit_signs_available",
    "fire_extinguishers_shown",
    "smoke_detector_fire_alarm_points_shown",
}


@dataclass(frozen=True)
class AnalysisInput:
    image_path: Path
    area_sqm: float
    mall_noc_uploaded: bool


def transfer_file_to_mock_storage(image_path: Path) -> dict[str, str]:
    if not image_path.exists():
        raise FileNotFoundError(f"Floor plan image not found: {image_path}")

    if image_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        allowed = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        raise ValueError(f"Unsupported file type. Use one of: {allowed}")

    upload_id = str(uuid.uuid4())
    target_dir = MOCK_UPLOAD_ROOT / upload_id
    target_dir.mkdir(parents=True, exist_ok=True)
    stored_path = target_dir / image_path.name
    shutil.copy2(image_path, stored_path)
    return {"upload_id": upload_id, "stored_path": str(stored_path)}


def extract_text_from_image(image_path: Path) -> tuple[str, list[str]]:
    warnings: list[str] = []
    try:
        import cv2
        import pytesseract

        configure_tesseract(pytesseract)
        image = cv2.imread(str(image_path))
        if image is None:
            return "", ["Image could not be decoded for OCR."]
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        gray = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
        text = pytesseract.image_to_string(gray)
        return text, warnings
    except Exception as exc:
        warnings.append(f"OCR unavailable or failed: {exc}")
        return "", warnings


def configure_tesseract(pytesseract_module: Any) -> None:
    detected_path = shutil.which("tesseract")
    if detected_path:
        pytesseract_module.pytesseract.tesseract_cmd = detected_path
        return

    common_paths = [
        Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe"),
        Path(r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"),
        Path(r"C:\ProgramData\chocolatey\bin\tesseract.exe"),
    ]
    for candidate in common_paths:
        if candidate.exists():
            pytesseract_module.pytesseract.tesseract_cmd = str(candidate)
            return


def count_keywords(text: str, filename: str) -> dict[str, int]:
    searchable = f"{text}\n{filename}".lower()
    counts: dict[str, int] = {}
    for key, patterns in KEYWORD_PATTERNS.items():
        total = 0
        for pattern in patterns:
            total += len(re.findall(pattern, searchable, flags=re.IGNORECASE))
        counts[key] = total
    return apply_demo_filename_hints(filename, counts)


def apply_demo_filename_hints(filename: str, counts: dict[str, int]) -> dict[str, int]:
    name = filename.lower()
    if "mall-inspection-demo-floorplan" in name:
        return {
            **counts,
            "exit_signs": max(counts["exit_signs"], 4),
            "emergency_lights": max(counts["emergency_lights"], 2),
            "fire_extinguishers": max(counts["fire_extinguishers"], 2),
            "fire_alarms": max(counts["fire_alarms"], 2),
            "smoke_detectors": max(counts["smoke_detectors"], 2),
            "manual_call_points": max(counts["manual_call_points"], 2),
            "sprinklers": max(counts["sprinklers"], 12),
            "scale_available": max(counts["scale_available"], 1),
            "legend_available": max(counts["legend_available"], 1),
        }
    if "complete-demo" in name:
        return {
            **counts,
            "exit_signs": max(counts["exit_signs"], 2),
            "emergency_lights": max(counts["emergency_lights"], 4),
            "fire_extinguishers": max(counts["fire_extinguishers"], 3),
            "fire_alarms": max(counts["fire_alarms"], 2),
            "smoke_detectors": max(counts["smoke_detectors"], 6),
            "manual_call_points": max(counts["manual_call_points"], 2),
            "sprinklers": max(counts["sprinklers"], 12),
            "scale_available": max(counts["scale_available"], 1),
            "legend_available": max(counts["legend_available"], 1),
        }
    if "review-demo" in name:
        return {
            **counts,
            "exit_signs": max(counts["exit_signs"], 1),
            "emergency_lights": max(counts["emergency_lights"], 2),
            "fire_extinguishers": max(counts["fire_extinguishers"], 1),
            "fire_alarms": max(counts["fire_alarms"], 1),
            "scale_available": max(counts["scale_available"], 1),
        }
    if "reject-demo" in name:
        return {
            **counts,
            "emergency_lights": max(counts["emergency_lights"], 2),
            "sprinklers": max(counts["sprinklers"], 4),
            "scale_available": max(counts["scale_available"], 1),
            "legend_available": max(counts["legend_available"], 1),
        }
    return counts


def basic_image_metrics(image_path: Path) -> dict[str, Any]:
    try:
        from PIL import Image

        with Image.open(image_path) as image:
            return {
                "width_px": image.width,
                "height_px": image.height,
                "mode": image.mode,
                "format": image.format,
            }
    except Exception:
        return {"width_px": None, "height_px": None, "mode": None, "format": None}


def evaluate_mall_shop_area(area_sqm: float) -> dict[str, Any]:
    area_sqft = round(area_sqm * 10.7639, 2)
    if 46.5 <= area_sqm <= 139.4:
        message = "Mall shop area is valid for this demo"
        valid_for_demo = True
    elif 13.9 < area_sqm < 46.5 or 139.4 < area_sqm <= 464.4:
        message = "Mall shop area needs manual review"
        valid_for_demo = False
    else:
        message = "Mall shop area is outside the demo range"
        valid_for_demo = False

    return {
        "area_sqm": round(area_sqm, 2),
        "area_sqft": area_sqft,
        "valid_for_demo": valid_for_demo,
        "message": message,
    }


def build_checklist(
    mall_shop_area: dict[str, Any], counts: dict[str, int], mall_noc_uploaded: bool
) -> list[dict[str, Any]]:
    smoke_or_alarm_count = (
        counts["smoke_detectors"] + counts["fire_alarms"] + counts["manual_call_points"]
    )
    checks = [
        (
            "mall_shop_area_valid",
            mall_shop_area["message"],
            bool(mall_shop_area["valid_for_demo"]),
        ),
        ("exit_signs_available", "Exit signs are available", counts["exit_signs"] > 0),
        (
            "emergency_lights_available",
            "Emergency lights are available",
            counts["emergency_lights"] > 0,
        ),
        (
            "fire_extinguishers_shown",
            "Fire extinguishers are shown",
            counts["fire_extinguishers"] > 0,
        ),
        (
            "smoke_detector_fire_alarm_points_shown",
            "Smoke detector/fire alarm points are shown",
            smoke_or_alarm_count > 0,
        ),
        ("sprinkler_layout_shown", "Sprinkler layout is shown", counts["sprinklers"] > 0),
        ("drawing_scale_available", "Drawing scale is available", counts["scale_available"] > 0),
        ("legend_symbols_available", "Legend/symbols are available", counts["legend_available"] > 0),
        ("mall_noc_uploaded", "Mall NOC is uploaded", mall_noc_uploaded),
    ]
    return [
        {
            "id": check_id,
            "label": label,
            "passed": passed,
            "critical": check_id in CRITICAL_CHECKS,
        }
        for check_id, label, passed in checks
    ]


def decide(checklist: list[dict[str, Any]], confidence: float) -> dict[str, Any]:
    passed = sum(1 for item in checklist if item["passed"])
    score = round((passed / len(checklist)) * 100, 2)
    missing_items = [item for item in checklist if not item["passed"]]
    critical_missing = [item for item in checklist if item["critical"] and not item["passed"]]

    if critical_missing or score < 50:
        status = "Rejected"
        accepted = False
    elif missing_items or score < 85:
        status = "Needs Manual Review"
        accepted = False
    else:
        status = "Accepted"
        accepted = True

    issues = [
        {
            "item_id": item["id"],
            "message": item["label"],
            "priority": "Critical" if item["critical"] else "Review",
        }
        for item in checklist
        if not item["passed"]
    ]
    return {
        "accepted": accepted,
        "status": status,
        "score": score,
        "confidence": round(max(0.1, min(0.99, confidence)), 2),
        "issues": issues,
    }


def build_recommendations(checklist: list[dict[str, Any]]) -> list[dict[str, str]]:
    output = []
    for item in checklist:
        if item["passed"]:
            continue
        recommendation, priority = RECOMMENDATIONS[item["id"]]
        output.append(
            {
                "item_id": item["id"],
                "reason": item["label"],
                "recommendation": recommendation,
                "priority": priority,
            }
        )
    return output


ANNOTATION_PLACEMENTS = {
    "fire_extinguishers_shown": [
        (0.38, 0.14, "Add fire extinguisher near the main mall corridor entrance"),
        (0.46, 0.64, "Add fire extinguisher near the secondary mall corridor exit"),
    ],
    "exit_signs_available": [
        (0.38, 0.09, "Add exit sign at main entrance"),
        (0.46, 0.64, "Add exit sign at secondary exit"),
    ],
    "emergency_lights_available": [
        (0.40, 0.18, "Add emergency light near entrance"),
        (0.46, 0.43, "Add emergency light at central circulation path"),
    ],
    "smoke_detector_fire_alarm_points_shown": [
        (0.40, 0.20, "Add detector / MCP near entrance"),
        (0.46, 0.38, "Add detector / MCP in central shop area"),
    ],
    "sprinkler_layout_shown": [
        (0.30, 0.30, "Add sprinkler coverage"),
        (0.44, 0.30, "Add sprinkler coverage"),
        (0.58, 0.30, "Add sprinkler coverage"),
        (0.44, 0.50, "Add sprinkler coverage"),
    ],
}


ANNOTATION_LABELS = {
    "fire_extinguishers_shown": "Add fire extinguisher",
    "exit_signs_available": "Add exit sign",
    "emergency_lights_available": "Add emergency light",
    "smoke_detector_fire_alarm_points_shown": "Add detector / MCP",
    "sprinkler_layout_shown": "Add sprinkler coverage",
}


def build_annotations(
    image_path: Path, recommendations: list[dict[str, str]]
) -> tuple[str | None, list[dict[str, Any]], list[str]]:
    warnings: list[str] = []
    drawable_recommendations = [
        rec for rec in recommendations if rec["item_id"] in ANNOTATION_PLACEMENTS
    ]
    if any(rec["item_id"] == "fire_extinguishers_shown" for rec in drawable_recommendations):
        drawable_recommendations = [
            rec for rec in drawable_recommendations if rec["item_id"] == "fire_extinguishers_shown"
        ]
    if not drawable_recommendations:
        return None, [], warnings

    try:
        from PIL import Image, ImageDraw, ImageFont

        with Image.open(image_path) as image:
            annotated = image.convert("RGB")

        draw = ImageDraw.Draw(annotated)
        width, height = annotated.size
        radius = max(24, min(width, height) // 34)
        font = ImageFont.load_default()
        annotations: list[dict[str, Any]] = []

        for rec in drawable_recommendations:
            item_id = rec["item_id"]
            for x_ratio, y_ratio, note in ANNOTATION_PLACEMENTS[item_id]:
                x = int(width * x_ratio)
                y = int(height * y_ratio)
                label = ANNOTATION_LABELS[item_id]
                bbox = [x - radius, y - radius, x + radius, y + radius]
                draw.ellipse(bbox, outline=(220, 0, 0), width=5)
                draw.line([x - radius, y, x + radius, y], fill=(220, 0, 0), width=2)
                draw.line([x, y - radius, x, y + radius], fill=(220, 0, 0), width=2)
                label_position = (max(4, x - radius), max(4, y - radius - 18))
                text_bbox = draw.textbbox(label_position, label, font=font)
                padded_bbox = [
                    text_bbox[0] - 3,
                    text_bbox[1] - 2,
                    text_bbox[2] + 3,
                    text_bbox[3] + 2,
                ]
                draw.rectangle(padded_bbox, fill=(255, 255, 255), outline=(220, 0, 0))
                draw.text(label_position, label, fill=(180, 0, 0), font=font)
                annotations.append(
                    {
                        "item_id": item_id,
                        "label": label,
                        "recommendation": rec["recommendation"],
                        "priority": rec["priority"],
                        "shape": "circle",
                        "x": x,
                        "y": y,
                        "radius": radius,
                        "note": note,
                    }
                )

        output_path = image_path.with_name(f"annotated_{image_path.stem}.png")
        annotated.save(output_path)
        return str(output_path), annotations, warnings
    except Exception as exc:
        warnings.append(f"Annotation generation failed: {exc}")
        return None, [], warnings


def estimate_confidence(text: str, counts: dict[str, int], metrics: dict[str, Any]) -> float:
    detected_groups = sum(1 for count in counts.values() if count > 0)
    base = 0.25 if text.strip() else 0.12
    if metrics.get("width_px") and metrics.get("height_px"):
        base += 0.08
    return base + detected_groups * 0.07


def analyse_floor_plan(payload: AnalysisInput) -> dict[str, Any]:
    transfer = transfer_file_to_mock_storage(payload.image_path)
    stored_path = Path(transfer["stored_path"])
    text, warnings = extract_text_from_image(stored_path)
    metrics = basic_image_metrics(stored_path)
    counts = count_keywords(text, stored_path.name)
    confidence = estimate_confidence(text, counts, metrics)
    mall_shop_area = evaluate_mall_shop_area(payload.area_sqm)
    checklist = build_checklist(mall_shop_area, counts, payload.mall_noc_uploaded)
    decision = decide(checklist, confidence)
    recommendations = build_recommendations(checklist)
    annotated_image_path, annotations, annotation_warnings = build_annotations(
        stored_path, recommendations
    )

    return {
        "project_type": "shop_in_mall",
        "analysis_type": "mock_floor_plan_image_precheck",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "input": {
            "original_file": str(payload.image_path),
            "stored_file": transfer["stored_path"],
            "upload_id": transfer["upload_id"],
            "area_sqm": payload.area_sqm,
            "mall_noc_uploaded": payload.mall_noc_uploaded,
        },
        "image": metrics,
        "mall_shop_area": mall_shop_area,
        "detected_counts": {
            "exit_signs": counts["exit_signs"],
            "emergency_lights": counts["emergency_lights"],
            "fire_extinguishers": counts["fire_extinguishers"],
            "fire_alarms": counts["fire_alarms"],
            "smoke_detectors": counts["smoke_detectors"],
            "manual_call_points": counts["manual_call_points"],
            "sprinklers": counts["sprinklers"],
            "drawing_scale_mentions": counts["scale_available"],
            "legend_mentions": counts["legend_available"],
        },
        "decision": decision,
        "checklist": checklist,
        "recommendations": recommendations,
        "annotated_image_path": annotated_image_path,
        "annotations": annotations,
        "ocr_text_excerpt": text[:800],
        "warnings": warnings
        + annotation_warnings
        + [
            "This is a mock heuristic analysis, not final DCD approval.",
            "Symbol counts are based on OCR/filename hints until a trained vision model is connected.",
        ],
    }


def parse_args() -> AnalysisInput:
    parser = argparse.ArgumentParser(description="Mock Shop-in-Mall floor plan image analyser")
    parser.add_argument("--image", required=True, help="Path to floor plan image")
    parser.add_argument("--area-sqm", required=True, type=float, help="Shop area in square meters")
    parser.add_argument(
        "--mall-noc-uploaded",
        action="store_true",
        help="Pass this flag when mall NOC/landlord approval is uploaded",
    )
    args = parser.parse_args()
    return AnalysisInput(
        image_path=Path(args.image),
        area_sqm=args.area_sqm,
        mall_noc_uploaded=args.mall_noc_uploaded,
    )


def main() -> int:
    try:
        result = analyse_floor_plan(parse_args())
        print(json.dumps(result, indent=2, ensure_ascii=True))
        return 0
    except Exception as exc:
        print(json.dumps({"error": str(exc)}, indent=2), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
