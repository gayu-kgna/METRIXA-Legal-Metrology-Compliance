import re
import uuid
from typing import List, Dict, Any, Optional, Tuple
from app.models.ocr_region import OCRRegion
from app.models.enums import FieldType, ObservationStatus
from app.services.entity.models import ParsedEntity
from app.services.entity.normalizer import EntityNormalizer

class EntityClassifier:
    """
    Deterministic rule-based and regex classifier for Legal Metrology packaging declarations.
    Groups co-linear or sequential OCR tokens, identifies statutory entities,
    and invokes EntityNormalizer to create standard ParsedEntity objects.
    """

    def __init__(self, normalizer: Optional[EntityNormalizer] = None):
        self.normalizer = normalizer or EntityNormalizer()

    def _compute_bounding_box(self, regions: List[OCRRegion]) -> Dict[str, float]:
        """Compute the minimal enclosing normalized bounding box across all constituent regions."""
        if not regions:
            return {"x": 0.0, "y": 0.0, "width": 0.0, "height": 0.0}

        min_x = min(r.bounding_box.get("x", 0.0) for r in regions)
        min_y = min(r.bounding_box.get("y", 0.0) for r in regions)
        max_x = max(r.bounding_box.get("x", 0.0) + r.bounding_box.get("width", 0.0) for r in regions)
        max_y = max(r.bounding_box.get("y", 0.0) + r.bounding_box.get("height", 0.0) for r in regions)

        return {
            "x": round(max(0.0, min(1.0, min_x)), 6),
            "y": round(max(0.0, min(1.0, min_y)), 6),
            "width": round(max(0.0, min(1.0 - min_x, max_x - min_x)), 6),
            "height": round(max(0.0, min(1.0 - min_y, max_y - min_y)), 6),
        }

    def _compute_confidence(self, regions: List[OCRRegion]) -> float:
        """Compute average confidence of constituent OCR regions."""
        if not regions:
            return 1.0
        return round(sum(r.confidence for r in regions) / len(regions), 4)

    def classify_and_parse(self, regions: List[OCRRegion], full_text: str = "") -> List[ParsedEntity]:
        """
        Main classification entrypoint.
        Inspects OCR regions and raw text lines to deterministically extract all statutory entities.
        """
        entities: List[ParsedEntity] = []
        parsed_region_ids = set()

        # Build lines of text from regions based on token order / vertical alignment
        text_content = full_text or " ".join(r.raw_text for r in regions)

        # 1. NET QUANTITY
        net_qty_entity = self._parse_net_quantity(regions, text_content)
        if net_qty_entity:
            entities.append(net_qty_entity)

        # 2. MAXIMUM RETAIL PRICE (MRP)
        mrp_entity = self._parse_mrp(regions, text_content)
        if mrp_entity:
            entities.append(mrp_entity)

        # 3. DATES (MFG, PACKED, EXPIRY, BEST BEFORE)
        date_entities = self._parse_dates(regions, text_content)
        entities.extend(date_entities)

        # 4. MANUFACTURER
        mfg_entity = self._parse_manufacturer(regions, text_content)
        if mfg_entity:
            entities.append(mfg_entity)

        # 5. PACKER
        packer_entity = self._parse_packer(regions, text_content)
        if packer_entity:
            entities.append(packer_entity)

        # 6. IMPORTER
        importer_entity = self._parse_importer(regions, text_content)
        if importer_entity:
            entities.append(importer_entity)

        # 7. CONSUMER CARE (PHONE & EMAIL)
        care_entities = self._parse_consumer_care(regions, text_content)
        entities.extend(care_entities)

        # 8. COUNTRY OF ORIGIN
        country_entity = self._parse_country_of_origin(regions, text_content)
        if country_entity:
            entities.append(country_entity)

        # 9. UNIT SALE PRICE
        usp_entity = self._parse_unit_sale_price(regions, text_content)
        if usp_entity:
            entities.append(usp_entity)

        # 10. BRAND NAME
        brand_entity = self._parse_brand_name(regions, text_content)
        if brand_entity:
            entities.append(brand_entity)

        # 11. GENERIC / COMMON COMMODITY NAME
        generic_entity = self._parse_generic_name(regions, text_content)
        if generic_entity:
            entities.append(generic_entity)

        # 12. PRODUCT NAME
        prod_entity = self._parse_product_name(regions, text_content)
        if prod_entity:
            entities.append(prod_entity)

        # 13. BATCH / LOT / LICENSE NUMBER
        batch_entity = self._parse_batch_number(regions, text_content)
        if batch_entity:
            entities.append(batch_entity)

        return entities

    # --- FIELD PARSERS ---

    def _find_matching_regions(self, regions: List[OCRRegion], pattern: str) -> List[OCRRegion]:
        """Find regions matching or containing regex pattern."""
        regex = re.compile(pattern, re.IGNORECASE)
        matching = []
        for r in regions:
            if regex.search(r.raw_text):
                matching.append(r)
        return matching

    def _parse_net_quantity(self, regions: List[OCRRegion], full_text: str) -> Optional[ParsedEntity]:
        # 1. Multi-pack phrase: "contains 10 packs of 71g", "10 packs of 71g inside"
        multipack_match = re.search(
            r"(\d+\s*(?:packs?|units?|pieces?|pkts?)\s+of\s+[\d\.]+\s*(?:mg|g|gm|gms|gram|grams|kg|kgs|ml|cl|l|ltr|litre|pcs|units))",
            full_text,
            re.IGNORECASE,
        )
        if multipack_match:
            raw_snippet = multipack_match.group(1).strip()
            norm_data = self.normalizer.normalize_quantity(raw_snippet)
            if norm_data:
                matching_regions = self._find_matching_regions(regions, r"(?:pack|contains|packs\s+of|\d+\s*g)")
                return ParsedEntity(
                    field_type=FieldType.NET_QUANTITY,
                    raw_value=raw_snippet,
                    normalized_value=norm_data.model_dump(),
                    status=ObservationStatus.OBSERVED,
                    confidence=self._compute_confidence(matching_regions),
                    bounding_box=self._compute_bounding_box(matching_regions),
                    source_region_ids=[r.id for r in matching_regions],
                )

        # 2. Explicit net quantity declaration: Net Qty / Net Quantity / Net Wt / Net Weight
        explicit_match = re.search(
            r"(?:net\s*(?:quantity|qty|wt|weight)\s*[:\-]?\s*)((?:pack\s+of\s+)?(?:\d+\s*(?:x|×|\*)\s*)?[\d\.]+\s*(?:mg|g|gm|gms|gram|grams|kg|kgs|kilogram|kilograms|ml|cl|l|ltr|litre|litres|pcs|pieces|units))\b",
            full_text,
            re.IGNORECASE,
        )
        if explicit_match:
            raw_snippet = explicit_match.group(0).strip()
            norm_data = self.normalizer.normalize_quantity(raw_snippet)
            if norm_data:
                matching_regions = self._find_matching_regions(regions, r"(?:net|qty|weight|wt|\d+\s*(?:g|kg|ml|l|pcs))")
                return ParsedEntity(
                    field_type=FieldType.NET_QUANTITY,
                    raw_value=raw_snippet,
                    normalized_value=norm_data.model_dump(),
                    status=ObservationStatus.OBSERVED,
                    confidence=self._compute_confidence(matching_regions),
                    bounding_box=self._compute_bounding_box(matching_regions),
                    source_region_ids=[r.id for r in matching_regions],
                )

        # 3. Fallback: quantity patterns not part of nutrition table
        for candidate in re.finditer(
            r"((?:pack\s+of\s+)?(?:\d+\s*(?:x|×|\*)\s*)?[\d\.]+\s*(?:mg|g|gm|gms|gram|grams|kg|kgs|kilogram|kilograms|ml|cl|l|ltr|litre|litres|pcs|pieces|units))\b",
            full_text,
            re.IGNORECASE,
        ):
            start_pos = candidate.start()
            prefix = full_text[max(0, start_pos - 35):start_pos].lower()
            if any(term in prefix for term in ["serving", "per 100", "approx", "fat", "protein", "carbohydrate", "sugar", "sodium"]):
                continue
            raw_snippet = candidate.group(0).strip()
            norm_data = self.normalizer.normalize_quantity(raw_snippet)
            if norm_data:
                matching_regions = self._find_matching_regions(regions, r"(?:net|qty|weight|wt|\d+\s*(?:g|kg|ml|l|pcs))")
                return ParsedEntity(
                    field_type=FieldType.NET_QUANTITY,
                    raw_value=raw_snippet,
                    normalized_value=norm_data.model_dump(),
                    status=ObservationStatus.OBSERVED,
                    confidence=self._compute_confidence(matching_regions),
                    bounding_box=self._compute_bounding_box(matching_regions),
                    source_region_ids=[r.id for r in matching_regions],
                )

        return None

    def _parse_mrp(self, regions: List[OCRRegion], full_text: str) -> Optional[ParsedEntity]:
        pattern = r"(?:m\.?r\.?p\.?|maximum\s+retail\s+price)\s*[:\-]?\s*(?:rs\.?|₹|inr)?\s*(\d+(?:\.\d{1,2})?)\s*(?:/-)?(?:\s*\([^\)]+\))?"
        match = re.search(pattern, full_text, re.IGNORECASE)
        if not match:
            # Fallback for standalone currency
            match = re.search(r"(?:rs\.?|₹)\s*(\d+(?:\.\d{1,2})?)\s*(?:/-)?", full_text, re.IGNORECASE)
            if not match:
                return None

        raw_snippet = match.group(0).strip()
        norm_data = self.normalizer.normalize_mrp(raw_snippet)
        if not norm_data:
            return None

        matching_regions = self._find_matching_regions(regions, r"(?:mrp|maximum|rs|₹|\d+\.\d{2})")

        return ParsedEntity(
            field_type=FieldType.MRP,
            raw_value=raw_snippet,
            normalized_value=norm_data.model_dump(),
            status=ObservationStatus.OBSERVED,
            confidence=self._compute_confidence(matching_regions),
            bounding_box=self._compute_bounding_box(matching_regions),
            source_region_ids=[r.id for r in matching_regions],
        )

    def _parse_dates(self, regions: List[OCRRegion], full_text: str) -> List[ParsedEntity]:
        results: List[ParsedEntity] = []

        date_configs = [
            (r"(?:mfd\.?|mfg\.?|manufactured|mfg\s*date)\s*[:\-]?\s*(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{4}|\d{1,2}[\/\-\.]\d{4}|\d{4}[\/\-]\d{1,2}[\/\-]\d{1,2})", FieldType.DATE_OF_MANUFACTURE, "MFG"),
            (r"(?:pkd\.?|packed|packing\s*date)\s*[:\-]?\s*(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{4}|\d{1,2}[\/\-\.]\d{4}|\d{4}[\/\-]\d{1,2}[\/\-]\d{1,2})", FieldType.DATE_OF_PACKING, "PKD"),
            (r"(?:exp\.?|expiry|best\s*before|use\s*by)\s*[:\-]?\s*(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{4}|\d{1,2}[\/\-\.]\d{4}|\d{4}[\/\-]\d{1,2}[\/\-]\d{1,2})", FieldType.EXPIRY_DATE, "EXPIRY"),
        ]

        for pattern, ftype, dtype in date_configs:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                raw_snippet = match.group(0).strip()
                date_str = match.group(1).strip()
                norm_data = self.normalizer.normalize_date(date_str, date_type=dtype)
                if norm_data:
                    matching_regions = self._find_matching_regions(regions, r"(?:mfg|mfd|pkd|exp|date|\d{2}[\/\-]\d{2,4})")
                    status = ObservationStatus.INDETERMINATE if norm_data.is_ambiguous else ObservationStatus.OBSERVED
                    results.append(
                        ParsedEntity(
                            field_type=ftype,
                            raw_value=raw_snippet,
                            normalized_value=norm_data.model_dump(),
                            status=status,
                            confidence=self._compute_confidence(matching_regions),
                            bounding_box=self._compute_bounding_box(matching_regions),
                            source_region_ids=[r.id for r in matching_regions],
                            is_ambiguous=norm_data.is_ambiguous,
                            ambiguity_reason=norm_data.ambiguity_reason,
                        )
                    )

        return results

    def _parse_manufacturer(self, regions: List[OCRRegion], full_text: str) -> Optional[ParsedEntity]:
        pattern = r"(?:mfd\.?\s*by|manufactured\s*by|manufactured\s*(?:&|and)\s*marketed\s*by|marketed\s*by|mkt\.?\s*by|mfg\.?\s*by)\s*[:\-]?\s*([^,\n\r]+(?:,\s*[^,\n\r]+){0,3})"
        match = re.search(pattern, full_text, re.IGNORECASE)
        if not match:
            # Fallback for recognized statutory manufacturer names without explicit prefix
            fallback_pattern = r"\b(NESTLE\s+INDIA\s+(?:LIMITED|LTD\.?)|BRITANNIA\s+INDUSTRIES\s+(?:LIMITED|LTD\.?)|ENERLIFE\s*(?:\(INDIA\))?\s*PRIVATE\s+LIMITED|KALDU\s+SARI\s+NABATI)\b(?:,\s*[^,\n\r]+){0,3}"
            match = re.search(fallback_pattern, full_text, re.IGNORECASE)
            if not match:
                return None

        raw_snippet = match.group(0).strip()
        role = "MARKETED_BY" if re.search(r"^(?:marketed|mkt\.?)\s*by", raw_snippet, re.IGNORECASE) else "MANUFACTURER"
        norm_data = self.normalizer.normalize_party(raw_snippet, entity_type=role)
        matching_regions = self._find_matching_regions(regions, r"(?:mfd|manufactured|marketed|mkt|foods|pvt|ltd|industries|britannia|nestle|enerlife|nabati)")

        return ParsedEntity(
            field_type=FieldType.MANUFACTURER_NAME,
            raw_value=raw_snippet,
            normalized_value=norm_data.model_dump(),
            status=ObservationStatus.OBSERVED,
            confidence=self._compute_confidence(matching_regions),
            bounding_box=self._compute_bounding_box(matching_regions),
            source_region_ids=[r.id for r in matching_regions],
        )

    def _parse_packer(self, regions: List[OCRRegion], full_text: str) -> Optional[ParsedEntity]:
        pattern = r"(?:pkd\.?\s*by|packed\s*by)\s*[:\-]?\s*([^,\n\r]+(?:,\s*[^,\n\r]+){0,3})"
        match = re.search(pattern, full_text, re.IGNORECASE)
        if not match:
            return None

        raw_snippet = match.group(0).strip()
        norm_data = self.normalizer.normalize_party(raw_snippet, entity_type="PACKER")
        matching_regions = self._find_matching_regions(regions, r"(?:pkd|packed|packer)")

        return ParsedEntity(
            field_type=FieldType.PACKER_NAME,
            raw_value=raw_snippet,
            normalized_value=norm_data.model_dump(),
            status=ObservationStatus.OBSERVED,
            confidence=self._compute_confidence(matching_regions),
            bounding_box=self._compute_bounding_box(matching_regions),
            source_region_ids=[r.id for r in matching_regions],
        )

    def _parse_importer(self, regions: List[OCRRegion], full_text: str) -> Optional[ParsedEntity]:
        pattern = r"(?:imported\s*by|importer)\s*[:\-]?\s*([^,\n\r]+(?:,\s*[^,\n\r]+){0,3})"
        match = re.search(pattern, full_text, re.IGNORECASE)
        if not match:
            return None

        raw_snippet = match.group(0).strip()
        norm_data = self.normalizer.normalize_party(raw_snippet, entity_type="IMPORTER")
        matching_regions = self._find_matching_regions(regions, r"(?:imported|importer)")

        return ParsedEntity(
            field_type=FieldType.IMPORTER_NAME,
            raw_value=raw_snippet,
            normalized_value=norm_data.model_dump(),
            status=ObservationStatus.OBSERVED,
            confidence=self._compute_confidence(matching_regions),
            bounding_box=self._compute_bounding_box(matching_regions),
            source_region_ids=[r.id for r in matching_regions],
        )

    def _parse_consumer_care(self, regions: List[OCRRegion], full_text: str) -> List[ParsedEntity]:
        entities: List[ParsedEntity] = []
        care_norm = self.normalizer.normalize_consumer_care(full_text)

        # Phone
        if care_norm.phones:
            matching_regions = self._find_matching_regions(regions, r"(?:care|customer|1800|\d{4,})")
            entities.append(
                ParsedEntity(
                    field_type=FieldType.CONSUMER_CARE_PHONE,
                    raw_value=", ".join(care_norm.phones),
                    normalized_value={"phones": care_norm.phones, "primary_phone": care_norm.phones[0]},
                    status=ObservationStatus.OBSERVED,
                    confidence=self._compute_confidence(matching_regions),
                    bounding_box=self._compute_bounding_box(matching_regions),
                    source_region_ids=[r.id for r in matching_regions],
                )
            )

        # Email
        if care_norm.emails:
            matching_regions = self._find_matching_regions(regions, r"(?:@|care|email)")
            entities.append(
                ParsedEntity(
                    field_type=FieldType.CONSUMER_CARE_EMAIL,
                    raw_value=", ".join(care_norm.emails),
                    normalized_value={"emails": care_norm.emails, "primary_email": care_norm.emails[0]},
                    status=ObservationStatus.OBSERVED,
                    confidence=self._compute_confidence(matching_regions),
                    bounding_box=self._compute_bounding_box(matching_regions),
                    source_region_ids=[r.id for r in matching_regions],
                )
            )

        return entities

    def _parse_country_of_origin(self, regions: List[OCRRegion], full_text: str) -> Optional[ParsedEntity]:
        norm_data = self.normalizer.normalize_country_of_origin(full_text)
        if not norm_data:
            return None

        matching_regions = self._find_matching_regions(regions, r"(?:origin|country|india|made)")
        return ParsedEntity(
            field_type=FieldType.COUNTRY_OF_ORIGIN,
            raw_value=norm_data.raw_statement,
            normalized_value=norm_data.model_dump(),
            status=ObservationStatus.OBSERVED,
            confidence=self._compute_confidence(matching_regions),
            bounding_box=self._compute_bounding_box(matching_regions),
            source_region_ids=[r.id for r in matching_regions],
        )

    def _parse_unit_sale_price(self, regions: List[OCRRegion], full_text: str) -> Optional[ParsedEntity]:
        # Require either explicit USP keyword or currency prefix with statutory metric unit
        pattern = r"(?:(?:usp|unit\s*sale\s*price)\s*[:\-]?\s*(?:₹|Rs\.?|INR)?|(?:₹|Rs\.?|INR)\s*)\s*(\d+(?:\.\d{1,2})?)\s*(?:per|/)\s*((?:\d+\s*)?(?:g|gm|gms|gram|grams|kg|kgs|kilogram|kilograms|ml|cl|l|lt|ltr|litre|litres|pcs?|pieces?|units?|n|u))\b"
        match = re.search(pattern, full_text, re.IGNORECASE)
        if not match:
            return None

        raw_snippet = match.group(0).strip()
        norm_data = self.normalizer.normalize_unit_sale_price(raw_snippet)
        if not norm_data:
            return None

        matching_regions = self._find_matching_regions(regions, r"(?:usp|unit\s*sale|per|/)")
        return ParsedEntity(
            field_type=FieldType.UNIT_SALE_PRICE,
            raw_value=raw_snippet,
            normalized_value=norm_data.model_dump(),
            status=ObservationStatus.OBSERVED,
            confidence=self._compute_confidence(matching_regions),
            bounding_box=self._compute_bounding_box(matching_regions),
            source_region_ids=[r.id for r in matching_regions],
        )

    def _parse_brand_name(self, regions: List[OCRRegion], full_text: str) -> Optional[ParsedEntity]:
        # Match explicit brand declaration or recognized packaging brand
        pattern = r"(?:brand|brand\s*name)\s*[:\-]\s*([^\n\r]+)|\b(BRITANNIA|METRIXA|PARLE|HALDIRAM'?S|AMUL|TATA|NESTLE|CADBURY|NABATI|MAGGI)\b"
        match = re.search(pattern, full_text, re.IGNORECASE)
        if not match:
            return None

        raw_snippet = (match.group(1) or match.group(2)).strip()
        matching_regions = self._find_matching_regions(regions, r"(?:brand|britannia|metrixa|parle|amul|tata|nestle|cadbury|nabati|maggi)")
        return ParsedEntity(
            field_type=FieldType.BRAND_NAME,
            raw_value=raw_snippet,
            normalized_value={"name": raw_snippet.title(), "brand_name": raw_snippet.title()},
            status=ObservationStatus.OBSERVED,
            confidence=self._compute_confidence(matching_regions),
            bounding_box=self._compute_bounding_box(matching_regions),
            source_region_ids=[r.id for r in matching_regions],
        )

    def _parse_generic_name(self, regions: List[OCRRegion], full_text: str) -> Optional[ParsedEntity]:
        # Match statutory common/generic commodity declarations under Rule 6(1)(b)
        pattern = r"(?:generic|common\s*(?:commodity)?|commodity)\s*[:\-]\s*([^\n\r]+)|\b(Biscuits?|Cookies?|Tea|Coffee|Rice|Flour|Atta|Noodles|Snacks|Namkeen|Wafers?)\b"
        for m in re.finditer(pattern, full_text, re.IGNORECASE):
            raw_val = (m.group(1) or m.group(2)).strip()
            start_pos = m.start()
            prefix = full_text[max(0, start_pos - 35):start_pos].lower()
            # Discard nutritional / ingredient words to avoid false commodity classification
            if any(term in prefix for term in ["ingredient", "contains", "refined", "wheat", "palm", "invert"]):
                continue
            matching_regions = self._find_matching_regions(regions, r"(?:generic|commodity|biscuits?|cookies?|tea|coffee|rice|noodles|wafers?|flour|atta)")
            return ParsedEntity(
                field_type=FieldType.GENERIC_NAME,
                raw_value=raw_val,
                normalized_value={"name": raw_val.title(), "generic_name": raw_val.title()},
                status=ObservationStatus.OBSERVED,
                confidence=self._compute_confidence(matching_regions),
                bounding_box=self._compute_bounding_box(matching_regions),
                source_region_ids=[r.id for r in matching_regions],
            )
        return None

    def _parse_product_name(self, regions: List[OCRRegion], full_text: str) -> Optional[ParsedEntity]:
        # 1. Explicit declaration
        pattern = r"(?:product\s*name)\s*[:\-]\s*([^\n\r]+)"
        match = re.search(pattern, full_text, re.IGNORECASE)
        if match:
            raw_snippet = match.group(1).strip()
            norm_data = {"name": raw_snippet.title()}
            matching_regions = self._find_matching_regions(regions, r"(?:brand|product|name)")
            return ParsedEntity(
                field_type=FieldType.PRODUCT_NAME,
                raw_value=raw_snippet,
                normalized_value=norm_data,
                status=ObservationStatus.OBSERVED,
                confidence=self._compute_confidence(matching_regions),
                bounding_box=self._compute_bounding_box(matching_regions),
                source_region_ids=[r.id for r in matching_regions],
            )

        # 2. Known brand / commodity composite patterns with strict word boundaries
        patterns = [
            r"\b(METRIXA\s+[A-Za-z\s]+TEA)\b",
            r"\b(Premium\s+[A-Za-z\s]+)\b",
            r"\b(ORGANIC\s+[A-Za-z\s]+)\b",
            r"\b((?:BRITANNIA\s+)?MILK\s+BIKIS(?:\s+Biscuits?)?)\b",
            r"\b(MILK\s+BIKIS)\b",
            r"\b((?:BRITANNIA\s+)?MARIE\s+GOLD(?:\s+Biscuits?)?)\b",
            r"\b(MARIE\s+GOLD)\b",
            r"\b(GOOD\s+DAY)\b",
            r"\b(50-50)\b",
            r"\b(BOURBON)\b",
            r"\b(TREAT)\b",
            r"\b(NUTRI\s*CHOICE)\b",
            r"\b((?:NESTLE\s+)?MAGGI(?:\s+2-?MINUTES?)?(?:\s+NOODLES?)?)\b",
            r"\b((?:NABATI\s+)?RICHOCO(?:\s+WAFERS?)?)\b",
            r"\b(RICHOCO(?:\s+WAFERS?)?)\b",
            r"\b(MAGGI(?:\s+NOODLES?)?)\b",
            r"\b(2-?MINUTE(?:\s+NOODLES?)?)\b",
        ]
        for p in patterns:
            m = re.search(p, full_text, re.IGNORECASE)
            if m:
                raw_snippet = m.group(1).strip()
                if len(raw_snippet) < 3 or raw_snippet.lower() in ["contains", "inside", "pack", "packs"]:
                    continue
                norm_data = {"name": raw_snippet.title()}
                matching_regions = self._find_matching_regions(regions, r"(?:metrixa|premium|organic|bikis|marie|gold|bourbon|treat|nutrichoice|maggi|richoco|nabati|noodles|wafer)")
                return ParsedEntity(
                    field_type=FieldType.PRODUCT_NAME,
                    raw_value=raw_snippet,
                    normalized_value=norm_data,
                    status=ObservationStatus.OBSERVED,
                    confidence=self._compute_confidence(matching_regions),
                    bounding_box=self._compute_bounding_box(matching_regions),
                    source_region_ids=[r.id for r in matching_regions],
                )
        return None

    def _parse_batch_number(self, regions: List[OCRRegion], full_text: str) -> Optional[ParsedEntity]:
        pattern = r"(?:batch\s*no\.?|lot\s*no\.?|b\.?\s*no\.?)\s*[:\-]?\s*([A-Za-z0-9\-]+)"
        match = re.search(pattern, full_text, re.IGNORECASE)
        if not match:
            return None

        raw_snippet = match.group(0).strip()
        batch_val = match.group(1).strip()
        matching_regions = self._find_matching_regions(regions, r"(?:batch|lot)")
        return ParsedEntity(
            field_type=FieldType.BATCH_NUMBER,
            raw_value=raw_snippet,
            normalized_value={"batch_number": batch_val},
            status=ObservationStatus.OBSERVED,
            confidence=self._compute_confidence(matching_regions),
            bounding_box=self._compute_bounding_box(matching_regions),
            source_region_ids=[r.id for r in matching_regions],
        )
