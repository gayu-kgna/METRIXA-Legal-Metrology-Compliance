# Metrixa Golden Dataset Benchmark Specification

> **Status**: Verified & Deterministic  
> **Classification**: `TEST / NON-PRODUCTION DATASET FOR BENCHMARKING ONLY`  
> **Statutory Basis**: *Legal Metrology (Packaged Commodities) Rules, 2011*

---

## 1. Overview & Purpose

The **Metrixa Golden Dataset** is a curated suite of **15 synthetic packaging test cases** created to provide a reproducible, deterministic benchmark for legal metrology inspection systems.

The dataset verifies:
1. **Perception Robustness**: Processing low-resolution, blurred, glared, and underexposed captures without crash or hallucination.
2. **Deterministic Metric Normalization**: Converting raw text (e.g. `200 N`, `1 L`, `1 kg`, `Rs 250.00`) into standard SI metric representations under Rule 12 of PCMR 2011.
3. **Statutory Legal Compliance**: Evaluating mandatory declarations (MRP, Net Qty, Date, Manufacturer, Country of Origin, Consumer Care, USP) against authoritative statutory rules.
4. **Adjudication Edge Cases**: Handling character confusion (e.g. `Rs. 4S0` vs `Rs. 450`), dual pricing overprint conflicts, and officer manual observation fallbacks.
5. **Cryptographic Invariance**: Ensuring deterministic label fingerprinting under key re-ordering.

---

## 2. Benchmark Cases Matrix

| Case ID | Case Name | Category | Expected Verdict | Primary Statutory Provision |
| :--- | :--- | :--- | :--- | :--- |
| `case_001` | Standard PCR Compliant Label | `COMPLIANT_BASELINE` | **PASS** | Complete PCMR 2011 Rule 6 & 7 baseline |
| `case_002` | Missing Maximum Retail Price | `DEFECT_MISSING_DECLARATION` | **FAIL** | Rule 6(1)(da) - Mandatory Retail Price |
| `case_003` | Low Resolution Package Label | `PERCEPTION_LOW_RESOLUTION` | **N/A** (Alert) | Image quality preprocessor resolution alert |
| `case_004` | Motion Blurred Capture | `PERCEPTION_BLUR` | **N/A** (Alert) | Laplacian variance blur estimation alert |
| `case_005` | Reflective Specular Glare | `PERCEPTION_GLARE` | **N/A** (Alert) | Specular glare hotspot detection alert |
| `case_006` | Underexposed Low-Light Capture | `PERCEPTION_UNDEREXPOSED` | **N/A** (Alert) | Histogram luminance underexposure alert |
| `case_007` | Conflicting Retail Price Overprint | `ADJUDICATION_CONFLICT` | **REVIEW** | Rule 6(1)(da) - Dual pricing prohibited |
| `case_008` | Multiple Quantities Declaration | `NORMALIZATION_WEIGHTS` | **PASS** | Rule 12 & Rule 24 - Drained & gross weight |
| `case_009` | MRP Currency Variant & USP | `NORMALIZATION_MRP_USP` | **PASS** | Rule 6(1)(da) & Rule 6(1)(g) - Unit Sale Price |
| `case_010` | Distinct Manufacturer & Packer | `ENTITIES_MULTI_PARTY` | **PASS** | Rule 6(1)(a) - Joint maker & packer credentials |
| `case_011` | Imported Commodity Missing Origin | `DEFECT_MISSING_ORIGIN` | **FAIL** | Rule 6(1)(f) - Mandatory Country of Origin |
| `case_012` | Comprehensive Consumer Care Cell | `COMPLIANT_CONSUMER_CARE` | **PASS** | Rule 6(1)(e) - Tripartite contact coordinates |
| `case_013` | Multi-Region Distributed Layout | `GEOMETRY_MULTI_REGION` | **PASS** | Rule 7 - Spatial quadrant distribution |
| `case_014` | OCR Character Confusion Adjudication | `ADJUDICATION_CONFUSION` | **REVIEW** | Rule 6(1)(da) - Alphanumeric OCR noise (`4S0`) |
| `case_015` | Manual Observation Fallback | `ADJUDICATION_MANUAL_ENTRY` | **PASS** | Officer fallback for damaged barcode labels |

---

## 3. Directory Layout

The dataset is located in the repository root at `golden_dataset/`:
```
golden_dataset/
├── README.md                     # Synthetic data disclaimer and guidelines
├── benchmark_manifest.json       # Machine-readable case inventory
├── benchmark_report.json         # Automated execution output and metrics
└── cases/
    ├── case_001/
    │   ├── metadata.json         # Case description, commodity type, declarations
    │   ├── package_front.png     # Synthetic packaging image with visual traits
    │   └── expected.json         # Deterministic statutory ground truth
    ├── case_002/
    │   ...
    └── case_015/
```

---

## 4. Running the Benchmark

The benchmark runner executes completely offline and requires no network connection:

```bash
# From backend directory:
..\.venv\Scripts\python scripts/run_golden_benchmark.py
```

### Execution Output & Verification
```
================================================================================
 METRIXA GOLDEN DATASET BENCHMARK RUNNER
 Legal Metrology Act, 2009 & Packaged Commodities Rules, 2011
================================================================================

[01/15] [PASS] case_001: Standard PCR Compliant Label (COMPLIANT_BASELINE)
[02/15] [PASS] case_002: Missing Maximum Retail Price (DEFECT_MISSING_DECLARATION)
[03/15] [PASS] case_003: Low Resolution Package Label (PERCEPTION_LOW_RESOLUTION)
[04/15] [PASS] case_004: Motion Blurred Capture (PERCEPTION_BLUR)
[05/15] [PASS] case_005: Reflective Specular Glare (PERCEPTION_GLARE)
[06/15] [PASS] case_006: Underexposed Low-Light Capture (PERCEPTION_UNDEREXPOSED)
[07/15] [PASS] case_007: Conflicting Retail Price Overprint (ADJUDICATION_CONFLICT)
[08/15] [PASS] case_008: Multiple Quantities Declaration (NORMALIZATION_WEIGHTS)
[09/15] [PASS] case_009: MRP Currency Variant & USP (NORMALIZATION_MRP_USP)
[10/15] [PASS] case_010: Distinct Manufacturer and Packer (ENTITIES_MULTI_PARTY)
[11/15] [PASS] case_011: Imported Commodity Missing Origin (DEFECT_MISSING_ORIGIN)
[12/15] [PASS] case_012: Comprehensive Consumer Care Cell (COMPLIANT_CONSUMER_CARE)
[13/15] [PASS] case_013: Multi-Region Distributed Layout (GEOMETRY_MULTI_REGION)
[14/15] [PASS] case_014: OCR Character Confusion Adjudication (ADJUDICATION_CONFUSION)
[15/15] [PASS] case_015: Manual Observation Fallback (ADJUDICATION_MANUAL_ENTRY)

================================================================================
 BENCHMARK EXECUTION SUMMARY
================================================================================
Total Test Cases   : 15
Cases Passed       : 15 (100.0%)
Cases Failed       : 0
Field Matches      : 110
Norm Matches       : 15
Pipeline Errors    : 0
Execution Duration : 0.014 seconds
Saved Report       : golden_dataset/benchmark_report.json
================================================================================

[ALL DETERMINISTIC BENCHMARK GATES PASSED WITH ZERO REGRESSIONS]
```

---

## 5. Regenerating the Dataset

To regenerate the synthetic images, metadata, and expected results:
```bash
cd backend
..\.venv\Scripts\python scripts/generate_golden_dataset.py
```
This regenerates all 15 cases in `golden_dataset/` with zero manual intervention.
