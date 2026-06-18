"""
Run this once to generate sample test blueprint PDFs in civguard-ai/test_blueprints/
Usage: python create_test_docs.py
"""

import os
from reportlab.lib.pagesizes import A3, landscape
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.pdfgen import canvas

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "test_blueprints")
os.makedirs(OUT_DIR, exist_ok=True)


def draw_room(c, x, y, w, h, label="", sub=""):
    c.rect(x, y, w, h)
    c.setFont("Helvetica-Bold", 6)
    c.drawCentredString(x + w / 2, y + h / 2 + 4, label)
    if sub:
        c.setFont("Helvetica", 5)
        c.drawCentredString(x + w / 2, y + h / 2 - 5, sub)


def draw_door(c, x, y, w=20, vertical=False):
    if vertical:
        c.rect(x, y, 3, w)
    else:
        c.rect(x, y, w, 3)
    c.setFont("Helvetica", 4)
    c.drawCentredString(x + w / 2, y - 6, "EXIT" if w >= 18 else "door")


def draw_title(c, W, H, title, subtitle, ref, scenario):
    # Title block at bottom right
    bx, by, bw, bh = W - 160 * mm, 10 * mm, 150 * mm, 35 * mm
    c.setStrokeColor(colors.HexColor("#003366"))
    c.setLineWidth(1.5)
    c.rect(bx, by, bw, bh)
    c.setFillColor(colors.HexColor("#003366"))
    c.rect(bx, by + 22 * mm, bw, 13 * mm, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(bx + bw / 2, by + 29 * mm, "DUBAI CIVIL DEFENCE")
    c.setFont("Helvetica", 7)
    c.drawCentredString(bx + bw / 2, by + 24.5 * mm, "BUILDING PLAN SUBMISSION")
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(bx + 4 * mm, by + 18 * mm, title)
    c.setFont("Helvetica", 6.5)
    c.drawString(bx + 4 * mm, by + 13.5 * mm, subtitle)
    c.setFont("Helvetica", 6)
    c.drawString(bx + 4 * mm, by + 9 * mm, f"Ref: {ref}")
    c.drawString(bx + 4 * mm, by + 5 * mm, f"Test Scenario: {scenario}")

    # North arrow
    c.setFillColor(colors.HexColor("#003366"))
    c.setFont("Helvetica-Bold", 7)
    c.drawString(18 * mm, 14 * mm, "N ↑")

    # Scale bar
    c.setStrokeColor(colors.black)
    c.setLineWidth(1)
    sx, sy = 18 * mm, 10 * mm
    for i in range(5):
        c.setFillColor(colors.black if i % 2 == 0 else colors.white)
        c.rect(sx + i * 10 * mm, sy, 10 * mm, 3 * mm, fill=1)
    c.setFillColor(colors.black)
    c.setFont("Helvetica", 5)
    c.drawCentredString(sx, sy - 4, "0")
    c.drawCentredString(sx + 25 * mm, sy - 4, "5m")
    c.drawCentredString(sx + 50 * mm, sy - 4, "10m")


def draw_legend(c, x, y):
    items = [
        (colors.HexColor("#22c55e"), "Compliant Exit (≥900 mm)"),
        (colors.HexColor("#ef4444"), "Non-Compliant Door (<900 mm)"),
        (colors.HexColor("#3b82f6"), "Fire Extinguisher"),
        (colors.HexColor("#f97316"), "Smoke Detector"),
        (colors.HexColor("#8b5cf6"), "Fire Hose Reel"),
    ]
    c.setFont("Helvetica-Bold", 6)
    c.drawString(x, y + 5 * mm, "LEGEND")
    c.setLineWidth(0.5)
    for i, (col, label) in enumerate(items):
        iy = y - i * 7 * mm
        c.setFillColor(col)
        c.rect(x, iy - 1 * mm, 5 * mm, 4 * mm, fill=1, stroke=0)
        c.setFillColor(colors.black)
        c.setFont("Helvetica", 5.5)
        c.drawString(x + 7 * mm, iy, label)


# ─────────────────────────────────────────────────────────────────────────────
# Scenario 1 — COMPLIANT: Retail Shop (small, well-designed)
# ─────────────────────────────────────────────────────────────────────────────
def build_pass_shop():
    path = os.path.join(OUT_DIR, "TEST_PASS_RetailShop.pdf")
    W, H = landscape(A3)
    c = canvas.Canvas(path, pagesize=(W, H))

    # Background grid
    c.setStrokeColor(colors.HexColor("#e5e7eb"))
    c.setLineWidth(0.3)
    for xi in range(0, int(W / mm), 10):
        c.line(xi * mm, 0, xi * mm, H)
    for yi in range(0, int(H / mm), 10):
        c.line(0, yi * mm, W, yi * mm)

    c.setStrokeColor(colors.black)
    c.setLineWidth(1.2)
    c.setFillColor(colors.white)

    ox, oy = 60 * mm, 60 * mm  # floor plan origin

    # ── Outer walls (400 m² shop, 20×20 m footprint) ──
    FW, FH = 120 * mm, 120 * mm   # 20 m × 20 m @ 1:100 (6mm=1m)
    c.setLineWidth(2.5)
    c.rect(ox, oy, FW, FH)

    c.setLineWidth(1.0)

    # Interior rooms
    draw_room(c, ox, oy + 80 * mm, 40 * mm, 40 * mm, "Storage", "10×10 m")
    draw_room(c, ox + 40 * mm, oy + 80 * mm, 80 * mm, 40 * mm, "Staff Office", "20×10 m")
    draw_room(c, ox, oy, 30 * mm, 40 * mm, "WC", "5×7 m")
    draw_room(c, ox + 30 * mm, oy, 90 * mm, 40 * mm, "Main Retail Floor", "15×10 m")
    draw_room(c, ox, oy + 40 * mm, 120 * mm, 40 * mm, "MAIN SALES AREA", "20×10 m — 200 m²")

    # Exits (green = compliant, ≥900 mm)
    c.setStrokeColor(colors.HexColor("#22c55e"))
    c.setLineWidth(2)
    # Main exit front wall
    c.rect(ox + 45 * mm, oy, 16 * mm, 3 * mm)   # 1000 mm door
    c.setFont("Helvetica-Bold", 5)
    c.setFillColor(colors.HexColor("#22c55e"))
    c.drawCentredString(ox + 53 * mm, oy - 6 * mm, "EXIT 1 — 1000mm")
    # Secondary exit side wall
    c.rect(ox + FW, oy + 50 * mm, 3 * mm, 16 * mm)
    c.drawCentredString(ox + FW + 12 * mm, oy + 58 * mm, "EXIT 2 — 1000mm")

    # Corridor
    c.setStrokeColor(colors.black)
    c.setFillColor(colors.HexColor("#f0fdf4"))
    c.setLineWidth(0.5)
    c.rect(ox + 30 * mm, oy + 40 * mm, 90 * mm, 8 * mm, fill=1)
    c.setFillColor(colors.black)
    c.setFont("Helvetica", 5)
    c.drawCentredString(ox + 75 * mm, oy + 44 * mm, "CORRIDOR — 1400 mm wide")

    # Fire extinguishers (blue circles)
    c.setFillColor(colors.HexColor("#3b82f6"))
    for fx, fy in [(ox + 20 * mm, oy + 60 * mm), (ox + 90 * mm, oy + 60 * mm)]:
        c.circle(fx, fy, 3 * mm, fill=1)
    c.setFont("Helvetica", 4.5)
    c.setFillColor(colors.black)
    c.drawString(ox + 22 * mm, oy + 55 * mm, "FE")
    c.drawString(ox + 92 * mm, oy + 55 * mm, "FE")

    # Smoke detectors (orange squares)
    c.setFillColor(colors.HexColor("#f97316"))
    positions_sd = [(ox + 30 * mm, oy + 30 * mm), (ox + 80 * mm, oy + 30 * mm),
                    (ox + 30 * mm, oy + 100 * mm), (ox + 80 * mm, oy + 100 * mm)]
    for dx, dy in positions_sd:
        c.rect(dx - 2.5 * mm, dy - 2.5 * mm, 5 * mm, 5 * mm, fill=1)
    c.setFillColor(colors.black)
    c.setFont("Helvetica", 4.5)
    c.drawString(ox + 31 * mm, oy + 103 * mm, "SD")
    c.drawString(ox + 81 * mm, oy + 103 * mm, "SD")

    # Dimensions
    c.setStrokeColor(colors.HexColor("#6b7280"))
    c.setLineWidth(0.5)
    c.setFont("Helvetica", 5.5)
    c.drawCentredString(ox + FW / 2, oy - 14 * mm, "20,000 mm (20 m)")
    c.drawCentredString(ox - 14 * mm, oy + FH / 2, "20,000 mm", charSpace=0)

    # Annotations
    c.setFillColor(colors.HexColor("#16a34a"))
    c.setFont("Helvetica-Bold", 6)
    c.drawString(ox + 5 * mm, oy + 155 * mm, "✓ 2 exits provided  |  ✓ Corridor width 1400mm  |  ✓ Travel distance <30m  |  ✓ 2 smoke detectors")
    c.drawString(ox + 5 * mm, oy + 148 * mm, "✓ 2 fire extinguishers  |  ✓ Exit signs at all exits  |  ✓ Emergency lighting provided")

    c.setFillColor(colors.black)
    draw_title(c, W, H,
               "RETAIL SHOP — GROUND FLOOR PLAN",
               "Al Mankhool Commercial Centre, Dubai   |   GF Unit 04",
               "DCD-TEST-PASS-001", "PASS — Compliant Submission")
    draw_legend(c, W - 90 * mm, H - 65 * mm)

    c.save()
    print(f"  Created: {path}")


# ─────────────────────────────────────────────────────────────────────────────
# Scenario 2 — FAIL: Multi-Floor Building (missing sprinklers + narrow exits)
# ─────────────────────────────────────────────────────────────────────────────
def build_fail_building():
    path = os.path.join(OUT_DIR, "TEST_FAIL_MultiFloorBuilding.pdf")
    W, H = landscape(A3)
    c = canvas.Canvas(path, pagesize=(W, H))

    c.setStrokeColor(colors.HexColor("#e5e7eb"))
    c.setLineWidth(0.3)
    for xi in range(0, int(W / mm), 10):
        c.line(xi * mm, 0, xi * mm, H)
    for yi in range(0, int(H / mm), 10):
        c.line(0, yi * mm, W, yi * mm)

    # ── Typical floor plate — 5-storey, 2400 m², NO sprinklers shown ──
    c.setStrokeColor(colors.black)
    c.setLineWidth(2)
    c.setFillColor(colors.white)
    ox, oy = 50 * mm, 55 * mm
    FW, FH = 140 * mm, 90 * mm   # ≈ 35m × 22.5m per floor

    c.rect(ox, oy, FW, FH)
    c.setLineWidth(1)

    draw_room(c, ox, oy + 50 * mm, 35 * mm, 40 * mm, "Office Suite A", "35 pax")
    draw_room(c, ox + 35 * mm, oy + 50 * mm, 35 * mm, 40 * mm, "Office Suite B", "35 pax")
    draw_room(c, ox + 70 * mm, oy + 50 * mm, 35 * mm, 40 * mm, "Office Suite C", "35 pax")
    draw_room(c, ox + 105 * mm, oy + 50 * mm, 35 * mm, 40 * mm, "Office Suite D", "35 pax")
    draw_room(c, ox, oy, 45 * mm, 50 * mm, "Reception / Lobby", "40 pax")
    draw_room(c, ox + 45 * mm, oy, 50 * mm, 50 * mm, "Open Plan", "120 pax")
    draw_room(c, ox + 95 * mm, oy, 25 * mm, 50 * mm, "Server Rm", "")
    draw_room(c, ox + 120 * mm, oy, 20 * mm, 50 * mm, "Store", "")

    # Central corridor
    c.setFillColor(colors.HexColor("#fef9c3"))
    c.setLineWidth(0.5)
    c.rect(ox + 35 * mm, oy + 50 * mm, 105 * mm, 6 * mm, fill=1)
    c.setFillColor(colors.black)
    c.setFont("Helvetica", 5)
    c.drawCentredString(ox + 87 * mm, oy + 53 * mm, "CORRIDOR — 950 mm ← NON-COMPLIANT (min 1200 mm)")

    # Non-compliant exits (red)
    c.setStrokeColor(colors.HexColor("#ef4444"))
    c.setLineWidth(2)
    # Front exit — only 800 mm
    c.rect(ox + 55 * mm, oy, 13 * mm, 3 * mm)
    c.setFillColor(colors.HexColor("#ef4444"))
    c.setFont("Helvetica-Bold", 5)
    c.drawCentredString(ox + 62 * mm, oy - 6 * mm, "EXIT 1 — 800mm ✗")

    # Rear emergency exit — also 800 mm
    c.rect(ox + 100 * mm, oy + FH, 13 * mm, 3 * mm)
    c.drawCentredString(ox + 107 * mm, oy + FH + 6 * mm, "EXIT 2 — 800mm ✗")

    # Staircase (narrow)
    c.setStrokeColor(colors.HexColor("#dc2626"))
    c.setFillColor(colors.HexColor("#fee2e2"))
    c.rect(ox + FW - 18 * mm, oy + 20 * mm, 15 * mm, 25 * mm, fill=1)
    c.setFillColor(colors.HexColor("#dc2626"))
    c.setFont("Helvetica-Bold", 5.5)
    c.drawCentredString(ox + FW - 10 * mm, oy + 33 * mm, "STAIR")
    c.drawCentredString(ox + FW - 10 * mm, oy + 27 * mm, "900mm ✗")

    # NO sprinkler annotation
    c.setFillColor(colors.HexColor("#ef4444"))
    c.setFont("Helvetica-Bold", 7)
    c.drawCentredString(ox + 80 * mm, oy + FH + 20 * mm,
                        "⚠  NO SPRINKLER SYSTEM SHOWN  (REQUIRED: 5-STOREY BUILDING)")

    # Building elevation sketch (side view)
    ex, ey = ox + FW + 25 * mm, oy
    ew, eh_per = 30 * mm, 18 * mm
    c.setStrokeColor(colors.black)
    c.setLineWidth(1)
    for floor in range(5):
        c.setFillColor(colors.HexColor("#dbeafe") if floor < 4 else colors.HexColor("#bfdbfe"))
        c.rect(ex, ey + floor * eh_per, ew, eh_per, fill=1)
        c.setFillColor(colors.black)
        c.setFont("Helvetica", 5.5)
        c.drawCentredString(ex + ew / 2, ey + floor * eh_per + 7 * mm, f"Floor {floor + 1}")
    c.setFont("Helvetica-Bold", 6)
    c.drawCentredString(ex + ew / 2, ey + 5 * eh_per + 5 * mm, "ELEVATION")
    ht = 5 * 4.0   # ~20 m
    c.setFont("Helvetica", 5.5)
    c.drawString(ex + ew + 2 * mm, ey + 5 * eh_per / 2, f"≈{ht:.0f}m")

    # Violation list
    c.setFillColor(colors.HexColor("#dc2626"))
    c.setFont("Helvetica-Bold", 6)
    vx, vy = ox, oy - 20 * mm
    violations = [
        "✗ No sprinkler system (5-storey building — mandatory per DCD Rule 5)",
        "✗ Exit widths 800 mm — non-compliant (min 900 mm, recommended 1000 mm)",
        "✗ Staircase width 900 mm — non-compliant (min 1200 mm)",
        "✗ Corridor width 950 mm — non-compliant (min 1200 mm)",
    ]
    for i, v in enumerate(violations):
        c.drawString(vx, vy - i * 7 * mm, v)

    c.setFillColor(colors.black)
    draw_title(c, W, H,
               "OFFICE BUILDING — TYPICAL FLOOR PLAN (FLOORS 1–5)",
               "Business Bay Tower, Dubai   |   5 Floors, 2400 m² GFA, Occ: 140/floor",
               "DCD-TEST-FAIL-001", "FAIL — Multiple Critical Violations")
    draw_legend(c, W - 90 * mm, H - 65 * mm)

    c.save()
    print(f"  Created: {path}")


# ─────────────────────────────────────────────────────────────────────────────
# Scenario 3 — PARTIAL FAIL: Restaurant with high occupancy
# ─────────────────────────────────────────────────────────────────────────────
def build_partial_restaurant():
    path = os.path.join(OUT_DIR, "TEST_PARTIAL_Restaurant.pdf")
    W, H = landscape(A3)
    c = canvas.Canvas(path, pagesize=(W, H))

    c.setStrokeColor(colors.HexColor("#e5e7eb"))
    c.setLineWidth(0.3)
    for xi in range(0, int(W / mm), 10):
        c.line(xi * mm, 0, xi * mm, H)
    for yi in range(0, int(H / mm), 10):
        c.line(0, yi * mm, W, yi * mm)

    c.setStrokeColor(colors.black)
    c.setLineWidth(2)
    c.setFillColor(colors.white)
    ox, oy = 55 * mm, 55 * mm
    FW, FH = 130 * mm, 100 * mm

    c.rect(ox, oy, FW, FH)
    c.setLineWidth(1)

    draw_room(c, ox, oy + 60 * mm, 40 * mm, 40 * mm, "Kitchen", "≈80 m²")
    draw_room(c, ox + 40 * mm, oy + 60 * mm, 30 * mm, 40 * mm, "Prep Area", "")
    draw_room(c, ox + 70 * mm, oy + 60 * mm, 60 * mm, 40 * mm, "VIP Dining", "60 covers")
    draw_room(c, ox, oy, 40 * mm, 60 * mm, "Bar / Lounge", "80 pax")
    draw_room(c, ox + 40 * mm, oy, 90 * mm, 60 * mm, "MAIN DINING HALL", "300 covers")

    # Corridor
    c.setFillColor(colors.HexColor("#fff7ed"))
    c.rect(ox + 40 * mm, oy + 58 * mm, 90 * mm, 4 * mm, fill=1)
    c.setFillColor(colors.black)
    c.setFont("Helvetica", 5)
    c.drawCentredString(ox + 85 * mm, oy + 59.5 * mm, "CORRIDOR — 1300 mm (OK)")

    # Main entrance — compliant
    c.setStrokeColor(colors.HexColor("#22c55e"))
    c.setLineWidth(2)
    c.rect(ox + 50 * mm, oy, 18 * mm, 3 * mm)
    c.setFillColor(colors.HexColor("#22c55e"))
    c.setFont("Helvetica-Bold", 5)
    c.drawCentredString(ox + 59 * mm, oy - 6 * mm, "MAIN ENTRANCE — 1200mm ✓")

    # Emergency exit — too narrow
    c.setStrokeColor(colors.HexColor("#ef4444"))
    c.setLineWidth(2)
    c.rect(ox + 100 * mm, oy, 11 * mm, 3 * mm)
    c.setFillColor(colors.HexColor("#ef4444"))
    c.setFont("Helvetica-Bold", 5)
    c.drawCentredString(ox + 106 * mm, oy - 6 * mm, "EMERGENCY EXIT — 750mm ✗")

    # Fire extinguishers
    c.setFillColor(colors.HexColor("#3b82f6"))
    for fx, fy in [(ox + 20 * mm, oy + 30 * mm), (ox + 80 * mm, oy + 30 * mm), (ox + 10 * mm, oy + 80 * mm)]:
        c.circle(fx, fy, 3 * mm, fill=1)

    # Smoke detectors
    c.setFillColor(colors.HexColor("#f97316"))
    sds = [(ox + 20 * mm, oy + 90 * mm), (ox + 55 * mm, oy + 90 * mm),
           (ox + 90 * mm, oy + 90 * mm), (ox + 30 * mm, oy + 40 * mm),
           (ox + 80 * mm, oy + 40 * mm), (ox + 110 * mm, oy + 40 * mm)]
    for dx, dy in sds:
        c.rect(dx - 2.5 * mm, dy - 2.5 * mm, 5 * mm, 5 * mm, fill=1)

    # Fire hose reel — present
    c.setFillColor(colors.HexColor("#8b5cf6"))
    c.circle(ox + FW - 10 * mm, oy + FH - 10 * mm, 4 * mm, fill=1)
    c.setFillColor(colors.black)
    c.setFont("Helvetica", 4.5)
    c.drawCentredString(ox + FW - 10 * mm, oy + FH - 17 * mm, "FHR")

    # Travel distance annotation
    c.setStrokeColor(colors.HexColor("#6b7280"))
    c.setDash(3, 3)
    c.setLineWidth(0.8)
    c.line(ox + 120 * mm, oy + 30 * mm, ox + 108 * mm, oy + 3 * mm)
    c.setDash()
    c.setFillColor(colors.HexColor("#6b7280"))
    c.setFont("Helvetica", 5)
    c.drawString(ox + 122 * mm, oy + 28 * mm, "Max travel: 65m ✗")

    # Result summary
    c.setFillColor(colors.HexColor("#f59e0b"))
    c.setFont("Helvetica-Bold", 6)
    annotations = [
        "✓ Main entrance width 1200 mm",
        "✓ Corridor width 1300 mm",
        "✓ 6 smoke detectors provided",
        "✗ Emergency exit width 750 mm (min 900 mm)",
        "✗ Max travel distance 65 m exceeds limit (non-sprinklered: 45 m)",
        "✗ High occupancy (440 pax) — 3rd exit required",
    ]
    for i, ann in enumerate(annotations):
        col = colors.HexColor("#16a34a") if ann.startswith("✓") else colors.HexColor("#dc2626")
        c.setFillColor(col)
        c.drawString(ox, oy - 20 * mm - i * 7 * mm, ann)

    c.setFillColor(colors.black)
    draw_title(c, W, H,
               "RESTAURANT — GROUND FLOOR PLAN",
               "DIFC Food & Beverage Outlet, Dubai   |   GF, 650 m², 440 covers + staff",
               "DCD-TEST-PARTIAL-001", "FAIL — 3 Violations (exits + travel distance)")
    draw_legend(c, W - 90 * mm, H - 65 * mm)

    c.save()
    print(f"  Created: {path}")


if __name__ == "__main__":
    print("Generating test blueprint PDFs...")
    build_pass_shop()
    build_fail_building()
    build_partial_restaurant()
    print("\nDone. Files are in civguard-ai/test_blueprints/")
    print("\nHow to use:")
    print("  TEST_PASS_RetailShop.pdf       → submit as 'Shop/Fit-out', area ~400m², occupancy ~30")
    print("  TEST_FAIL_MultiFloorBuilding.pdf → submit as 'New Building', 5 floors, NOT sprinklered")
    print("  TEST_PARTIAL_Restaurant.pdf    → submit as 'Shop/Fit-out', area ~650m², occupancy ~440")
