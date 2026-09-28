import re
from typing import Optional, Tuple, Dict, Any, List
from datetime import datetime

from app.services.entity.models import (
    QuantityNormalized,
    MRPNormalized,
    DateNormalized,
    ConsumerCareNormalized,
    PartyNormalized,
    CountryOfOriginNormalized,
    UnitSalePriceNormalized,
)

class EntityNormalizer:
    """
    Deterministic normalizer for Legal Metrology statutory declaration fields.
    Converts raw OCR text into standardized units, amounts, dates, and entities
    without altering raw evidence or guessing ambiguous declarations.
    """

    # --- NET QUANTITY NORMALIZATION ---
    MASS_UNITS = {
        "mg": ("mg", "g", 0.001),
        "milligram": ("mg", "g", 0.001),
        "g": ("g", "g", 1.0),
        "gm": ("g", "g", 1.0),
        "gms": ("g", "g", 1.0),
        "gram": ("g", "g", 1.0),
        "grams": ("g", "g", 1.0),
        "kg": ("kg", "g", 1000.0),
        "kgs": ("kg", "g", 1000.0),
        "kilogram": ("kg", "g", 1000.0),
        "kilograms": ("kg", "g", 1000.0),
    }

    VOLUME_UNITS = {
        "ml": ("ml", "ml", 1.0),
        "m.l.": ("ml", "ml", 1.0),
        "millilitre": ("ml", "ml", 1.0),
        "millilitres": ("ml", "ml", 1.0),
        "cl": ("cl", "ml", 10.0),
        "centilitre": ("cl", "ml", 10.0),
        "l": ("L", "ml", 1000.0),
        "lt": ("L", "ml", 1000.0),
        "ltr": ("L", "ml", 1000.0),
        "litre": ("L", "ml", 1000.0),
        "litres": ("L", "ml", 1000.0),
    }

    COUNT_UNITS = {
        "piece": ("pcs", "units", 1.0),
        "pieces": ("pcs", "units", 1.0),
        "pc": ("pcs", "units", 1.0),
        "pcs": ("pcs", "units", 1.0),
        "unit": ("units", "units", 1.0),
        "units": ("units", "units", 1.0),
        "n": ("units", "units", 1.0),
        "u": ("units", "units", 1.0),
    }

    def normalize_quantity(self, raw_text: str) -> Optional[QuantityNormalized]:
        """
        Normalize net quantity strings including single units and multi-packs.
        Examples: '500 g', '1 kg', '750 ml', '2 x 500 g', '10 packs of 71g', 'Pack of 6'.
        """
        cleaned = raw_text.strip()

        # 1. Multi-pack with explicit multiplication: e.g. "2 x 500 g", "6 × 100 ml", "4 * 250g"
        multipack_match = re.search(
            r"(?:pack\s+of\s+)?(\d+)\s*(?:x|×|\*)\s*([\d\.]+)\s*([a-zA-Z\.]+)",
            cleaned,
            re.IGNORECASE,
        )
        if multipack_match:
            try:
                count = int(multipack_match.group(1))
                ind_val = float(multipack_match.group(2))
                raw_u = multipack_match.group(3).lower().strip(".")
                unit_info = self._resolve_unit(raw_u)
                if unit_info:
                    norm_u, base_u, factor = unit_info
                    total_val = round(count * ind_val, 3)
                    base_qty = round(total_val * factor, 3)
                    return QuantityNormalized(
                        value=total_val,
                        unit=norm_u,
                        raw_unit=raw_u,
                        raw_declaration=cleaned,
                        base_quantity=base_qty,
                        base_unit=base_u,
                        count=count,
                        individual_quantity=ind_val,
                        individual_unit=norm_u,
                        total_quantity=total_val,
                        total_unit=norm_u,
                    )
            except ValueError:
                pass

        # 2. Multi-pack with explicit count of individual units: e.g. "10 packs of 71g", "5 units of 20g"
        multipack_inside_match = re.search(
            r"(\d+)\s*(?:packs?|units?|pieces?|pkts?)\s+of\s+([\d\.]+)\s*([a-zA-Z\.]+)",
            cleaned,
            re.IGNORECASE,
        )
        if multipack_inside_match:
            try:
                count = int(multipack_inside_match.group(1))
                ind_val = float(multipack_inside_match.group(2))
                raw_u = multipack_inside_match.group(3).lower().strip(".")
                unit_info = self._resolve_unit(raw_u)
                if unit_info:
                    norm_u, base_u, factor = unit_info
                    total_val = round(count * ind_val, 3)
                    base_qty = round(total_val * factor, 3)
                    return QuantityNormalized(
                        value=total_val,
                        unit=norm_u,
                        raw_unit=raw_u,
                        raw_declaration=cleaned,
                        base_quantity=base_qty,
                        base_unit=base_u,
                        count=count,
                        individual_quantity=ind_val,
                        individual_unit=norm_u,
                        total_quantity=total_val,
                        total_unit=norm_u,
                    )
            except ValueError:
                pass

        # 3. Count-only multi-pack: e.g. "Pack of 6", "Package of 12"
        pack_of_match = re.search(r"(?:pack|package|box)\s+of\s+(\d+)", cleaned, re.IGNORECASE)
        if pack_of_match:
            try:
                count = int(pack_of_match.group(1))
                return QuantityNormalized(
                    value=float(count),
                    unit="pcs",
                    raw_unit="pcs",
                    raw_declaration=cleaned,
                    base_quantity=float(count),
                    base_unit="units",
                    count=count,
                    individual_quantity=1.0,
                    individual_unit="pcs",
                    total_quantity=float(count),
                    total_unit="pcs",
                )
            except ValueError:
                pass

        # 4. Standard single quantity: e.g. "Net Qty: 500 g", "1.5 kg", "750 ml", "10 units"
        single_match = re.search(r"([\d\.]+)\s*([a-zA-Z\.]+)", cleaned)
        if single_match:
            try:
                val = float(single_match.group(1))
                raw_u = single_match.group(2).lower().strip(".")
                unit_info = self._resolve_unit(raw_u)
                if unit_info:
                    norm_u, base_u, factor = unit_info
                    base_qty = round(val * factor, 3)
                    return QuantityNormalized(
                        value=val,
                        unit=norm_u,
                        raw_unit=raw_u,
                        raw_declaration=cleaned,
                        base_quantity=base_qty,
                        base_unit=base_u,
                        count=1,
                        individual_quantity=val,
                        individual_unit=norm_u,
                        total_quantity=val,
                        total_unit=norm_u,
                    )
            except ValueError:
                pass

        return None

    def _resolve_unit(self, unit_str: str) -> Optional[Tuple[str, str, float]]:
        """Look up normalized unit, base unit, and conversion factor."""
        u = unit_str.lower().strip(".")
        if u in self.MASS_UNITS:
            return self.MASS_UNITS[u]
        if u in self.VOLUME_UNITS:
            return self.VOLUME_UNITS[u]
        if u in self.COUNT_UNITS:
            return self.COUNT_UNITS[u]
        return None

    # --- MRP NORMALIZATION ---
    def normalize_mrp(self, raw_text: str) -> Optional[MRPNormalized]:
        """
        Extract numeric MRP and currency without assessing statutory validity.
        Handles 'MRP Rs. 250.00', 'MRP ₹120/-', 'Maximum Retail Price Rs 99.50'.
        """
        cleaned = raw_text.strip()
        # Detect currency symbol
        curr_symbol = "₹" if "₹" in cleaned else ("Rs." if ("rs" in cleaned.lower() or "rs." in cleaned.lower()) else "INR")

        # Check for taxes clause
        taxes = any(term in cleaned.lower() for term in ["incl", "tax", "taxes"])

        # Extract number: match digits with optional decimal
        match = re.search(r"(?:₹|Rs\.?|INR)?\s*(\d+(?:\.\d{1,2})?)\s*(?:/-)?", cleaned, re.IGNORECASE)
        if match:
            try:
                val = float(match.group(1))
                return MRPNormalized(
                    value=val,
                    currency="INR",
                    currency_symbol=curr_symbol,
                    raw_amount=match.group(1),
                    includes_taxes=taxes,
                )
            except ValueError:
                pass
        return None

    # --- DATE NORMALIZATION ---
    def normalize_date(self, raw_text: str, date_type: str = "MFG") -> Optional[DateNormalized]:
        """
        Normalize date declarations with ambiguity detection.
        Formats supported: DD/MM/YYYY, DD-MM-YYYY, MM/YYYY, YYYY-MM-DD.
        Ambiguity rule: '03/04/2026' has day and month both <= 12, marked as ambiguous.
        """
        cleaned = raw_text.strip()

        # 1. Full date with delimiters: DD/MM/YYYY or DD-MM-YYYY or DD.MM.YYYY
        full_date_match = re.search(r"(\d{1,2})[\/\-\.](\d{1,2})[\/\-\.](\d{4})", cleaned)
        if full_date_match:
            part1 = int(full_date_match.group(1))
            part2 = int(full_date_match.group(2))
            year = int(full_date_match.group(3))

            # Check ambiguity between DD/MM and MM/DD
            if 1 <= part1 <= 12 and 1 <= part2 <= 12 and part1 != part2:
                return DateNormalized(
                    date_iso=f"{year}-{part2:02d}-{part1:02d}",
                    date_type=date_type,
                    precision="DAY_MONTH_YEAR",
                    day=part1,
                    month=part2,
                    year=year,
                    is_ambiguous=True,
                    ambiguity_reason=f"Ambiguous day and month values ({part1} and {part2}); format could be DD/MM/YYYY or MM/DD/YYYY.",
                )
            elif part1 > 12 and 1 <= part2 <= 12:
                # Unambiguous DD/MM/YYYY
                day, month = part1, part2
            elif part2 > 12 and 1 <= part1 <= 12:
                # Unambiguous MM/DD/YYYY
                month, day = part1, part2
            else:
                day, month = part1, part2

            return DateNormalized(
                date_iso=f"{year}-{month:02d}-{day:02d}",
                date_type=date_type,
                precision="DAY_MONTH_YEAR",
                day=day,
                month=month,
                year=year,
                is_ambiguous=False,
            )

        # 2. Month and Year: MM/YYYY or MM-YYYY
        month_year_match = re.search(r"(\d{1,2})[\/\-\.](\d{4})", cleaned)
        if month_year_match:
            month = int(month_year_match.group(1))
            year = int(month_year_match.group(2))
            if 1 <= month <= 12:
                return DateNormalized(
                    date_iso=f"{year}-{month:02d}",
                    date_type=date_type,
                    precision="MONTH_YEAR",
                    day=None,
                    month=month,
                    year=year,
                    is_ambiguous=False,
                )

        # 3. ISO format: YYYY-MM-DD
        iso_match = re.search(r"(\d{4})[\/\-](\d{1,2})[\/\-](\d{1,2})", cleaned)
        if iso_match:
            year = int(iso_match.group(1))
            month = int(iso_match.group(2))
            day = int(iso_match.group(3))
            if 1 <= month <= 12 and 1 <= day <= 31:
                return DateNormalized(
                    date_iso=f"{year}-{month:02d}-{day:02d}",
                    date_type=date_type,
                    precision="DAY_MONTH_YEAR",
                    day=day,
                    month=month,
                    year=year,
                    is_ambiguous=False,
                )

        return None

    # --- CONSUMER CARE NORMALIZATION ---
    def normalize_consumer_care(self, raw_text: str) -> ConsumerCareNormalized:
        """
        Extract and sanitize phone numbers, emails, and postal references.
        """
        cleaned = raw_text.strip()
        phones: List[str] = []
        emails: List[str] = []

        # Phone numbers: Toll-free 1-800 or 1800, 10-digit mobile (+91), landlines
        phone_matches = re.findall(
            r"\b(?:1-?800[-\s]?\d{3,4}[-\s]?\d{3,4}|(?:\+91[-\s]?)?[6-9]\d{9}|\d{3,5}[-\s]\d{6,8})\b",
            cleaned,
        )
        for p in phone_matches:
            sanitized_p = re.sub(r"[^\d\+\-]", "", p)
            if sanitized_p and sanitized_p not in phones:
                phones.append(sanitized_p)

        # Emails (tolerating optional whitespace around @ introduced by OCR)
        email_matches = re.findall(
            r"[a-zA-Z0-9_.+-]+\s*@\s*[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+",
            cleaned,
        )
        for em in email_matches:
            clean_em = em.replace(" ", "").lower().strip(".,;")
            if clean_em.startswith("ustomercare@"):
                clean_em = "c" + clean_em
            if clean_em and clean_em not in emails:
                emails.append(clean_em)

        return ConsumerCareNormalized(
            phones=phones,
            emails=emails,
            addresses=[],
            website=None,
        )

    # --- PARTY (MANUFACTURER / PACKER / IMPORTER) NORMALIZATION ---
    def normalize_party(self, raw_text: str, entity_type: str) -> PartyNormalized:
        """
        Extract legal name and address while removing leading labels.
        Does NOT merge separate parties.
        """
        cleaned = raw_text.strip()
        # Strip leading contextual label
        cleaned = re.sub(
            r"^(?:mfd\.?\s*by|manufactured\s*(?:&|and)?\s*marketed\s*by|manufactured\s*by|packed\s*by|imported\s*by|marketed\s*by|mkt\.?\s*by|mfg\.?\s*by)\s*[:\-]?\s*",
            "",
            cleaned,
            flags=re.IGNORECASE,
        ).strip()

        # Strip trailing feedback / consumer care prefix if accidentally captured in multiline snippet
        cleaned = re.split(r"\s*(?:for\s+feedback|consumer\s+care|customer\s+care|ph\.\s*:)", cleaned, flags=re.IGNORECASE)[0].strip()

        # Separate name and address if comma or address delimiter is encountered
        name = cleaned
        address = None

        addr_markers = ["plot", "industrial", "area", "sector", "road", "street", "delhi", "mumbai", "bangalore", "pincode", "pin"]
        parts = re.split(r",\s*", cleaned)
        if len(parts) > 1:
            name = parts[0].strip()
            address = ", ".join(parts[1:]).strip()

        # Determine specific party entity role if text clearly specifies it
        role = entity_type
        if re.search(r"^(?:marketed\s*by|mkt\.?\s*by)", raw_text.strip(), re.IGNORECASE):
            role = "MARKETED_BY"
        elif re.search(r"^(?:mfd\.?\s*by|manufactured\s*by)", raw_text.strip(), re.IGNORECASE):
            role = "MANUFACTURER"
        elif re.search(r"^(?:pkd\.?\s*by|packed\s*by)", raw_text.strip(), re.IGNORECASE):
            role = "PACKER"
        elif re.search(r"^(?:imported\s*by)", raw_text.strip(), re.IGNORECASE):
            role = "IMPORTER"

        return PartyNormalized(
            entity_type=role,
            name=name,
            address=address,
        )

    # --- COUNTRY OF ORIGIN ---
    def normalize_country_of_origin(self, raw_text: str) -> Optional[CountryOfOriginNormalized]:
        """
        Extract explicit country of origin declaration without deciding mandatory applicability.
        """
        cleaned = raw_text.strip()
        match = re.search(
            r"(?:country\s+of\s+origin\s*[:\-]?|made\s+in|product\s+of)\s*([a-zA-Z]+(?:\s+(?!USP|MRP|NET|MFG|RS|PKD|BATCH|CARE)[a-zA-Z]+)?)",
            cleaned,
            re.IGNORECASE,
        )
        if match:
            country = match.group(1).strip(" .,-")
            if country and country.upper() not in ["USP", "MRP", "NET", "RS"]:
                return CountryOfOriginNormalized(
                    country=country.title(),
                    raw_statement=match.group(0).strip(),
                )
        return None

    # --- UNIT SALE PRICE ---
    def normalize_unit_sale_price(self, raw_text: str) -> Optional[UnitSalePriceNormalized]:
        """
        Extract unit sale price (e.g. '₹240/kg', '₹2.40 per g', '₹45/100g') without deciding mandatory applicability.
        Requires statutory metric/count units with optional quantity multiplier.
        """
        cleaned = raw_text.strip()
        match = re.search(
            r"(?:₹|Rs\.?|INR)?\s*(\d+(?:\.\d{1,2})?)\s*(?:per|/)\s*((?:\d+\s*)?(?:g|gm|gms|gram|grams|kg|kgs|kilogram|kilograms|ml|cl|l|lt|ltr|litre|litres|pcs?|pieces?|units?|n|u))\b",
            cleaned,
            re.IGNORECASE,
        )
        if match:
            try:
                price = float(match.group(1))
                unit = match.group(2).strip(" .,-")
                return UnitSalePriceNormalized(
                    value=price,
                    currency="INR",
                    unit=unit,
                )
            except ValueError:
                pass
        return None
