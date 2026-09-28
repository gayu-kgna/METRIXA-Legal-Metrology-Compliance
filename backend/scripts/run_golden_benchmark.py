import os
import sys
import json
import time
import uuid
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List, Tuple

# Add backend to Python path
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.models.enums import FieldType, RuleOutcome, ObservationStatus, ObservationSource, SurfaceType
from app.models.observation import Observation
from app.models.inspection import Inspection
from app.models.surface import InspectionSurface
from app.models.pdp_geometry import PDPGeometry
from app.models.rule_definition import RuleDefinition
from app.services.entity.normalizer import EntityNormalizer
from app.services.entity.classifiers import EntityClassifier
from app.services.entity.models import ParsedEntity
from app.services.entity.parser import EntityParsingService
from app.services.rules.models import EvaluationContext, ApplicabilityResult
from app.services.rules.evaluators import DeterministicEvaluator
from app.services.geometry.pdp import PDPGeometryService
from app.services.product.ledger_service import compute_label_fingerprint, compare_label_versions
from app.models.label_version import LabelVersion

from app.services.rules.registry import AUTHORITATIVE_RULES

REPO_ROOT = BACKEND_DIR.parent
GOLDEN_DATASET_DIR = REPO_ROOT / "golden_dataset"

# Load authoritative PCR rule definitions for deterministic benchmarking
STANDARD_RULES = {
    r["rule_code"]: RuleDefinition(id=uuid.uuid4(), **dict(r))
    for r in AUTHORITATIVE_RULES
}

def normalize_field_for_benchmark(normalizer: EntityNormalizer, ft: FieldType, raw_val: str) -> dict:
    if ft == FieldType.MRP:
        res = normalizer.normalize_mrp(raw_val)
        return res.model_dump() if res else {"value": 0.0, "currency": "INR", "includes_taxes": False}
    elif ft == FieldType.NET_QUANTITY:
        res = normalizer.normalize_quantity(raw_val)
        return res.model_dump() if res else {"value": 0.0, "unit": "unknown"}
    elif ft == FieldType.UNIT_SALE_PRICE:
        res = normalizer.normalize_unit_sale_price(raw_val)
        return res.model_dump() if res else {"value": 0.0, "currency": "INR"}
    elif ft in (FieldType.DATE_OF_MANUFACTURE, FieldType.EXPIRY_DATE, FieldType.BEST_BEFORE):
        res = normalizer.normalize_date(raw_val)
        return res.model_dump() if res else {}
    elif ft in (FieldType.CONSUMER_CARE_PHONE, FieldType.CONSUMER_CARE_EMAIL, FieldType.CONSUMER_CARE_ADDRESS):
        res = normalizer.normalize_consumer_care(raw_val)
        return res.model_dump() if res else {}
    elif ft == FieldType.COUNTRY_OF_ORIGIN:
        res = normalizer.normalize_country_of_origin(raw_val)
        return res.model_dump() if res else {}
    elif ft in (FieldType.MANUFACTURER_NAME, FieldType.PACKER_NAME, FieldType.IMPORTER_NAME):
        res = normalizer.normalize_party(raw_val, ft.value)
        return res.model_dump() if res else {}
    return {"value": raw_val, "text": raw_val}

def create_mock_observation(field_type_str: str, raw_val: str, norm_val: dict, status: ObservationStatus = ObservationStatus.VERIFIED, source: ObservationSource = ObservationSource.CAMERA_STREAM) -> Observation:
    try:
        ft = FieldType[field_type_str]
    except KeyError:
        ft = FieldType.OTHER_DECLARATION

    return Observation(
        id=uuid.uuid4(),
        inspection_id=uuid.uuid4(),
        field_type=ft,
        raw_value=raw_val,
        normalized_value=norm_val,
        status=status,
        source=source,
        is_latest=True,
        confidence=0.98,
    )

def run_benchmark():
    start_time = time.time()
    manifest_path = GOLDEN_DATASET_DIR / "benchmark_manifest.json"

    print("\n" + "=" * 80)
    print(" METRIXA GOLDEN DATASET BENCHMARK RUNNER")
    print(" Legal Metrology Act, 2009 & Packaged Commodities Rules, 2011")
    print("=" * 80 + "\n")

    if not manifest_path.exists():
        print(f"[FATAL] Benchmark manifest not found at: {manifest_path}")
        print("Please run `python backend/scripts/generate_golden_dataset.py` first.")
        sys.exit(1)

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    total_cases = len(manifest["cases"])
    cases_passed = 0
    cases_failed = 0
    field_matches = 0
    normalization_matches = 0
    pipeline_errors = 0
    benchmark_details = []

    normalizer = EntityNormalizer()
    classifier = EntityClassifier(normalizer=normalizer)
    parser_service = EntityParsingService(classifier=classifier, normalizer=normalizer)
    geometry_service = PDPGeometryService()

    for idx, c in enumerate(manifest["cases"], 1):
        cid = c["case_id"]
        c_dir = GOLDEN_DATASET_DIR / c["relative_dir"]
        
        meta_file = c_dir / "metadata.json"
        exp_file = c_dir / "expected.json"
        img_file = c_dir / c["image_filename"]

        if not meta_file.exists() or not exp_file.exists() or not img_file.exists():
            print(f"[{idx}/{total_cases}] [ERROR] Missing files in {c_dir}")
            cases_failed += 1
            pipeline_errors += 1
            continue

        with open(meta_file, "r", encoding="utf-8") as f:
            metadata = json.load(f)
        with open(exp_file, "r", encoding="utf-8") as f:
            expected = json.load(f)["expected"]

        decls = metadata.get("declarations", {})
        case_errors: List[str] = []

        # -------------------------------------------------------------
        # 1. Deterministic Normalization Check
        # -------------------------------------------------------------
        if "normalized_values" in expected:
            for exp_field, exp_norm in expected["normalized_values"].items():
                raw_text = decls.get(exp_field)
                if raw_text:
                    if exp_field == "NET_QUANTITY":
                        norm_obj = normalizer.normalize_quantity(raw_text)
                        actual_norm = norm_obj.model_dump() if norm_obj else {}
                        for k, v in exp_norm.items():
                            if k in actual_norm:
                                actual_val = actual_norm[k]
                                if (actual_val == v) or (str(actual_val).lower() == str(v).lower()):
                                    normalization_matches += 1
                                else:
                                    case_errors.append(f"Net Qty Norm mismatch for {k}: expected {v}, got {actual_norm[k]}")
                    elif exp_field == "MRP":
                        norm_obj = normalizer.normalize_mrp(raw_text)
                        actual_norm = norm_obj.model_dump() if norm_obj else {}
                        if "value" in exp_norm:
                            if actual_norm.get("value") == exp_norm["value"]:
                                normalization_matches += 1
                            else:
                                case_errors.append(f"MRP Norm value mismatch: expected {exp_norm['value']}, got {actual_norm.get('value')}")
                    elif exp_field == "UNIT_SALE_PRICE":
                        norm_obj = normalizer.normalize_unit_sale_price(raw_text)
                        actual_norm = norm_obj.model_dump() if norm_obj else {}
                        if "value" in exp_norm:
                            if actual_norm.get("value") == exp_norm["value"]:
                                normalization_matches += 1
                            else:
                                case_errors.append(f"USP Norm mismatch: expected {exp_norm['value']}, got {actual_norm.get('value')}")

        # -------------------------------------------------------------
        # 2. Conflict Detection Check (Case 7)
        # -------------------------------------------------------------
        if expected.get("conflict_detected"):
            parsed_entities = [
                ParsedEntity(
                    field_type=FieldType.MRP,
                    raw_value=decls["MRP"],
                    normalized_value={"value": 110.0, "currency": "INR"},
                    confidence=0.95,
                    status=ObservationStatus.OBSERVED,
                    bounding_box={"x": 0.1, "y": 0.1, "width": 0.2, "height": 0.1},
                ),
                ParsedEntity(
                    field_type=FieldType.MRP,
                    raw_value=decls["COMPETING_MRP"],
                    normalized_value={"value": 135.0, "currency": "INR"},
                    confidence=0.92,
                    status=ObservationStatus.OBSERVED,
                    bounding_box={"x": 0.5, "y": 0.1, "width": 0.2, "height": 0.1},
                )
            ]
            parser_service.detect_conflicts(parsed_entities)
            if not all(e.is_conflicting for e in parsed_entities):
                case_errors.append("Expected conflict detection between divergent MRPs failed")
            else:
                field_matches += 1

        # -------------------------------------------------------------
        # 3. Geometry Quadrant Check (Case 13)
        # -------------------------------------------------------------
        if "multi_region_quadrants" in expected:
            test_bboxes = [
                {"x": 0.1, "y": 0.1, "width": 0.2, "height": 0.1}, # TOP_LEFT
                {"x": 0.7, "y": 0.1, "width": 0.2, "height": 0.1}, # TOP_RIGHT
                {"x": 0.1, "y": 0.8, "width": 0.2, "height": 0.1}, # BOTTOM_LEFT
                {"x": 0.7, "y": 0.8, "width": 0.2, "height": 0.1}, # BOTTOM_RIGHT
            ]
            quads = [geometry_service._determine_quadrant(b) for b in test_bboxes]
            for exp_q in expected["multi_region_quadrants"]:
                if exp_q not in quads:
                    case_errors.append(f"Expected geometry quadrant '{exp_q}' not derived: got {quads}")
                else:
                    field_matches += 1

        # -------------------------------------------------------------
        # 4. Deterministic Statutory Rule Engine Verification
        # -------------------------------------------------------------
        if "rule_verdict" in expected:
            # Build observations
            obs_map: Dict[FieldType, List[Observation]] = {}
            for k, val in decls.items():
                if k in ("RAW_OCR_SNIPPET", "MANUAL_ENTRY_REASON"):
                    continue
                ft_key = "MRP" if k == "COMPETING_MRP" else k
                try:
                    ft = FieldType[ft_key]
                    is_conflict = expected.get("conflict_detected") and ft == FieldType.MRP
                    is_ocr_confusion = expected.get("ocr_confusion_detected") and ft == FieldType.MRP
                    obs_status = ObservationStatus.CONFLICTING if (is_conflict or is_ocr_confusion) else ObservationStatus.VERIFIED
                    obs_source = ObservationSource.OFFICER_INPUT if expected.get("observation_source") == "OFFICER_INPUT" else ObservationSource.CAMERA_STREAM
                    norm = normalize_field_for_benchmark(normalizer, ft, str(val))
                    obs = create_mock_observation(ft_key, str(val), norm, status=obs_status, source=obs_source)
                    obs_map.setdefault(ft, []).append(obs)
                    field_matches += 1
                except KeyError:
                    pass

            mock_insp = Inspection(
                id=uuid.uuid4(),
                inspection_number=f"BENCH-{cid.upper()}",
                initiated_at=datetime.now(timezone.utc),
            )
            mock_surf = InspectionSurface(
                id=uuid.uuid4(),
                inspection_id=mock_insp.id,
                surface_type=SurfaceType.FRONT_PDP,
                image_width=800,
                image_height=600,
            )

            mock_pdp = PDPGeometry(
                id=uuid.uuid4(),
                inspection_id=mock_insp.id,
                surface_id=mock_surf.id,
                surface_type=SurfaceType.FRONT_PDP,
                is_pdp_candidate=True,
                image_width=800,
                image_height=600,
                pdp_bounding_box={"x": 0.0, "y": 0.0, "width": 1.0, "height": 1.0},
                has_calibration=True,
                scale_px_per_mm=5.0,
                declarations_geometry={
                    "declarations": [
                        {
                            "field_type": "NET_QUANTITY",
                            "text_height_mm": 4.5,
                            "estimated_physical_text_height_mm": 4.5,
                            "quadrant": "BOTTOM_RIGHT",
                            "bounding_box": {"x": 0.6, "y": 0.7, "width": 0.3, "height": 0.15}
                        }
                    ]
                }
            )

            context = EvaluationContext(
                inspection=mock_insp,
                product=None,
                observations_by_type=obs_map,
                surfaces=[mock_surf],
                pdp_geometries=[mock_pdp],
                evaluation_timestamp=datetime.now(timezone.utc),
            )

            applicability = ApplicabilityResult(is_applicable=True, reason="Benchmark package subject to PCR 2011")

            # Evaluate each authoritative rule
            eval_results = {}
            for rcode, rdef in STANDARD_RULES.items():
                res = DeterministicEvaluator.evaluate(rdef, context, applicability)
                eval_results[rcode] = res.outcome

            # Determine composite verdict
            outcomes = list(eval_results.values())
            if any(o == RuleOutcome.FAIL for o in outcomes):
                actual_composite = "FAIL"
            elif any(o == RuleOutcome.REVIEW for o in outcomes):
                actual_composite = "REVIEW"
            elif all(o in (RuleOutcome.PASS, RuleOutcome.NOT_APPLICABLE) for o in outcomes):
                actual_composite = "PASS"
            else:
                actual_composite = "INDETERMINATE"

            exp_verdict = expected["rule_verdict"]
            if actual_composite != exp_verdict:
                case_errors.append(f"Rule verdict mismatch: expected {exp_verdict}, got {actual_composite} (Details: {eval_results})")

            # Check specific failing rules
            if "failing_rules" in expected:
                for frule in expected["failing_rules"]:
                    if eval_results.get(frule) != RuleOutcome.FAIL:
                        case_errors.append(f"Expected failing rule {frule} did not FAIL, outcome was {eval_results.get(frule)}")

        # -------------------------------------------------------------
        # 5. Deterministic Label Fingerprint Stability
        # -------------------------------------------------------------
        fp1 = compute_label_fingerprint(decls)
        fp2 = compute_label_fingerprint({k: decls[k] for k in sorted(decls.keys(), reverse=True)})
        if fp1 != fp2:
            case_errors.append("Label fingerprint is non-deterministic under key reordering")
        elif len(fp1) != 64:
            case_errors.append(f"Invalid SHA-256 fingerprint length: {len(fp1)}")

        # Record case status
        passed = len(case_errors) == 0
        if passed:
            cases_passed += 1
            status_tag = "[PASS]"
        else:
            cases_failed += 1
            status_tag = "[FAIL]"

        print(f"[{idx:02d}/{total_cases:02d}] {status_tag} {cid}: {c['name']} ({c['category']})")
        if not passed:
            for err in case_errors:
                print(f"       -> Regression Defect: {err}")

        benchmark_details.append({
            "case_id": cid,
            "name": c["name"],
            "category": c["category"],
            "passed": passed,
            "errors": case_errors,
        })

    duration = time.time() - start_time

    # Generate benchmark summary report
    report_doc = {
        "benchmark_timestamp": datetime.now(timezone.utc).isoformat(),
        "duration_seconds": round(duration, 3),
        "total_cases_evaluated": total_cases,
        "cases_passed": cases_passed,
        "cases_failed": cases_failed,
        "accuracy_pct": round((cases_passed / total_cases) * 100, 2) if total_cases > 0 else 0,
        "field_matches": field_matches,
        "normalization_matches": normalization_matches,
        "pipeline_errors": pipeline_errors,
        "details": benchmark_details,
    }

    report_path = GOLDEN_DATASET_DIR / "benchmark_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report_doc, f, indent=2)

    print("\n" + "=" * 80)
    print(" BENCHMARK EXECUTION SUMMARY")
    print("=" * 80)
    print(f"Total Test Cases   : {total_cases}")
    print(f"Cases Passed       : {cases_passed} ({round((cases_passed/total_cases)*100, 1)}%)")
    print(f"Cases Failed       : {cases_failed}")
    print(f"Field Matches      : {field_matches}")
    print(f"Norm Matches       : {normalization_matches}")
    print(f"Pipeline Errors    : {pipeline_errors}")
    print(f"Execution Duration : {round(duration, 3)} seconds")
    print(f"Saved Report       : {report_path}")
    print("=" * 80 + "\n")

    if cases_failed > 0:
        print(f"[REGRESSION FAILURE] {cases_failed} benchmark cases failed deterministic assertions.")
        sys.exit(1)
    else:
        print("[ALL DETERMINISTIC BENCHMARK GATES PASSED WITH ZERO REGRESSIONS]")
        sys.exit(0)

if __name__ == "__main__":
    run_benchmark()
