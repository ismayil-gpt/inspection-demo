"""
Demo analyser — derives realistic compliance extraction from submitted form data.
Switch to real Claude Vision by setting USE_REAL_AI=true in .env.
"""

import os
import random
from rules_engine import check_compliance

USE_REAL_AI = os.environ.get("USE_REAL_AI", "false").lower() == "true"


def analyse_blueprint(file_bytes: bytes, file_type: str, form_data: dict) -> dict:
    if USE_REAL_AI:
        return _analyse_with_claude(file_bytes, file_type, form_data)
    return _analyse_demo(form_data)


# ---------------------------------------------------------------------------
# Demo mode
# ---------------------------------------------------------------------------

def _analyse_demo(form_data: dict) -> dict:
    floor_count    = _num(form_data.get("number_of_floors") or form_data.get("floor_number"), 2)
    building_height = _num(form_data.get("building_height_m"), floor_count * 3.5)
    total_area     = _num(form_data.get("total_area_m2") or form_data.get("unit_area_m2"), 300)
    occupancy      = _num(form_data.get("estimated_occupancy"), 30)
    sprinklered    = str(form_data.get("sprinklered", "false")).lower() in ("true", "1", "yes")

    # ---------- derive realistic (sometimes failing) values ----------

    # Exit width: small units often have narrow doors
    if total_area < 100:
        exit_widths = [random.choice([800, 850, 900, 950])]   # may fail
    elif total_area < 300:
        exit_widths = [random.choice([900, 950, 1000]), 1000]
    else:
        exit_widths = [1000, 1100, 1200]

    # Exit count: single-exit shops often fail
    if occupancy <= 50 and total_area <= 93:
        exit_count = 1          # marginal — may fail rule 2
    elif occupancy <= 100:
        exit_count = 2
    else:
        exit_count = 3

    # Corridor width: older fit-outs often too narrow
    if total_area < 150:
        corridor_widths = [random.choice([900, 1000, 1100, 1200, 1300])]
    else:
        corridor_widths = [1200, 1400]

    # Travel distance: large open-plan spaces can exceed limits
    max_travel = total_area / (exit_count * 2.5)
    max_travel = round(min(max_travel, 70), 1)

    # Sprinkler: required if ≥3 floors or ≥14 m — use actual form values
    needs_sprinkler = floor_count >= 3 or building_height >= 14
    has_sprinkler   = sprinklered or needs_sprinkler  # if required, assume present unless user said no

    # Smoke detector coverage
    detector_coverage = round(total_area / max(1, int(total_area / 55)), 1)

    # Extinguisher
    ext_count    = max(1, int(total_area / 200))
    ext_distance = round(total_area / (ext_count * 4), 1)

    # Fire truck access: site plans often missing from shop submissions
    sub_type = form_data.get("submission_type", "")
    truck_access = 5.0 if sub_type == "new_building" else None   # shops → unverifiable

    extracted = {
        "building_height_m":            building_height,
        "floor_count":                  floor_count,
        "total_floor_area_m2":          total_area,
        "estimated_occupancy":          occupancy,
        "exit_count":                   exit_count,
        "exit_widths_mm":               exit_widths,
        "corridor_widths_mm":           corridor_widths,
        "staircase_widths_mm":          [1200] if floor_count > 1 else None,
        "max_travel_distance_m":        max_travel,
        "dead_end_length_m":            round(random.uniform(2, 7), 1),
        "has_sprinkler_system":         has_sprinkler,
        "sprinkler_coverage_m2_per_head": 11.5 if has_sprinkler else None,
        "smoke_detector_count":         max(1, int(total_area / 50)),
        "smoke_detector_coverage_m2":   detector_coverage,
        "fire_extinguisher_count":      ext_count,
        "max_distance_to_extinguisher_m": ext_distance,
        "fire_hose_reel_present":       floor_count >= 2,
        "emergency_lighting_present":   random.choice([True, True, True, False]),
        "exit_signs_present":           True,
        "fire_truck_access_width_m":    truck_access,
        "nearest_hydrant_distance_m":   round(random.uniform(30, 120), 1),
        "assembly_point_marked":        sub_type == "new_building",
        "fire_compartment_max_area_m2": min(total_area, 1800),
        "fire_door_ratings_present":    floor_count >= 2,
        "page_notes":                   _page_notes(form_data),
    }

    result = check_compliance(extracted, form_data)
    result["extracted_data"] = extracted
    result["pages_analysed"] = 1
    result["processing_time_s"] = round(random.uniform(1.8, 3.5), 2)
    result["summary"] = _summary(result, form_data)
    return result


def _page_notes(form_data: dict) -> str:
    sub_type = form_data.get("submission_type", "building")
    name = form_data.get("project_name") or form_data.get("shop_name") or "the submitted property"
    return (f"Floor plan for {name}. Shows room layout, exit locations, "
            f"corridor dimensions, and fire safety provisions for this {sub_type.replace('_', ' ')}.")


def _summary(result: dict, form_data: dict) -> str:
    verdict   = result["overall_result"]
    passes    = result["pass_count"]
    failures  = result["fail_count"]
    critical  = result["critical_failures"]
    unverif   = result["unverifiable_count"]
    name      = form_data.get("project_name") or form_data.get("shop_name") or "The submitted property"

    if verdict == "approved":
        return (
            f"{name} has passed all verifiable UAE Fire and Life Safety Code checks "
            f"({passes}/10 rules confirmed compliant). "
            f"No critical compliance failures were identified in the submitted blueprint. "
            f"{f'{unverif} rule(s) could not be fully verified from the drawings and are flagged for manual site review. ' if unverif else ''}"
            f"This result is pending verification by a DCD officer before it becomes official."
        )
    else:
        failed_names = [c["name"] for c in result.get("checks", []) if not c.get("passed") and c.get("verifiable", True)]
        failed_str   = "; ".join(failed_names[:3])
        return (
            f"{name} has {critical} critical compliance failure(s) under the UAE Fire and Life Safety Code "
            f"({passes}/10 rules passed). "
            f"Key issues identified: {failed_str}. "
            f"All CRITICAL items must be corrected and resubmitted before approval can be granted. "
            f"Please refer to the detailed checklist below for specific requirements."
        )


def _num(val, default):
    try:
        return float(val) if val not in (None, "", "null") else float(default)
    except (ValueError, TypeError):
        return float(default)


# ---------------------------------------------------------------------------
# Real AI mode (Claude Vision) — enabled with USE_REAL_AI=true in .env
# ---------------------------------------------------------------------------

def _analyse_with_claude(file_bytes: bytes, file_type: str, form_data: dict) -> dict:
    import json
    import anthropic
    from pdf_processor import pdf_to_images, image_to_base64

    CLAUDE_MODEL = "claude-sonnet-4-6"
    EXTRACTION_PROMPT = """You are a certified fire safety and building compliance inspector for the UAE.
Analyse the architectural blueprint image provided and extract compliance data.
Return ONLY a valid JSON object with the following fields.
If a value cannot be determined from the drawing, set it to null.
Do not include any text outside the JSON object.
{
  "building_height_m": number|null, "floor_count": number|null,
  "total_floor_area_m2": number|null, "estimated_occupancy": number|null,
  "exit_count": number|null, "exit_widths_mm": [number]|null,
  "corridor_widths_mm": [number]|null, "staircase_widths_mm": [number]|null,
  "max_travel_distance_m": number|null, "dead_end_length_m": number|null,
  "has_sprinkler_system": boolean|null, "sprinkler_coverage_m2_per_head": number|null,
  "smoke_detector_count": number|null, "smoke_detector_coverage_m2": number|null,
  "fire_extinguisher_count": number|null, "max_distance_to_extinguisher_m": number|null,
  "fire_hose_reel_present": boolean|null, "emergency_lighting_present": boolean|null,
  "exit_signs_present": boolean|null, "fire_truck_access_width_m": number|null,
  "nearest_hydrant_distance_m": number|null, "assembly_point_marked": boolean|null,
  "fire_compartment_max_area_m2": number|null, "fire_door_ratings_present": boolean|null,
  "page_notes": "string"
}"""

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    pages = pdf_to_images(file_bytes) if file_type in ("application/pdf", "pdf") else [
        {"page_number": 1, "base64": image_to_base64(file_bytes),
         "media_type": "image/jpeg" if file_type in ("jpg", "jpeg", "image/jpeg") else "image/png"}
    ]

    all_extracted = []
    for page in pages:
        content = [
            {"type": "image", "source": {"type": "base64",
             "media_type": page.get("media_type", "image/jpeg"), "data": page["base64"]}},
            {"type": "text", "text": EXTRACTION_PROMPT},
        ]
        raw = client.messages.create(model=CLAUDE_MODEL, max_tokens=2048,
                                     messages=[{"role": "user", "content": content}]).content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1][4:] if raw.split("```")[1].startswith("json") else raw.split("```")[1]
        try:
            extracted = json.loads(raw)
        except json.JSONDecodeError:
            extracted = {}
        extracted["_page"] = page["page_number"]
        all_extracted.append(extracted)

    merged = _merge(all_extracted)
    result = check_compliance(merged, form_data)
    result["extracted_data"] = merged
    result["pages_analysed"] = len(pages)

    summary_resp = client.messages.create(
        model=CLAUDE_MODEL, max_tokens=300,
        messages=[{"role": "user", "content":
            f"Write a 2-3 sentence professional summary of this UAE fire code review. "
            f"Verdict: {result['overall_result'].upper()}. Passed: {result['pass_count']}/10. "
            f"Critical failures: {result['critical_failures']}."}]
    )
    result["summary"] = summary_resp.content[0].text.strip()
    return result


def _merge(pages: list) -> dict:
    merged = {}
    list_fields = {"exit_widths_mm", "corridor_widths_mm", "staircase_widths_mm"}
    for page in pages:
        for key, value in page.items():
            if key.startswith("_"):
                continue
            if key in list_fields:
                existing = merged.get(key) or []
                if isinstance(value, list):
                    existing.extend(value)
                merged[key] = existing or None
            elif key not in merged or merged[key] is None:
                merged[key] = value
    return merged
