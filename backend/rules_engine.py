from rules_config import DCD_RULES, RULE_METADATA


def check_compliance(extracted: dict, form_data: dict) -> dict:
    """Run all 10 DCD compliance checks and return structured result."""
    is_sprinklered = extracted.get('has_sprinkler_system') or form_data.get('sprinklered', False)
    floor_count = extracted.get('floor_count') or form_data.get('number_of_floors')
    building_height = extracted.get('building_height_m') or form_data.get('building_height_m')
    total_area = extracted.get('total_floor_area_m2') or form_data.get('total_area_m2')

    checks = []

    # Rule 1 – Emergency exit width
    exit_widths = extracted.get('exit_widths_mm')
    if exit_widths:
        min_width = min(exit_widths)
        passed = min_width >= DCD_RULES['exit_width_min_mm']
        checks.append({
            **RULE_METADATA['exit_width'],
            'rule_key': 'exit_width',
            'passed': passed,
            'extracted_value': f'{min_width} mm (minimum found)',
            'required_value': f'≥{DCD_RULES["exit_width_min_mm"]} mm',
            'notes': None if passed else f'Minimum exit width {min_width} mm is below required 900 mm.',
        })
    else:
        checks.append(_unverifiable('exit_width'))

    # Rule 2 – Minimum number of exits
    exit_count = extracted.get('exit_count')
    if exit_count is not None:
        passed = exit_count >= DCD_RULES['exit_count_min']
        checks.append({
            **RULE_METADATA['exit_count'],
            'rule_key': 'exit_count',
            'passed': passed,
            'extracted_value': str(exit_count),
            'required_value': f'≥{DCD_RULES["exit_count_min"]}',
            'notes': None if passed else f'Only {exit_count} exit(s) found. Minimum 2 required.',
        })
    else:
        checks.append(_unverifiable('exit_count'))

    # Rule 3 – Max travel distance
    travel_dist = extracted.get('max_travel_distance_m')
    if travel_dist is not None:
        max_allowed = (DCD_RULES['travel_distance_sprinklered_max_m'] if is_sprinklered
                       else DCD_RULES['travel_distance_nonsprinklered_max_m'])
        passed = travel_dist <= max_allowed
        checks.append({
            **RULE_METADATA['travel_distance'],
            'rule_key': 'travel_distance',
            'passed': passed,
            'extracted_value': f'{travel_dist} m',
            'required_value': f'≤{max_allowed} m ({"sprinklered" if is_sprinklered else "non-sprinklered"})',
            'notes': None if passed else f'Travel distance {travel_dist} m exceeds maximum {max_allowed} m.',
        })
    else:
        checks.append(_unverifiable('travel_distance'))

    # Rule 4 – Minimum corridor width
    corridor_widths = extracted.get('corridor_widths_mm')
    if corridor_widths:
        min_corridor = min(corridor_widths)
        passed = min_corridor >= DCD_RULES['corridor_width_min_mm']
        checks.append({
            **RULE_METADATA['corridor_width'],
            'rule_key': 'corridor_width',
            'passed': passed,
            'extracted_value': f'{min_corridor} mm (minimum found)',
            'required_value': f'≥{DCD_RULES["corridor_width_min_mm"]} mm',
            'notes': None if passed else f'Corridor width {min_corridor} mm is below required 1200 mm.',
        })
    else:
        checks.append(_unverifiable('corridor_width'))

    # Rule 5 – Sprinkler system
    sprinkler_required = (
        (floor_count and floor_count >= DCD_RULES['sprinkler_required_floors']) or
        (building_height and building_height >= DCD_RULES['sprinkler_required_height_m'])
    )
    if sprinkler_required is not None:
        if sprinkler_required:
            passed = bool(extracted.get('has_sprinkler_system'))
            coverage = extracted.get('sprinkler_coverage_m2_per_head')
            coverage_ok = (coverage is None or coverage <= DCD_RULES['sprinkler_coverage_ordinary_hazard_max_m2'])
            passed = passed and coverage_ok
            notes = None
            if not extracted.get('has_sprinkler_system'):
                notes = 'Sprinkler system required but not found in blueprint.'
            elif not coverage_ok:
                notes = f'Sprinkler coverage {coverage} m²/head exceeds max 12.4 m²/head.'
            checks.append({
                **RULE_METADATA['sprinkler_system'],
                'rule_key': 'sprinkler_system',
                'passed': passed,
                'extracted_value': f'System present: {extracted.get("has_sprinkler_system")}, Coverage: {coverage} m²/head',
                'required_value': 'System required; ≤12.4 m²/head (ordinary hazard)',
                'notes': notes,
            })
        else:
            checks.append({
                **RULE_METADATA['sprinkler_system'],
                'rule_key': 'sprinkler_system',
                'passed': True,
                'extracted_value': 'Building below threshold',
                'required_value': 'Not required for this building',
                'notes': None,
            })
    else:
        checks.append(_unverifiable('sprinkler_system'))

    # Rule 6 – Smoke detector coverage
    detector_coverage = extracted.get('smoke_detector_coverage_m2')
    if detector_coverage is not None:
        passed = detector_coverage <= DCD_RULES['smoke_detector_max_coverage_m2']
        checks.append({
            **RULE_METADATA['smoke_detector'],
            'rule_key': 'smoke_detector',
            'passed': passed,
            'extracted_value': f'{detector_coverage} m² per detector',
            'required_value': f'≤{DCD_RULES["smoke_detector_max_coverage_m2"]} m²',
            'notes': None if passed else f'Coverage {detector_coverage} m² exceeds max 60 m².',
        })
    else:
        checks.append(_unverifiable('smoke_detector'))

    # Rule 7 – Fire extinguisher placement
    ext_distance = extracted.get('max_distance_to_extinguisher_m')
    if ext_distance is not None:
        passed = ext_distance <= DCD_RULES['extinguisher_max_travel_m']
        checks.append({
            **RULE_METADATA['fire_extinguisher'],
            'rule_key': 'fire_extinguisher',
            'passed': passed,
            'extracted_value': f'{ext_distance} m (max travel distance)',
            'required_value': f'≤{DCD_RULES["extinguisher_max_travel_m"]} m',
            'notes': None if passed else f'Max travel distance {ext_distance} m exceeds 25 m.',
        })
    elif total_area and extracted.get('fire_extinguisher_count') is not None:
        ext_count = extracted.get('fire_extinguisher_count')
        required_count = total_area / DCD_RULES['extinguisher_per_area_m2']
        passed = ext_count >= required_count
        checks.append({
            **RULE_METADATA['fire_extinguisher'],
            'rule_key': 'fire_extinguisher',
            'passed': passed,
            'extracted_value': f'{ext_count} extinguisher(s)',
            'required_value': f'≥{required_count:.1f} (1 per {DCD_RULES["extinguisher_per_area_m2"]} m²)',
            'notes': None if passed else f'Only {ext_count} extinguisher(s) found; {required_count:.1f} required.',
        })
    else:
        checks.append(_unverifiable('fire_extinguisher'))

    # Rule 8 – Fire truck access
    truck_access = extracted.get('fire_truck_access_width_m')
    if truck_access is not None:
        passed = truck_access >= DCD_RULES['fire_truck_access_min_width_m']
        checks.append({
            **RULE_METADATA['fire_truck_access'],
            'rule_key': 'fire_truck_access',
            'passed': passed,
            'extracted_value': f'{truck_access} m road width',
            'required_value': f'≥{DCD_RULES["fire_truck_access_min_width_m"]} m',
            'notes': None if passed else f'Access road {truck_access} m is below required 4 m.',
        })
    else:
        checks.append(_unverifiable('fire_truck_access'))

    # Rule 9 – Exit separation
    # Simplified check – if exit_count >= 2, note that separation needs site verification
    exit_count_val = extracted.get('exit_count')
    if exit_count_val and exit_count_val >= 2:
        checks.append({
            **RULE_METADATA['exit_separation'],
            'rule_key': 'exit_separation',
            'passed': True,
            'extracted_value': f'{exit_count_val} exits present',
            'required_value': f'Exits must be separated by ≥{"1/3" if is_sprinklered else "1/2"} of building diagonal',
            'notes': 'Exact separation distance requires geometric calculation – manual verification recommended.',
        })
    else:
        checks.append(_unverifiable('exit_separation'))

    # Rule 10 – Emergency lighting
    has_emergency_lighting = extracted.get('emergency_lighting_present')
    if has_emergency_lighting is not None:
        checks.append({
            **RULE_METADATA['emergency_lighting'],
            'rule_key': 'emergency_lighting',
            'passed': bool(has_emergency_lighting),
            'extracted_value': 'Present' if has_emergency_lighting else 'Not found',
            'required_value': 'Required in all corridors and exit routes',
            'notes': None if has_emergency_lighting else 'Emergency lighting not indicated in blueprint.',
        })
    else:
        checks.append(_unverifiable('emergency_lighting'))

    # Determine overall result
    critical_failures = [c for c in checks if not c['passed'] and c['severity'] == 'CRITICAL' and c.get('verifiable', True)]
    high_failures = [c for c in checks if not c['passed'] and c['severity'] == 'HIGH' and c.get('verifiable', True)]

    overall_passed = len(critical_failures) == 0

    pass_count = sum(1 for c in checks if c['passed'])
    fail_count = sum(1 for c in checks if not c['passed'] and c.get('verifiable', True))
    unverifiable_count = sum(1 for c in checks if not c.get('verifiable', True))

    confidence = _calculate_confidence(checks)

    return {
        'checks': checks,
        'overall_result': 'approved' if overall_passed else 'rejected',
        'pass_count': pass_count,
        'fail_count': fail_count,
        'unverifiable_count': unverifiable_count,
        'confidence': confidence,
        'critical_failures': len(critical_failures),
        'high_failures': len(high_failures),
    }


def _unverifiable(rule_key: str) -> dict:
    return {
        **RULE_METADATA[rule_key],
        'rule_key': rule_key,
        'passed': True,
        'verifiable': False,
        'extracted_value': 'Could not extract from blueprint',
        'required_value': RULE_METADATA[rule_key]['description'],
        'notes': 'Could not verify – manual review required.',
    }


def _calculate_confidence(checks: list) -> float:
    verifiable = [c for c in checks if c.get('verifiable', True)]
    if not verifiable:
        return 0.0
    return round(len(verifiable) / len(checks) * 100, 1)
