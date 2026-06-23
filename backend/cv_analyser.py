"""
cv_analyser.py — OpenCV compliance analyser for "new_building" submissions.

Requires two reference files in backend/assets/:
  assets/reference_floor_plan.png  — the labeled original floor plan
  assets/annotations.json          — Roboflow COCO JSON for that image

If these files are missing, raises MissingAssetsError so the caller
can fall back to the demo analyser.
"""

import os
import base64
import json
from datetime import datetime

import cv2
import numpy as np

from civguard_compliance import run_analysis, ComplianceIssue

ASSETS_DIR       = os.path.join(os.path.dirname(__file__), "assets")
REFERENCE_IMAGE  = os.path.join(ASSETS_DIR, "reference_floor_plan.png")
ANNOTATIONS_FILE = os.path.join(ASSETS_DIR, "annotations.json")


class MissingAssetsError(RuntimeError):
    pass


def analyse_new_building(file_bytes: bytes, file_type: str, form_data: dict) -> dict:
    """
    Run the CV compliance engine on a submitted floor plan.

    Returns the same structure as the demo analyser (checks, overall_result,
    pass_count, …) plus an extra key: annotated_image_base64 (PNG).
    """
    if not os.path.isfile(REFERENCE_IMAGE) or not os.path.isfile(ANNOTATIONS_FILE):
        raise MissingAssetsError(
            "Reference assets not found. Place reference_floor_plan.png and "
            "annotations.json in the backend/assets/ folder."
        )

    # ── Load reference image + annotations ──
    original = cv2.imread(REFERENCE_IMAGE)
    if original is None:
        raise MissingAssetsError(f"Cannot read reference image: {REFERENCE_IMAGE}")

    with open(ANNOTATIONS_FILE) as f:
        annotations_data = json.load(f)

    # ── Convert uploaded file to OpenCV image ──
    test_img = _file_bytes_to_cv2(file_bytes, file_type)

    # ── Run compliance engine ──
    output_img, issues, found_count, missing_count = run_analysis(original, test_img, annotations_data)

    # ── Encode annotated output image as base64 PNG ──
    success, buf = cv2.imencode(".png", output_img)
    annotated_b64 = base64.b64encode(buf.tobytes()).decode("utf-8") if success else None

    # ── Map issues to the standard checks format ──
    checks = _build_checks(issues, found_count, missing_count, form_data)

    errors   = [i for i in issues if i.severity == "ERROR"]
    warnings = [i for i in issues if i.severity == "WARNING"]
    passed   = not errors

    pass_count  = sum(1 for c in checks if c["passed"])
    fail_count  = sum(1 for c in checks if not c["passed"] and c.get("verifiable", True))
    unverif     = sum(1 for c in checks if not c.get("verifiable", True))
    critical    = sum(1 for c in checks
                      if not c["passed"] and c.get("severity") == "CRITICAL" and c.get("verifiable", True))

    result = {
        "overall_result":      "approved" if passed else "rejected",
        "pass_count":          pass_count,
        "fail_count":          fail_count,
        "unverifiable_count":  unverif,
        "critical_failures":   critical,
        "high_failures":       sum(1 for c in checks
                                   if not c["passed"] and c.get("severity") == "HIGH"
                                   and c.get("verifiable", True)),
        "confidence":          round(found_count / max(1, found_count + missing_count) * 100, 1),
        "checks":              checks,
        "pages_analysed":      1,
        "found_symbols":       found_count,
        "missing_symbols":     missing_count,
        "summary":             _build_summary(passed, errors, warnings, found_count,
                                              missing_count, form_data),
        "annotated_image_base64": annotated_b64,
    }
    return result


# ──────────────────────────────────────────────────────
# CHECKS BUILDER — maps R1/R2/R3 to frontend check format
# ──────────────────────────────────────────────────────
def _build_checks(issues: list, found: int, missing: int, form_data: dict) -> list:
    checks = []

    # Group issues by rule
    r1 = [i for i in issues if i.rule == "R1"]
    r2 = [i for i in issues if i.rule == "R2"]
    r3 = [i for i in issues if i.rule == "R3"]

    # R1a — Fire Extinguisher coverage across all quadrants
    r1_ext = [i for i in r1 if "Extinguisher" in i.message]
    checks.append({
        "rule_key":        "cv_extinguisher_coverage",
        "name":            "Fire Extinguisher — Quadrant Coverage",
        "description":     "At least one fire extinguisher must be present in every floor quadrant.",
        "reference":       "Chapter 9, Section 13 – Portable Fire Extinguishers",
        "severity":        "CRITICAL",
        "verifiable":      True,
        "passed":          not r1_ext,
        "extracted_value": f"{4 - len(r1_ext)}/4 quadrants covered",
        "required_value":  "All 4 quadrants must have ≥1 extinguisher",
        "notes":           "; ".join(i.message for i in r1_ext) or None,
    })

    # R1b — Fire Alarm coverage
    r1_alm = [i for i in r1 if "Alarm" in i.message]
    checks.append({
        "rule_key":        "cv_alarm_coverage",
        "name":            "Fire Alarm — Quadrant Coverage",
        "description":     "At least one fire alarm must be present in every floor quadrant.",
        "reference":       "Chapter 9, Section 17 – Fire Detection",
        "severity":        "CRITICAL",
        "verifiable":      True,
        "passed":          not r1_alm,
        "extracted_value": f"{4 - len(r1_alm)}/4 quadrants covered",
        "required_value":  "All 4 quadrants must have ≥1 fire alarm",
        "notes":           "; ".join(i.message for i in r1_alm) or None,
    })

    # R1c — Emergency Exit coverage
    r1_exit = [i for i in r1 if "Emergency Exit" in i.message]
    checks.append({
        "rule_key":        "cv_exit_coverage",
        "name":            "Emergency Exit — Quadrant Coverage",
        "description":     "At least one emergency exit must be accessible in every floor quadrant.",
        "reference":       "Chapter 10 – Means of Egress, Section 11.4",
        "severity":        "CRITICAL",
        "verifiable":      True,
        "passed":          not r1_exit,
        "extracted_value": f"{4 - len(r1_exit)}/4 quadrants covered",
        "required_value":  "All 4 quadrants must have ≥1 emergency exit",
        "notes":           "; ".join(i.message for i in r1_exit) or None,
    })

    # R2 — Lift → Staircase proximity
    checks.append({
        "rule_key":        "cv_lift_stair_proximity",
        "name":            "Staircase Proximity to Each Lift",
        "description":     f"Every lift must have a staircase within {300} px (approx. 15 m).",
        "reference":       "Chapter 7, Section 10 – Vertical Transportation",
        "severity":        "HIGH",
        "verifiable":      True,
        "passed":          not r2,
        "extracted_value": "All lifts compliant" if not r2 else f"{len(r2)} lift(s) non-compliant",
        "required_value":  "Staircase within proximity of each lift",
        "notes":           "; ".join(i.message for i in r2) or None,
    })

    # R3 — Staircase → Emergency Exit proximity
    r3_errors = [i for i in r3 if i.severity == "ERROR"]
    checks.append({
        "rule_key":        "cv_stair_exit_proximity",
        "name":            "Emergency Exit Adjacent to Staircases",
        "description":     f"At least {MIN_STAIRS_WITH_EXIT} staircases must have an emergency exit within {400} px.",
        "reference":       "Chapter 10, Section 11.3 – Exit Separation",
        "severity":        "HIGH",
        "verifiable":      True,
        "passed":          not r3_errors,
        "extracted_value": "Compliant" if not r3_errors else r3_errors[0].message,
        "required_value":  f"≥{MIN_STAIRS_WITH_EXIT} staircases with nearby exit",
        "notes":           "; ".join(i.message for i in r3) or None,
    })

    # Remaining original 4 checks — unverifiable without form measurements
    for rule_key, name, desc, ref, sev in [
        ("sprinkler_system",  "Sprinkler System",
         "Required for buildings ≥3 floors or ≥14 m height.",
         "Chapter 9, Section 25", "CRITICAL"),
        ("travel_distance",   "Max Travel Distance to Exit",
         "Non-sprinklered ≤45 m; sprinklered ≤60 m.",
         "Chapter 10, Section 11.4 – Table 3.6A", "CRITICAL"),
        ("corridor_width",    "Minimum Corridor Width",
         "≥1200 mm clear width.",
         "Chapter 10, Section 11.6.5", "CRITICAL"),
        ("emergency_lighting","Emergency Lighting",
         "Required in all corridors and exit routes.",
         "Chapter 9, Section 23", "MEDIUM"),
    ]:
        checks.append({
            "rule_key":        rule_key,
            "name":            name,
            "description":     desc,
            "reference":       ref,
            "severity":        sev,
            "verifiable":      False,
            "passed":          True,
            "extracted_value": "Not measurable from image alone",
            "required_value":  desc,
            "notes":           "Manual site inspection required to verify this rule.",
        })

    return checks


# ──────────────────────────────────────────────────────
# SUMMARY TEXT
# ──────────────────────────────────────────────────────
def _build_summary(passed, errors, warnings, found, missing, form_data):
    name = form_data.get("project_name") or "The submitted building"
    if passed:
        return (
            f"{name} has passed all computer-vision compliance checks: "
            f"{found} fire-safety symbols detected across all quadrants. "
            f"Quadrant coverage for extinguishers, alarms, and exits is confirmed. "
            f"Pending DCD officer sign-off before the result is official."
        )
    else:
        msgs = "; ".join(e.message[:80] for e in errors[:3])
        return (
            f"{name} has {len(errors)} critical compliance failure(s) detected by AI visual analysis. "
            f"Key issues: {msgs}. "
            f"{'Additionally, '+str(missing)+' fire-safety symbol(s) were not found in the submitted plan. ' if missing else ''}"
            f"All CRITICAL items must be corrected before resubmission."
        )


# ──────────────────────────────────────────────────────
# FILE → OpenCV IMAGE CONVERSION
# ──────────────────────────────────────────────────────
def _file_bytes_to_cv2(file_bytes: bytes, file_type: str) -> np.ndarray:
    """Convert raw file bytes (image or PDF first page) to a BGR numpy array."""
    mime = (file_type or "").lower()

    if "pdf" in mime:
        # Use PyMuPDF (already in requirements) to render first page
        try:
            import fitz  # PyMuPDF
            doc  = fitz.open(stream=file_bytes, filetype="pdf")
            page = doc[0]
            mat  = fitz.Matrix(2, 2)   # 2× scale → ~150 dpi
            pix  = page.get_pixmap(matrix=mat)
            img_array = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
            if pix.n == 4:
                img_array = cv2.cvtColor(img_array, cv2.COLOR_RGBA2BGR)
            elif pix.n == 3:
                img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
            return img_array
        except Exception as e:
            raise RuntimeError(f"PDF rendering failed: {e}") from e
    else:
        # Image (JPEG, PNG, etc.)
        arr = np.frombuffer(file_bytes, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            raise RuntimeError("Could not decode submitted image file.")
        return img


# Import constant for use in checks builder
from civguard_compliance import MIN_STAIRS_WITH_EXIT
