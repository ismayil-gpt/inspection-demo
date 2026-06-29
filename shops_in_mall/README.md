# Shop-In-Mall Floor Plan Demo

Standalone demo for pre-checking a mall shop floor plan image. It reads one image, shop area in square meters, and Mall NOC status, then returns JSON with the compliance decision, detected fire-safety items, recommendations, and optional annotated image output.

This is a demo pre-check only. It is not final Dubai Civil Defence approval.

## Setup

Install Python packages:

```powershell
pip install -r requirements.txt
```

Install Tesseract OCR using the steps in `tesseract_setup.md`.

## Run

Accepted demo example:

```powershell
python shop_mall_floor_plan_mock.py --image "C:\Users\ajuma\Downloads\Mall-Inspection-Demo-Floorplan.jpeg" --area-sqm 96 --mall-noc-uploaded
```

Missing-item demo example:

```powershell
python shop_mall_floor_plan_mock.py --image "C:\Users\ajuma\Downloads\Mall-Inspection-Demo-3.png" --area-sqm 96 --mall-noc-uploaded
```

Without Mall NOC:

```powershell
python shop_mall_floor_plan_mock.py --image "C:\Users\ajuma\Downloads\Mall-Inspection-Demo-Floorplan.jpeg" --area-sqm 96
```

## Inputs

- `--image`: path to a PNG/JPG/JPEG/BMP/TIF floor plan image.
- `--area-sqm`: shop area in square meters.
- `--mall-noc-uploaded`: include this flag when Mall NOC/landlord approval is available.

## JSON Output

The script prints JSON containing:

- `decision`: accepted/rejected/manual review status, score, confidence, and issues.
- `mall_shop_area`: area in sqm/sqft and demo validity.
- `detected_counts`: detected fire-safety item counts.
- `checklist`: pass/fail checklist.
- `recommendations`: remediation messages for failed checks.
- `annotated_image_path`: generated annotated image when floor-plan items are missing.
- `annotations`: circle coordinates and notes for suggested placements.
- `ocr_text_excerpt`: OCR text read from the drawing.
- `warnings`: demo and OCR notes.

## Notes

- Missing fire extinguishers are annotated with two suggested locations near common exit/entrance areas.
- Document/package issues such as missing Mall NOC are reported in JSON but not circled on the floor plan.
- Annotation placement is approximate and for demo visualization only.

