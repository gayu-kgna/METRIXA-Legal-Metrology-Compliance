import uuid
import pytest
from app.models.ocr_region import OCRRegion
from app.models.enums import FieldType, ObservationStatus
from app.services.entity.normalizer import EntityNormalizer
from app.services.entity.classifiers import EntityClassifier
from app.services.entity.models import PARSER_VERSION, NORMALIZER_VERSION

def make_ocr_region(text: str, x=0.1, y=0.1, w=0.2, h=0.05, conf=0.95) -> OCRRegion:
    return OCRRegion(
        id=uuid.uuid4(),
        surface_id=uuid.uuid4(),
        raw_text=text,
        confidence=conf,
        bounding_box={"x": x, "y": y, "width": w, "height": h},
        token_order=0,
    )

def test_normalizer_quantity_units_and_conversions():
    norm = EntityNormalizer()

    # Grams
    q_g = norm.normalize_quantity("Net Qty: 500 g")
    assert q_g is not None
    assert q_g.value == 500.0
    assert q_g.unit == "g"
    assert q_g.base_quantity == 500.0
    assert q_g.base_unit == "g"

    # Kilograms
    q_kg = norm.normalize_quantity("1.5 kg")
    assert q_kg is not None
    assert q_kg.value == 1.5
    assert q_kg.unit == "kg"
    assert q_kg.base_quantity == 1500.0
    assert q_kg.base_unit == "g"

    # Millilitres & Litres
    q_ml = norm.normalize_quantity("750 ml")
    assert q_ml is not None
    assert q_ml.base_quantity == 750.0
    assert q_ml.base_unit == "ml"

    q_l = norm.normalize_quantity("2 L")
    assert q_l is not None
    assert q_l.base_quantity == 2000.0
    assert q_l.base_unit == "ml"

    # Count
    q_pcs = norm.normalize_quantity("10 units")
    assert q_pcs is not None
    assert q_pcs.unit == "units"
    assert q_pcs.base_quantity == 10.0

def test_normalizer_multipack_quantities():
    norm = EntityNormalizer()

    # "2 x 500 g"
    multi = norm.normalize_quantity("2 x 500 g")
    assert multi is not None
    assert multi.count == 2
    assert multi.individual_quantity == 500.0
    assert multi.total_quantity == 1000.0
    assert multi.base_quantity == 1000.0
    assert multi.base_unit == "g"

    # "6 * 100 ml"
    multi_vol = norm.normalize_quantity("6 * 100 ml")
    assert multi_vol is not None
    assert multi_vol.count == 6
    assert multi_vol.individual_quantity == 100.0
    assert multi_vol.total_quantity == 600.0

    # "Pack of 6"
    pack_of = norm.normalize_quantity("Pack of 6")
    assert pack_of is not None
    assert pack_of.count == 6
    assert pack_of.total_quantity == 6.0

def test_normalizer_mrp_extraction():
    norm = EntityNormalizer()

    mrp1 = norm.normalize_mrp("MRP Rs. 250.00 (INCL. OF ALL TAXES)")
    assert mrp1 is not None
    assert mrp1.value == 250.00
    assert mrp1.currency == "INR"
    assert mrp1.includes_taxes is True

    mrp2 = norm.normalize_mrp("M.R.P. ₹ 120/-")
    assert mrp2 is not None
    assert mrp2.value == 120.0
    assert mrp2.currency_symbol == "₹"

def test_normalizer_date_and_ambiguity_handling():
    norm = EntityNormalizer()

    # Unambiguous DD/MM/YYYY (day > 12)
    d_unambig = norm.normalize_date("25/08/2026", date_type="MFG")
    assert d_unambig is not None
    assert d_unambig.day == 25
    assert d_unambig.month == 8
    assert d_unambig.year == 2026
    assert d_unambig.date_iso == "2026-08-25"
    assert d_unambig.is_ambiguous is False

    # Ambiguous DD/MM vs MM/DD (both <= 12)
    d_ambig = norm.normalize_date("03/04/2026", date_type="MFG")
    assert d_ambig is not None
    assert d_ambig.is_ambiguous is True
    assert "Ambiguous" in d_ambig.ambiguity_reason

    # Month and Year: 01/2026
    d_my = norm.normalize_date("01/2026", date_type="PKD")
    assert d_my is not None
    assert d_my.precision == "MONTH_YEAR"
    assert d_my.month == 1
    assert d_my.year == 2026
    assert d_my.date_iso == "2026-01"
    assert d_my.is_ambiguous is False

def test_normalizer_consumer_care():
    norm = EntityNormalizer()
    text = "Consumer Care: 1800-111-222, Email: care@metrixa.example.com"
    care = norm.normalize_consumer_care(text)
    assert len(care.phones) >= 1
    assert "1800-111-222" in care.phones[0]
    assert len(care.emails) >= 1
    assert "care@metrixa.example.com" in care.emails[0]

def test_normalizer_parties():
    norm = EntityNormalizer()
    mfg = norm.normalize_party("Mfd By: Metrixa Foods Pvt Ltd, Plot 42, Industrial Area, New Delhi 110001", "MANUFACTURER")
    assert mfg.entity_type == "MANUFACTURER"
    assert "Metrixa Foods Pvt Ltd" in mfg.name
    assert "New Delhi" in mfg.address

    packer = norm.normalize_party("Packed by: Standard Packaging Co, Okhla Phase 3", "PACKER")
    assert packer.entity_type == "PACKER"
    assert "Standard Packaging Co" in packer.name

def test_normalizer_country_of_origin_and_usp():
    norm = EntityNormalizer()

    origin = norm.normalize_country_of_origin("Country of Origin: India")
    assert origin is not None
    assert origin.country == "India"

    usp = norm.normalize_unit_sale_price("USP: ₹ 240.00 / kg")
    assert usp is not None
    assert usp.value == 240.00
    assert "kg" in usp.unit

def test_classifier_comprehensive_packaging_extraction():
    classifier = EntityClassifier()

    r1 = make_ocr_region("METRIXA PREMIUM GREEN TEA", x=0.05, y=0.05, w=0.5, h=0.05)
    r2 = make_ocr_region("Mfd By: Metrixa Foods Pvt Ltd, Plot 42, New Delhi 110001", x=0.05, y=0.15, w=0.7, h=0.05)
    r3 = make_ocr_region("Net Qty: 500 g", x=0.05, y=0.25, w=0.3, h=0.05)
    r4 = make_ocr_region("MRP Rs. 250.00 (INCL. OF ALL TAXES)", x=0.05, y=0.35, w=0.5, h=0.05)
    r5 = make_ocr_region("MFG DATE: 01/2026", x=0.05, y=0.45, w=0.3, h=0.05)
    r6 = make_ocr_region("Care: 1800-111-222, care@metrixa.example.com", x=0.05, y=0.55, w=0.6, h=0.05)
    r7 = make_ocr_region("Country of Origin: India", x=0.05, y=0.65, w=0.4, h=0.05)
    r8 = make_ocr_region("USP: ₹ 0.50 / g", x=0.05, y=0.75, w=0.3, h=0.05)
    r9 = make_ocr_region("Batch No: BATCH-2026-X1", x=0.05, y=0.85, w=0.3, h=0.05)

    all_regions = [r1, r2, r3, r4, r5, r6, r7, r8, r9]
    full_text = " ".join(r.raw_text for r in all_regions)

    entities = classifier.classify_and_parse(all_regions, full_text)
    field_types = {e.field_type for e in entities}

    assert FieldType.PRODUCT_NAME in field_types
    assert FieldType.MANUFACTURER_NAME in field_types
    assert FieldType.NET_QUANTITY in field_types
    assert FieldType.MRP in field_types
    assert FieldType.DATE_OF_MANUFACTURE in field_types
    assert FieldType.CONSUMER_CARE_PHONE in field_types
    assert FieldType.CONSUMER_CARE_EMAIL in field_types
    assert FieldType.COUNTRY_OF_ORIGIN in field_types
    assert FieldType.UNIT_SALE_PRICE in field_types
    assert FieldType.BATCH_NUMBER in field_types

    # Verify bounding boxes are valid normalized [0, 1]
    for ent in entities:
        assert 0.0 <= ent.bounding_box["x"] <= 1.0
        assert 0.0 <= ent.bounding_box["y"] <= 1.0
        assert 0.0 <= ent.bounding_box["width"] <= 1.0
        assert 0.0 <= ent.bounding_box["height"] <= 1.0
        assert ent.parser_version == PARSER_VERSION
        assert ent.normalizer_version == NORMALIZER_VERSION
