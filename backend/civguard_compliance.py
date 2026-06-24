"""
CivGuard AI — Compliance Engine
================================
Detects fire-safety symbols on a floor plan via template matching and enforces
three DCD rules.

  R1. Each quadrant must have ≥1 fire extinguisher, fire alarm, emergency exit
  R2. Each lift must have a staircase within LIFT_STAIR_RADIUS px
  R3. Each staircase must have ≥1 emergency exit within EXIT_STAIR_RADIUS px
      (at least MIN_STAIRS_WITH_EXIT stairs must pass)

Blackout guard: matched patches are rejected if they look like solid black
rectangles (variance + brightness test), preventing false positives when
symbols are redacted/hidden.

Requirements: opencv-python-headless numpy

Programmatic use (from cv_analyser.py):
    from civguard_compliance import run_analysis
    result_img, issues, found, missing = run_analysis(original_img, test_img, annotations_data)

CLI use:
    python civguard_compliance.py --original floor_plan.png --test modified.png --json annotations.json
"""

import cv2
import numpy as np
import json
import argparse
import os
from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict


# ──────────────────────────────────────────────────────
# TUNABLE PARAMETERS
# ──────────────────────────────────────────────────────
TEMPLATE_THRESHOLD   = 0.95
TEMPLATE_PADDING     = 4
SCALE_VARIANTS       = [1.0, 0.95, 0.90]

LIFT_STAIR_RADIUS    = 300
EXIT_STAIR_RADIUS    = 400
MIN_STAIRS_WITH_EXIT = 3

MIN_PATCH_VARIANCE   = 80.0
MIN_PATCH_BRIGHTNESS = 30

SPLIT_LINES = [
    np.array([[1644, -2],  [1624, 1886]]),
    np.array([[6,  1033],  [2738, 1041]]),
]
SPLIT_X = 1634
SPLIT_Y = 1037

C_FOUND   = (34,  197,  94)
C_MISSING = (30,   30, 220)
C_WARNING = (0,   165, 255)
C_CIRCLE  = (180,  50, 255)
C_QUAD    = (200, 200, 200)
C_WHITE   = (255, 255, 255)
C_BLACK   = (0,     0,   0)


# ──────────────────────────────────────────────────────
# DATA STRUCTURES
# ──────────────────────────────────────────────────────
@dataclass
class Annotation:
    id:       int
    class_id: int
    cls:      str
    bbox:     Tuple[int,int,int,int]
    template: Optional[np.ndarray] = field(default=None, repr=False)

    @property
    def center(self) -> Tuple[int,int]:
        x, y, w, h = self.bbox
        return (x + w // 2, y + h // 2)

    @property
    def x1(self): return self.bbox[0]
    @property
    def y1(self): return self.bbox[1]
    @property
    def x2(self): return self.bbox[0] + self.bbox[2]
    @property
    def y2(self): return self.bbox[1] + self.bbox[3]


@dataclass
class ComplianceIssue:
    rule:     str
    message:  str
    bbox:     Optional[Tuple] = None
    severity: str = "ERROR"


# ──────────────────────────────────────────────────────
# LOAD ANNOTATIONS
# ──────────────────────────────────────────────────────
def load_annotations_from_file(json_path: str) -> Tuple[Dict, List[Annotation]]:
    with open(json_path) as f:
        data = json.load(f)
    return _parse_annotations(data)


def load_annotations_from_dict(data: dict) -> Tuple[Dict, List[Annotation]]:
    return _parse_annotations(data)


def _parse_annotations(data: dict) -> Tuple[Dict, List[Annotation]]:
    categories = {c["id"]: c["name"] for c in data["categories"]}
    annotations = []
    for ann in data["annotations"]:
        x, y, w, h = ann["bbox"]
        annotations.append(Annotation(
            id       = ann["id"],
            class_id = ann["category_id"],
            cls      = categories[ann["category_id"]],
            bbox     = (int(x), int(y), int(w), int(h))
        ))
    return categories, annotations


# ──────────────────────────────────────────────────────
# TEMPLATE CROPPING
# ──────────────────────────────────────────────────────
def attach_templates(original: np.ndarray, annotations: List[Annotation], padding=TEMPLATE_PADDING):
    h_img, w_img = original.shape[:2]
    for ann in annotations:
        x, y, w, h = ann.bbox
        x1 = max(0, x - padding);   y1 = max(0, y - padding)
        x2 = min(w_img, x+w+padding); y2 = min(h_img, y+h+padding)
        crop = original[y1:y2, x1:x2]
        if crop.size > 0:
            ann.template = crop


# ──────────────────────────────────────────────────────
# TEMPLATE MATCHING + BLACKOUT GUARD
# ──────────────────────────────────────────────────────
def _is_blacked_out(patch: np.ndarray) -> bool:
    mean, std = cv2.meanStdDev(patch)
    return float(std[0][0]) < MIN_PATCH_VARIANCE and float(mean[0][0]) < MIN_PATCH_BRIGHTNESS


def match_one(test_gray: np.ndarray, template_gray: np.ndarray, threshold=TEMPLATE_THRESHOLD):
    best_score, best_loc, best_tpl_size = 0.0, (0, 0), template_gray.shape[:2]
    th, tw = template_gray.shape[:2]

    for scale in SCALE_VARIANTS:
        tpl = (cv2.resize(template_gray, (max(1,int(tw*scale)), max(1,int(th*scale))))
               if scale != 1.0 else template_gray)
        if tpl.shape[0] >= test_gray.shape[0] or tpl.shape[1] >= test_gray.shape[1]:
            continue
        res = cv2.matchTemplate(test_gray, tpl, cv2.TM_CCOEFF_NORMED)
        _, mv, _, ml = cv2.minMaxLoc(res)
        if mv > best_score:
            best_score, best_loc, best_tpl_size = mv, ml, tpl.shape[:2]

    if best_score < threshold:
        return False, best_score, best_loc

    lx, ly = best_loc
    ph, pw = best_tpl_size
    patch = test_gray[ly:ly+ph, lx:lx+pw]
    if patch.size > 0 and _is_blacked_out(patch):
        return False, best_score, best_loc

    return True, best_score, best_loc


# ──────────────────────────────────────────────────────
# QUADRANT HELPERS
# ──────────────────────────────────────────────────────
def quadrant_of(cx: int, cy: int) -> int:
    left = cx <= SPLIT_X;  top = cy <= SPLIT_Y
    if   left and top:  return 1
    elif not left and top:  return 2
    elif left and not top:  return 3
    else: return 4

QUAD_NAMES = {1:"Top-Left", 2:"Top-Right", 3:"Bottom-Left", 4:"Bottom-Right"}

def quadrant_bbox(q: int, img_w: int, img_h: int):
    sx, sy = SPLIT_X, SPLIT_Y
    return {1:(0,0,sx,sy), 2:(sx,0,img_w,sy), 3:(0,sy,sx,img_h), 4:(sx,sy,img_w,img_h)}[q]


def dist(a, b) -> float:
    return ((a[0]-b[0])**2 + (a[1]-b[1])**2) ** 0.5


# ──────────────────────────────────────────────────────
# COMPLIANCE RULES
# ──────────────────────────────────────────────────────
def check_rule1(detected: List[Annotation], img_w: int, img_h: int) -> List[ComplianceIssue]:
    EXTINGUISHER = {"Fire Extinguishers", "Fire Extinguishers and alarm"}
    ALARM        = {"Fire alarm",          "Fire Extinguishers and alarm"}
    EXIT         = {"Emergency Exit"}
    issues = []
    for q in range(1, 5):
        q_anns = [a for a in detected if quadrant_of(*a.center) == q]
        qname  = QUAD_NAMES[q]
        qbox   = quadrant_bbox(q, img_w, img_h)
        if not any(a.cls in EXTINGUISHER for a in q_anns):
            issues.append(ComplianceIssue("R1", f"Quadrant {qname}: no Fire Extinguisher found", qbox))
        if not any(a.cls in ALARM for a in q_anns):
            issues.append(ComplianceIssue("R1", f"Quadrant {qname}: no Fire Alarm found", qbox))
        if not any(a.cls in EXIT for a in q_anns):
            issues.append(ComplianceIssue("R1", f"Quadrant {qname}: no Emergency Exit found", qbox))
    return issues


def check_rule2(detected: List[Annotation], output_img: np.ndarray) -> List[ComplianceIssue]:
    issues = []
    lifts  = [a for a in detected if a.cls == "Lift"]
    stairs = [a for a in detected if a.cls == "Stairs"]
    for lift in lifts:
        lc = lift.center
        nearest = min(stairs, key=lambda s: dist(lc, s.center), default=None)
        if nearest is None:
            issues.append(ComplianceIssue("R2", f"Lift at {lc}: no staircase found anywhere", lift.bbox))
            continue
        d  = dist(lc, nearest.center)
        sc = nearest.center
        if d <= LIFT_STAIR_RADIUS:
            r = max(nearest.bbox[2], nearest.bbox[3]) // 2 + 20
            cv2.circle(output_img, sc, r, C_CIRCLE, 3)
            cv2.putText(output_img, "STAIR✓", (sc[0]-28, sc[1]-r-8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, C_CIRCLE, 1, cv2.LINE_AA)
        else:
            issues.append(ComplianceIssue(
                "R2", f"Lift at {lc}: nearest staircase {int(d)}px away (limit {LIFT_STAIR_RADIUS}px)", lift.bbox))
            cv2.circle(output_img, lc, LIFT_STAIR_RADIUS, C_MISSING, 2)
            cv2.putText(output_img, f"Need stair within {LIFT_STAIR_RADIUS}px",
                        (lc[0]-80, lc[1]-LIFT_STAIR_RADIUS-8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, C_MISSING, 1, cv2.LINE_AA)
    return issues


def check_rule3(detected: List[Annotation]) -> List[ComplianceIssue]:
    issues = []
    stairs = [a for a in detected if a.cls == "Stairs"]
    exits  = [a for a in detected if a.cls == "Emergency Exit"]
    stairs_ok = 0
    for stair in stairs:
        sc = stair.center
        if any(dist(sc, e.center) <= EXIT_STAIR_RADIUS for e in exits):
            stairs_ok += 1
        else:
            issues.append(ComplianceIssue(
                "R3", f"Staircase at {sc}: no Emergency Exit within {EXIT_STAIR_RADIUS}px",
                stair.bbox, severity="WARNING"))
    if stairs_ok < MIN_STAIRS_WITH_EXIT:
        issues.append(ComplianceIssue(
            "R3",
            f"Only {stairs_ok}/{len(stairs)} staircases have a nearby exit "
            f"(minimum required: {MIN_STAIRS_WITH_EXIT})",
            severity="ERROR"))
    return issues


# ──────────────────────────────────────────────────────
# DRAWING HELPERS
# ──────────────────────────────────────────────────────
def draw_quadrant_grid(img, img_w, img_h):
    p1 = (SPLIT_LINES[0][0][0], max(0, SPLIT_LINES[0][0][1]))
    p2 = (SPLIT_LINES[0][1][0], min(img_h, SPLIT_LINES[0][1][1]))
    cv2.line(img, p1, p2, C_QUAD, 2, cv2.LINE_AA)
    p3 = (max(0, SPLIT_LINES[1][0][0]), SPLIT_LINES[1][0][1])
    p4 = (min(img_w, SPLIT_LINES[1][1][0]), SPLIT_LINES[1][1][1])
    cv2.line(img, p3, p4, C_QUAD, 2, cv2.LINE_AA)
    offsets = {1:(10,30), 2:(SPLIT_X+10,30), 3:(10,SPLIT_Y+30), 4:(SPLIT_X+10,SPLIT_Y+30)}
    for q, (ox, oy) in offsets.items():
        cv2.putText(img, f"Q{q}: {QUAD_NAMES[q]}", (ox, oy),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, C_QUAD, 2, cv2.LINE_AA)


def draw_detection(img, ann: Annotation, found: bool, score: float):
    x, y, w, h = ann.bbox
    colour = C_FOUND if found else C_MISSING
    if found:
        cv2.rectangle(img, (x,y), (x+w,y+h), colour, 2)
        label = f"{ann.cls} ({score:.2f})"
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.38, 1)
        cv2.rectangle(img, (x, y-th-6), (x+tw+4, y), colour, -1)
        cv2.putText(img, label, (x+2, y-3), cv2.FONT_HERSHEY_SIMPLEX, 0.38, C_WHITE, 1, cv2.LINE_AA)
    else:
        _draw_dashed_rect(img, x, y, w, h, colour)
        label = f"MISSING: {ann.cls}"
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.4, 1)
        cv2.rectangle(img, (x, y-th-8), (x+tw+6, y), colour, -1)
        cv2.putText(img, label, (x+3, y-3), cv2.FONT_HERSHEY_SIMPLEX, 0.4, C_WHITE, 1, cv2.LINE_AA)


def draw_issue_highlight(img, issue: ComplianceIssue):
    if issue.bbox is None or len(issue.bbox) != 4:
        return
    x1, y1, x2, y2 = issue.bbox
    colour = C_MISSING if issue.severity == "ERROR" else C_WARNING
    _draw_dashed_rect(img, x1, y1, x2-x1, y2-y1, colour, dash=20, gap=10, thickness=3)
    cv2.putText(img, f"[{issue.rule}] {issue.message[:60]}",
                (x1+10, y1+55), cv2.FONT_HERSHEY_SIMPLEX, 0.5, colour, 2, cv2.LINE_AA)


def _draw_dashed_rect(img, x, y, w, h, colour, dash=12, gap=6, thickness=2):
    for side in ["top","bottom","left","right"]:
        if side == "top":    p,end,horiz = x,x+w,True;  fy=y
        elif side == "bottom": p,end,horiz = x,x+w,True;  fy=y+h
        elif side == "left":   p,end,horiz = y,y+h,False; fx=x
        else:                  p,end,horiz = y,y+h,False; fx=x+w
        pos = p
        while pos < end:
            stop = min(pos+dash, end)
            if horiz: cv2.line(img, (pos,fy), (stop,fy), colour, thickness)
            else:     cv2.line(img, (fx,pos), (fx,stop), colour, thickness)
            pos += dash + gap


def draw_summary_strip(img, all_issues: List[ComplianceIssue]):
    errors   = [i for i in all_issues if i.severity == "ERROR"]
    warnings = [i for i in all_issues if i.severity == "WARNING"]
    passed   = not errors
    strip_h  = 60
    h, w     = img.shape[:2]
    colour   = (20,120,20) if passed else (30,30,180)
    cv2.rectangle(img, (0,h-strip_h), (w,h), colour, -1)
    verdict = "COMPLIANT" if passed else f"NON-COMPLIANT  |  {len(errors)} errors  |  {len(warnings)} warnings"
    cv2.putText(img, verdict, (20, h-strip_h+38),
                cv2.FONT_HERSHEY_SIMPLEX, 1.0, C_WHITE, 2, cv2.LINE_AA)
    cv2.putText(img, f"CivGuard AI  |  {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                (w-500, h-strip_h+38), cv2.FONT_HERSHEY_SIMPLEX, 0.55, C_WHITE, 1, cv2.LINE_AA)


# ──────────────────────────────────────────────────────
# PROGRAMMATIC ENTRY POINT  (called by cv_analyser.py)
# ──────────────────────────────────────────────────────
def run_analysis(
    original_img: np.ndarray,
    test_img:     np.ndarray,
    annotations_data: dict,
) -> Tuple[np.ndarray, List[ComplianceIssue], int, int]:
    """
    Run the full compliance analysis and return:
      (annotated_output_image, issues_list, found_count, missing_count)
    """
    img_h, img_w = test_img.shape[:2]
    orig_gray = cv2.cvtColor(original_img, cv2.COLOR_BGR2GRAY)
    test_gray = cv2.cvtColor(test_img,     cv2.COLOR_BGR2GRAY)

    _cats, annotations = load_annotations_from_dict(annotations_data)
    attach_templates(original_img, annotations)

    found_anns, missing_anns, detected = [], [], []
    for ann in annotations:
        if ann.template is None:
            continue
        tg = cv2.cvtColor(ann.template, cv2.COLOR_BGR2GRAY)
        ok, score, _loc = match_one(test_gray, tg)
        if ok:
            found_anns.append((ann, score))
            detected.append(ann)
        else:
            missing_anns.append((ann, score))

    output = test_img.copy()
    draw_quadrant_grid(output, img_w, img_h)
    for ann, score in found_anns:
        if ann.class_id != 6:
            draw_detection(output, ann, True, score)
    for ann, score in missing_anns:
        if ann.class_id != 6:
            draw_detection(output, ann, False, score)

    all_issues: List[ComplianceIssue] = []
    all_issues.extend(check_rule1(detected, img_w, img_h))
    for issue in all_issues:
        draw_issue_highlight(output, issue)
    all_issues.extend(check_rule2(detected, output))
    all_issues.extend(check_rule3(detected))

    draw_summary_strip(output, all_issues)

    return output, all_issues, len(found_anns), len(missing_anns)


# ──────────────────────────────────────────────────────
# CLI ENTRY POINT
# ──────────────────────────────────────────────────────
def _cli_run(original_path, test_path, json_path, output_path):
    original = cv2.imread(original_path)
    test_img = cv2.imread(test_path)
    assert original is not None, f"Cannot load: {original_path}"
    assert test_img  is not None, f"Cannot load: {test_path}"

    with open(json_path) as f:
        annotations_data = json.load(f)

    output, issues, found, missing = run_analysis(original, test_img, annotations_data)

    cv2.imwrite(output_path, output)
    print(f"Output image: {output_path}")

    report_path = os.path.splitext(output_path)[0] + "_report.json"
    errors   = [i for i in issues if i.severity == "ERROR"]
    warnings = [i for i in issues if i.severity == "WARNING"]
    with open(report_path, "w") as f:
        json.dump({
            "timestamp":     datetime.now().isoformat(),
            "found_count":   found,
            "missing_count": missing,
            "overall":       "PASS" if not errors else "FAIL",
            "issues": [{"rule":i.rule,"severity":i.severity,"message":i.message} for i in issues],
        }, f, indent=2)
    print(f"Report: {report_path}")

    errors = [i for i in issues if i.severity == "ERROR"]
    print(f"\nResult: {'PASS' if not errors else 'FAIL'}  |  Found: {found}  |  Missing: {missing}  |  Issues: {len(issues)}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="CivGuard AI — Floor Plan Compliance Engine")
    ap.add_argument("--original", required=True)
    ap.add_argument("--test",     required=True)
    ap.add_argument("--json",     required=True)
    ap.add_argument("--output",   default="civguard_result.png")
    args = ap.parse_args()
    _cli_run(args.original, args.test, args.json, args.output)
