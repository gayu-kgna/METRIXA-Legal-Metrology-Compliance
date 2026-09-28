# Metrixa Golden Dataset Benchmark

> **CRITICAL NOTICE**: ALL DATA CONTAINED HEREIN IS SYNTHETIC TEST DATA (`TEST / NON-PRODUCTION`).
> None of these records represent actual manufacturers, individuals, or government enforcement proceedings.

## Overview
The **Metrixa Golden Dataset** provides an authoritative, deterministic benchmarking suite for testing perception robustness, entity extraction, statutory normalization, Principal Display Panel (PDP) geometry, and Legal Metrology rule evaluation under the **Legal Metrology (Packaged Commodities) Rules, 2011**.

## Case Categories
The benchmark suite covers 15 distinct packaging declaration and perception scenarios:
1. `case_001`: Compliant Baseline Standard Packaged Food
2. `case_002`: Defect — Missing Mandatory MRP
3. `case_003`: Perception — Extremely Low Resolution Capture
4. `case_004`: Perception — Motion Blurred Frame (Laplacian Variance < 50)
5. `case_005`: Perception — Specular Glare Reflection Hotspot
6. `case_006`: Perception — Underexposed Low-Light Ambient
7. `case_007`: Adjudication — Conflicting Overprinted Price Declarations
8. `case_008`: Normalization — Multiple Weight Declarations (Gross, Net, Drained)
9. `case_009`: Normalization — Currency Symbol Variants & Unit Sale Price
10. `case_010`: Entities — Distinct Manufacturer and Packer Entities
11. `case_011`: Defect — Imported Packaged Commodity Missing Country of Origin
12. `case_012`: Compliant — Comprehensive Tripartite Consumer Care Details
13. `case_014`: Adjudication — Alphanumeric Character Confusion ('Rs. 4S0')
14. `case_013`: Geometry — Distributed Multi-Quadrant Declarations
15. `case_015`: Fallback — Officer Manual Observation Entry

## Execution
Run the automated benchmark runner:
```bash
python backend/scripts/run_golden_benchmark.py
```
