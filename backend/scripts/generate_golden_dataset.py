import os
import sys
import json
import uuid
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
GOLDEN_DATASET_DIR = REPO_ROOT / "golden_dataset"

CASES_METADATA = [
    {
        "case_id": "case_001",
        "name": "Standard PCR Compliant Label",
        "category": "COMPLIANT_BASELINE",
        "description": "Premium Basmati Rice package containing all mandatory Rule 6 declarations with clear visual contrast and standard formatting.",
        "commodity_type": "Packaged Food",
        "declarations": {
            "BRAND_NAME": "Metrixa Organics",
            "PRODUCT_NAME": "Premium Royal Basmati Rice 1kg",
            "GENERIC_NAME": "Basmati Rice",
            "NET_QUANTITY": "1 kg",
            "MRP": "Rs. 180.00 (incl. of all taxes)",
            "UNIT_SALE_PRICE": "Rs. 180.00 / kg",
            "DATE_OF_PACKING": "01/2026",
            "EXPIRY_DATE": "01/2028",
            "BATCH_NUMBER": "LOT-BR-2026-01",
            "MANUFACTURER_NAME": "Metrixa Food Estates Ltd, Sonipat, Haryana 131101",
            "COUNTRY_OF_ORIGIN": "India",
            "CONSUMER_CARE_EMAIL": "care@metrixafoods.in",
            "CONSUMER_CARE_PHONE": "1800-123-4567"
        },
        "expected": {
            "deterministic_fields": ["BRAND_NAME", "PRODUCT_NAME", "NET_QUANTITY", "MRP", "UNIT_SALE_PRICE", "COUNTRY_OF_ORIGIN", "CONSUMER_CARE_EMAIL"],
            "normalized_values": {
                "NET_QUANTITY": {"value": 1.0, "unit": "kg", "standard_si_value": 1000.0, "standard_si_unit": "g"},
                "MRP": {"value": 180.0, "currency": "INR", "taxes_included": True},
                "UNIT_SALE_PRICE": {"value": 180.0, "unit": "kg"}
            },
            "rule_verdict": "PASS",
            "quality_tier": "PRISTINE"
        }
    },
    {
        "case_id": "case_002",
        "name": "Missing Maximum Retail Price",
        "category": "DEFECT_MISSING_DECLARATION",
        "description": "Edible sunflower oil package with net quantity and manufacturer present, but completely omitting mandatory Maximum Retail Price.",
        "commodity_type": "Edible Oil",
        "declarations": {
            "BRAND_NAME": "SunGold Pure",
            "PRODUCT_NAME": "Refined Sunflower Oil 1 Litre",
            "GENERIC_NAME": "Sunflower Oil",
            "NET_QUANTITY": "1 L",
            "DATE_OF_PACKING": "02/2026",
            "MANUFACTURER_NAME": "SunGold Refineries Ltd, Kandla, Gujarat",
            "COUNTRY_OF_ORIGIN": "India",
            "CONSUMER_CARE_EMAIL": "support@sungold.in"
        },
        "expected": {
            "deterministic_fields": ["BRAND_NAME", "PRODUCT_NAME", "NET_QUANTITY", "COUNTRY_OF_ORIGIN"],
            "missing_mandatory_fields": ["MRP"],
            "normalized_values": {
                "NET_QUANTITY": {"value": 1.0, "unit": "l", "standard_si_value": 1000.0, "standard_si_unit": "ml"}
            },
            "rule_verdict": "FAIL",
            "failing_rules": ["PCR-2011-R06-1-DA"],
            "quality_tier": "GOOD"
        }
    },
    {
        "case_id": "case_003",
        "name": "Low Resolution Package Label",
        "category": "PERCEPTION_LOW_RESOLUTION",
        "description": "Extremely pixelated label image testing image preprocessor resolution alerts and robust parsing under noise.",
        "commodity_type": "Packaged Food",
        "declarations": {
            "BRAND_NAME": "CrispySnax",
            "PRODUCT_NAME": "Spicy Potato Chips 50g",
            "NET_QUANTITY": "50 g",
            "MRP": "Rs. 20.00",
            "MANUFACTURER_NAME": "Snax Ltd, Delhi 110020",
            "COUNTRY_OF_ORIGIN": "India"
        },
        "expected": {
            "deterministic_fields": ["BRAND_NAME", "NET_QUANTITY", "MRP"],
            "normalized_values": {
                "NET_QUANTITY": {"value": 50.0, "unit": "g"},
                "MRP": {"value": 20.0, "currency": "INR"}
            },
            "quality_alert": "LOW_RESOLUTION_ESTIMATE",
            "quality_tier": "DEGRADED"
        }
    },
    {
        "case_id": "case_004",
        "name": "Motion Blurred Capture",
        "category": "PERCEPTION_BLUR",
        "description": "Simulated camera motion blur with Laplacian variance below inspection readiness threshold.",
        "commodity_type": "Beverages",
        "declarations": {
            "BRAND_NAME": "Himalayan Spring",
            "PRODUCT_NAME": "Natural Mineral Water 500ml",
            "NET_QUANTITY": "500 ml",
            "MRP": "Rs. 30.00",
            "MANUFACTURER_NAME": "Spring Springs Ltd, Dehradun",
            "COUNTRY_OF_ORIGIN": "India"
        },
        "expected": {
            "deterministic_fields": ["BRAND_NAME", "NET_QUANTITY", "MRP"],
            "quality_alert": "HIGH_BLUR_DETECTED",
            "blur_score_tier": "FAIL",
            "quality_tier": "BLURRED"
        }
    },
    {
        "case_id": "case_005",
        "name": "Reflective Specular Glare",
        "category": "PERCEPTION_GLARE",
        "description": "Laminated metallic foil pouch exhibiting high-intensity flash glare hotspot occluding consumer care info.",
        "commodity_type": "Packaged Food",
        "declarations": {
            "BRAND_NAME": "ChocoDelight",
            "PRODUCT_NAME": "Roasted Almond Chocolate Bar 100g",
            "NET_QUANTITY": "100 g",
            "MRP": "Rs. 99.00",
            "MANUFACTURER_NAME": "Choco Works Ltd, Mumbai",
            "COUNTRY_OF_ORIGIN": "India",
            "CONSUMER_CARE_EMAIL": "help@chocodelight.in"
        },
        "expected": {
            "deterministic_fields": ["BRAND_NAME", "NET_QUANTITY", "MRP"],
            "quality_alert": "SPECULAR_GLARE_WARNING",
            "quality_tier": "GLARE_DEFECT"
        }
    },
    {
        "case_id": "case_006",
        "name": "Underexposed Low-Light Capture",
        "category": "PERCEPTION_UNDEREXPOSED",
        "description": "Warehouse twilight capture exhibiting sub-threshold luminance testing contrast stretching preprocessor.",
        "commodity_type": "Household Goods",
        "declarations": {
            "BRAND_NAME": "CleanGleam",
            "PRODUCT_NAME": "Dishwash Gel Lemon 250ml",
            "NET_QUANTITY": "250 ml",
            "MRP": "Rs. 65.00",
            "MANUFACTURER_NAME": "CleanHome Corp, Pune 411001",
            "COUNTRY_OF_ORIGIN": "India"
        },
        "expected": {
            "deterministic_fields": ["BRAND_NAME", "NET_QUANTITY", "MRP"],
            "quality_alert": "LOW_LIGHT_WARNING",
            "quality_tier": "UNDEREXPOSED"
        }
    },
    {
        "case_id": "case_007",
        "name": "Conflicting Retail Price Overprint",
        "category": "ADJUDICATION_CONFLICT",
        "description": "Two competing MRP values printed on same packaging surface triggering multi-declaration conflict flag.",
        "commodity_type": "Snacks & Savouries",
        "declarations": {
            "BRAND_NAME": "TasteBites",
            "PRODUCT_NAME": "Namkeen Mixture 400g",
            "NET_QUANTITY": "400 g",
            "MRP": "Rs. 110.00 (incl. of all taxes)",
            "COMPETING_MRP": "Rs. 135.00 (incl. of all taxes)",
            "DATE_OF_PACKING": "02/2026",
            "MANUFACTURER_NAME": "TasteBites Snacks Ltd, Indore",
            "COUNTRY_OF_ORIGIN": "India",
            "CONSUMER_CARE_EMAIL": "care@tastebites.in",
            "UNIT_SALE_PRICE": "Rs. 0.28 / g"
        },
        "expected": {
            "conflict_detected": True,
            "conflict_field": "MRP",
            "divergent_values": [110.0, 135.0],
            "rule_verdict": "REVIEW",
            "requires_adjudication": True,
            "quality_tier": "GOOD"
        }
    },
    {
        "case_id": "case_008",
        "name": "Multiple Quantities Declaration",
        "category": "NORMALIZATION_WEIGHTS",
        "description": "Canned rasgulla declaring Net Quantity, Drained Weight, and Gross Weight; testing correct statutory extraction.",
        "commodity_type": "Canned Food",
        "declarations": {
            "BRAND_NAME": "SweetHeritage",
            "PRODUCT_NAME": "Kolkata Rasgulla 1kg Can",
            "NET_QUANTITY": "1 kg",
            "DRAINED_WEIGHT": "500 g",
            "GROSS_WEIGHT": "1250 g",
            "MRP": "Rs. 240.00 (incl. of all taxes)",
            "DATE_OF_PACKING": "01/2026",
            "MANUFACTURER_NAME": "Heritage Sweets Ltd, Kolkata 700001",
            "COUNTRY_OF_ORIGIN": "India",
            "CONSUMER_CARE_EMAIL": "info@heritagesweets.in",
            "UNIT_SALE_PRICE": "Rs. 240.00 / kg"
        },
        "expected": {
            "deterministic_fields": ["BRAND_NAME", "NET_QUANTITY", "MRP"],
            "normalized_values": {
                "NET_QUANTITY": {"value": 1.0, "unit": "kg", "standard_si_value": 1000.0, "standard_si_unit": "g"}
            },
            "rule_verdict": "PASS",
            "quality_tier": "PRISTINE"
        }
    },
    {
        "case_id": "case_009",
        "name": "MRP Currency Variant & USP",
        "category": "NORMALIZATION_MRP_USP",
        "description": "Label declaring price using currency symbol variant 'M.R.P. ` 250.00 (Inclusive of all taxes)' alongside Unit Sale Price.",
        "commodity_type": "Packaged Food",
        "declarations": {
            "BRAND_NAME": "NutriFlakes",
            "PRODUCT_NAME": "Whole Wheat Corn Flakes 500g",
            "NET_QUANTITY": "500 g",
            "MRP": "M.R.P. Rs 250.00 (INCLUSIVE OF ALL TAXES)",
            "UNIT_SALE_PRICE": "Rs. 0.50 per gram",
            "DATE_OF_PACKING": "03/2026",
            "MANUFACTURER_NAME": "Nutri Grain Ltd, Ghaziabad",
            "COUNTRY_OF_ORIGIN": "India",
            "CONSUMER_CARE_EMAIL": "support@nutrigrain.in"
        },
        "expected": {
            "deterministic_fields": ["BRAND_NAME", "NET_QUANTITY", "MRP", "UNIT_SALE_PRICE"],
            "normalized_values": {
                "MRP": {"value": 250.0, "currency": "INR", "taxes_included": True},
                "UNIT_SALE_PRICE": {"value": 0.50, "unit": "g"}
            },
            "rule_verdict": "PASS",
            "quality_tier": "PRISTINE"
        }
    },
    {
        "case_id": "case_010",
        "name": "Distinct Manufacturer and Packer",
        "category": "ENTITIES_MULTI_PARTY",
        "description": "Commodity declaring both primary manufacturing entity and distinct contract packaging facility.",
        "commodity_type": "Dry Fruits",
        "declarations": {
            "BRAND_NAME": "FarmSelect",
            "PRODUCT_NAME": "Californian Almonds 250g",
            "NET_QUANTITY": "250 g",
            "MRP": "Rs. 350.00 (incl. of all taxes)",
            "DATE_OF_PACKING": "02/2026",
            "MANUFACTURER_NAME": "Valley Agro Farms, Nashik",
            "PACKER_NAME": "FastPack Logistics Ltd, Navi Mumbai",
            "COUNTRY_OF_ORIGIN": "India",
            "CONSUMER_CARE_EMAIL": "care@farmselect.in",
            "UNIT_SALE_PRICE": "Rs. 1.40 / g"
        },
        "expected": {
            "deterministic_fields": ["BRAND_NAME", "NET_QUANTITY", "MRP", "MANUFACTURER_NAME", "PACKER_NAME"],
            "rule_verdict": "PASS",
            "quality_tier": "PRISTINE"
        }
    },
    {
        "case_id": "case_011",
        "name": "Imported Commodity Missing Origin",
        "category": "DEFECT_MISSING_ORIGIN",
        "description": "Imported olive oil product listing importer credentials but omitting mandatory Country of Origin declaration.",
        "commodity_type": "Imported Food",
        "declarations": {
            "BRAND_NAME": "Mediterranean Gold",
            "PRODUCT_NAME": "Extra Virgin Olive Oil 500ml",
            "NET_QUANTITY": "500 ml",
            "MRP": "Rs. 690.00 (incl. of all taxes)",
            "DATE_OF_IMPORT": "01/2026",
            "IMPORTER_NAME": "Global Fine Foods Pvt Ltd, Ballard Estate, Mumbai 400001",
            "CONSUMER_CARE_EMAIL": "help@globalfinefoods.in",
            "UNIT_SALE_PRICE": "Rs. 1.38 / ml"
        },
        "expected": {
            "deterministic_fields": ["BRAND_NAME", "NET_QUANTITY", "MRP", "IMPORTER_NAME"],
            "missing_mandatory_fields": ["COUNTRY_OF_ORIGIN"],
            "rule_verdict": "FAIL",
            "failing_rules": ["PCR-2011-R06-1-F"],
            "quality_tier": "GOOD"
        }
    },
    {
        "case_id": "case_012",
        "name": "Comprehensive Consumer Care Cell",
        "category": "COMPLIANT_CONSUMER_CARE",
        "description": "Label displaying exhaustive tripartite consumer grievance coordinates under Rule 6(1)(g).",
        "commodity_type": "Personal Care",
        "declarations": {
            "BRAND_NAME": "Metrixa Derma",
            "PRODUCT_NAME": "Moisturizing Cream 100g",
            "NET_QUANTITY": "100 g",
            "MRP": "Rs. 220.00 (incl. of all taxes)",
            "DATE_OF_PACKING": "01/2026",
            "MANUFACTURER_NAME": "Derma Care Ltd, Baddi, HP",
            "COUNTRY_OF_ORIGIN": "India",
            "CONSUMER_CARE_EMAIL": "care@metrixaderma.in",
            "CONSUMER_CARE_PHONE": "1800-444-8899",
            "CONSUMER_CARE_ADDRESS": "Consumer Cell, Box 55, South Delhi 110017",
            "UNIT_SALE_PRICE": "Rs. 2.20 / g"
        },
        "expected": {
            "deterministic_fields": ["BRAND_NAME", "NET_QUANTITY", "MRP", "CONSUMER_CARE_EMAIL", "CONSUMER_CARE_PHONE", "CONSUMER_CARE_ADDRESS"],
            "rule_verdict": "PASS",
            "quality_tier": "PRISTINE"
        }
    },
    {
        "case_id": "case_013",
        "name": "Multi-Region Distributed Layout",
        "category": "GEOMETRY_MULTI_REGION",
        "description": "Statutory declarations distributed into 4 spatial quadrants across Principal Display Panel.",
        "commodity_type": "Packaged Food",
        "declarations": {
            "BRAND_NAME": "NatureHarvest",
            "PRODUCT_NAME": "Organic Rolled Oats 1kg",
            "NET_QUANTITY": "1 kg",
            "MRP": "Rs. 195.00 (incl. of all taxes)",
            "DATE_OF_MANUFACTURE": "03/2026",
            "MANUFACTURER_NAME": "Nature Harvest Organics, Mohali",
            "COUNTRY_OF_ORIGIN": "India",
            "CONSUMER_CARE_EMAIL": "help@natureharvest.in",
            "UNIT_SALE_PRICE": "Rs. 195.00 / kg"
        },
        "expected": {
            "multi_region_quadrants": ["TOP_LEFT", "TOP_RIGHT", "BOTTOM_LEFT", "BOTTOM_RIGHT"],
            "deterministic_fields": ["BRAND_NAME", "PRODUCT_NAME", "NET_QUANTITY", "MRP"],
            "rule_verdict": "PASS",
            "quality_tier": "GOOD"
        }
    },
    {
        "case_id": "case_014",
        "name": "OCR Character Confusion Adjudication",
        "category": "ADJUDICATION_CONFUSION",
        "description": "Simulated OCR alphanumeric character confusion ('Rs. 4S0.00' instead of 'Rs. 450.00') demonstrating human adjudication workflow.",
        "commodity_type": "Beverages",
        "declarations": {
            "BRAND_NAME": "Assam Royale",
            "PRODUCT_NAME": "CTC Black Tea 500g",
            "NET_QUANTITY": "500 g",
            "MRP": "Rs. 450.00 (incl. of all taxes)",
            "RAW_OCR_SNIPPET": "Rs. 4S0.00 (INCL OF TAXES)",
            "DATE_OF_PACKING": "02/2026",
            "MANUFACTURER_NAME": "Assam Royale Estates Ltd, Dibrugarh",
            "COUNTRY_OF_ORIGIN": "India",
            "CONSUMER_CARE_EMAIL": "support@assamroyale.in",
            "UNIT_SALE_PRICE": "Rs. 0.90 / g"
        },
        "expected": {
            "ocr_confusion_detected": True,
            "target_field": "MRP",
            "raw_candidate": "Rs. 4S0.00 (INCL OF TAXES)",
            "corrected_value": 450.0,
            "rule_verdict": "REVIEW",
            "adjudication_type": "TEXT_CORRECTION",
            "quality_tier": "DEGRADED"
        }
    },
    {
        "case_id": "case_015",
        "name": "Manual Observation Fallback",
        "category": "ADJUDICATION_MANUAL_ENTRY",
        "description": "Unscannable damaged barcode label where field inspector enters manual statutory observation with officer rationale.",
        "commodity_type": "Hardware & Tools",
        "declarations": {
            "BRAND_NAME": "IronCraft",
            "PRODUCT_NAME": "Stainless Steel Fasteners Set 200pcs",
            "NET_QUANTITY": "200 N",
            "MRP": "Rs. 480.00 (incl. of all taxes)",
            "DATE_OF_PACKING": "01/2026",
            "MANUFACTURER_NAME": "IronCraft Industrial Works, Ludhiana 141003",
            "COUNTRY_OF_ORIGIN": "India",
            "CONSUMER_CARE_EMAIL": "sales@ironcraft.in",
            "UNIT_SALE_PRICE": "Rs. 2.40 per unit",
            "MANUAL_ENTRY_REASON": "Barcode and price tag partially rubbed off in transit; officer manually verified from shelf SKU label"
        },
        "expected": {
            "observation_source": "OFFICER_INPUT",
            "deterministic_fields": ["BRAND_NAME", "PRODUCT_NAME", "NET_QUANTITY", "MRP", "COUNTRY_OF_ORIGIN"],
            "normalized_values": {
                "NET_QUANTITY": {"value": 200.0, "unit": "units"}
            },
            "rule_verdict": "PASS",
            "quality_tier": "MANUAL_FALLBACK"
        }
    }
]

def draw_synthetic_label(case_data: dict, output_path: Path):
    """Draw a deterministic synthetic packaging label corresponding to the test case."""
    width, height = 800, 600
    category = case_data["category"]
    decls = case_data["declarations"]

    # Base canvas background
    if category == "PERCEPTION_UNDEREXPOSED":
        bg_color = (25, 28, 35)
        text_color = (130, 135, 145)
        accent_color = (70, 90, 110)
    else:
        bg_color = (245, 248, 252)
        text_color = (15, 23, 42)
        accent_color = (6, 95, 160)

    img = Image.new("RGB", (width, height), color=bg_color)
    draw = ImageDraw.Draw(img)

    # Outer packaging border
    border_color = (180, 200, 220) if category != "PERCEPTION_UNDEREXPOSED" else (40, 50, 65)
    draw.rectangle([20, 20, width - 20, height - 20], outline=border_color, width=4)

    # Header / Brand banner
    header_fill = (225, 235, 248) if category != "PERCEPTION_UNDEREXPOSED" else (35, 42, 55)
    draw.rectangle([25, 25, width - 25, 110], fill=header_fill)
    
    brand_text = f"★ {decls.get('BRAND_NAME', 'METRIXA BRAND')} ★"
    prod_text = decls.get('PRODUCT_NAME', 'Packaged Commodity SKU')
    draw.text((45, 40), brand_text, fill=accent_color)
    draw.text((45, 75), prod_text, fill=text_color)

    # Statutory Declarations Section
    y = 135
    for k, v in decls.items():
        if k in ("BRAND_NAME", "PRODUCT_NAME"):
            continue
        line = f"• {k.replace('_', ' ').title()}: {v}"
        draw.text((45, y), line, fill=text_color)
        y += 32

    # Case-specific visual effects
    if category == "PERCEPTION_BLUR":
        img = img.filter(ImageFilter.GaussianBlur(radius=7))

    elif category == "PERCEPTION_GLARE":
        # Draw bright white specular flare on price area
        overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        ol_draw = ImageDraw.Draw(overlay)
        ol_draw.ellipse([80, 220, 420, 360], fill=(255, 255, 255, 230))
        img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")

    elif category == "PERCEPTION_LOW_RESOLUTION":
        # Downsample and upsample
        small = img.resize((160, 120), resample=Image.Resampling.NEAREST)
        img = small.resize((width, height), resample=Image.Resampling.NEAREST)

    # Test/Non-Production Watermark banner
    watermark_draw = ImageDraw.Draw(img)
    watermark_draw.rectangle([25, height - 55, width - 25, height - 25], fill=(239, 68, 68))
    watermark_draw.text(
        (45, height - 48),
        "METRIXA GOLDEN DATASET — TEST / NON-PRODUCTION — SIH 2026 BENCHMARK",
        fill=(255, 255, 255)
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, format="PNG")

def generate_golden_dataset():
    cases_dir = GOLDEN_DATASET_DIR / "cases"
    cases_dir.mkdir(parents=True, exist_ok=True)

    manifest_entries = []

    print(f"[*] Generating Metrixa Golden Dataset in: {GOLDEN_DATASET_DIR}")

    for c in CASES_METADATA:
        cid = c["case_id"]
        c_dir = cases_dir / cid
        c_dir.mkdir(parents=True, exist_ok=True)

        # 1. Metadata JSON
        meta_obj = {
            "case_id": cid,
            "name": c["name"],
            "category": c["category"],
            "description": c["description"],
            "commodity_type": c["commodity_type"],
            "declarations": c["declarations"],
            "dataset_version": "1.0.0",
            "is_test_data": True,
            "legal_disclaimer": "TEST / NON-PRODUCTION DATASET FOR SOFTWARE BENCHMARKING ONLY."
        }
        with open(c_dir / "metadata.json", "w", encoding="utf-8") as f:
            json.dump(meta_obj, f, indent=2)

        # 2. Package Image
        img_path = c_dir / "package_front.png"
        draw_synthetic_label(c, img_path)

        # 3. Expected JSON
        expected_obj = {
            "case_id": cid,
            "expected": c["expected"],
            "is_test_data": True
        }
        with open(c_dir / "expected.json", "w", encoding="utf-8") as f:
            json.dump(expected_obj, f, indent=2)

        manifest_entries.append({
            "case_id": cid,
            "name": c["name"],
            "category": c["category"],
            "relative_dir": f"cases/{cid}",
            "image_filename": "package_front.png",
            "expected_verdict": c["expected"].get("rule_verdict", "N/A"),
            "is_test_case": True
        })
        print(f"  [+] Created {cid}: {c['name']} ({c['category']})")

    # 4. Manifest
    manifest_doc = {
        "dataset_name": "Metrixa Golden Dataset Benchmark Suite",
        "version": "1.0.0",
        "created_date": "2026-09-23",
        "total_cases": len(manifest_entries),
        "purpose": "Deterministic benchmarking of entity parsing, normalization, geometry, and legal rules.",
        "marker": "TEST / NON-PRODUCTION",
        "cases": manifest_entries
    }
    with open(GOLDEN_DATASET_DIR / "benchmark_manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest_doc, f, indent=2)

    # 5. README.md
    readme_content = """# Metrixa Golden Dataset Benchmark

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
"""
    with open(GOLDEN_DATASET_DIR / "README.md", "w", encoding="utf-8") as f:
        f.write(readme_content)

    print(f"\n[SUCCESS] Generated all {len(manifest_entries)} Golden Dataset cases successfully!\n")

if __name__ == "__main__":
    generate_golden_dataset()
