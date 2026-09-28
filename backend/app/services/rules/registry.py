from typing import List, Dict, Any
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.rule_definition import RuleDefinition
from app.models.enums import RuleSeverity

# Authoritative Statutory Rules under Legal Metrology (Packaged Commodities) Rules, 2011
# Source: G.S.R. 202(E) dated 7th March 2011 and official Ministry amendments
AUTHORITATIVE_RULES: List[Dict[str, Any]] = [
    {
        "rule_code": "PCR-2011-R06-1-A",
        "version": "1.0.0",
        "legal_act": "Legal Metrology Act, 2009",
        "rule_reference": "Rule 6(1)(a)",
        "clause_reference": "Sub-rule (1) Clause (a)",
        "title": "Name and Address of Manufacturer, Packer or Importer",
        "description": "Every package shall bear the name and complete address of the manufacturer, or where manufacturer is not the packer, the name and address of the manufacturer and packer, or for imported packages, the name and address of the importer.",
        "source_document": "G.S.R. 202(E) dated 7th March 2011",
        "source_url": "https://consumeraffairs.gov.in/sites/default/files/pcmr2011.pdf",
        "jurisdiction": "IN",
        "category": "MANDATORY_DECLARATION",
        "is_test_rule": False,
        "is_active": True,
        "severity": RuleSeverity.MANDATORY,
        "effective_from": datetime(2011, 4, 1, 0, 0, 0, tzinfo=timezone.utc),
        "applicability_conditions": {"commodity_scope": "ALL_RETAIL_PACKAGES"},
        "exemptions": {"exempt_industrial_consumers": True},
        "parameters": {"require_importer": False},
        "evaluation_logic": {"type": "MANUFACTURER_PACKER_IMPORTER"},
        "evidence_requirements": {"required_fields": ["MANUFACTURER_NAME", "PACKER_NAME", "IMPORTER_NAME"]},
    },
    {
        "rule_code": "PCR-2011-R06-1-B",
        "version": "1.0.0",
        "legal_act": "Legal Metrology Act, 2009",
        "rule_reference": "Rule 6(1)(b)",
        "clause_reference": "Sub-rule (1) Clause (b)",
        "title": "Generic or Common Name of the Commodity",
        "description": "The common or generic names of the commodity contained in the package and in case of packages with more than one product, the name and quantity of each product.",
        "source_document": "G.S.R. 202(E) dated 7th March 2011",
        "source_url": "https://consumeraffairs.gov.in/sites/default/files/pcmr2011.pdf",
        "jurisdiction": "IN",
        "category": "MANDATORY_DECLARATION",
        "is_test_rule": False,
        "is_active": True,
        "severity": RuleSeverity.MANDATORY,
        "effective_from": datetime(2011, 4, 1, 0, 0, 0, tzinfo=timezone.utc),
        "applicability_conditions": {"commodity_scope": "ALL_RETAIL_PACKAGES"},
        "exemptions": {},
        "parameters": {},
        "evaluation_logic": {"type": "GENERIC_NAME"},
        "evidence_requirements": {"required_fields": ["GENERIC_NAME"]},
    },
    {
        "rule_code": "PCR-2011-R06-1-C",
        "version": "1.0.0",
        "legal_act": "Legal Metrology Act, 2009",
        "rule_reference": "Rule 6(1)(c)",
        "clause_reference": "Sub-rule (1) Clause (c)",
        "title": "Net Quantity Declaration in Standard Units",
        "description": "The net quantity, in terms of the standard unit of weight or measure, of the commodity contained in the package or where the commodity is packed or sold by number, the number of the commodity contained in the package.",
        "source_document": "G.S.R. 202(E) dated 7th March 2011",
        "source_url": "https://consumeraffairs.gov.in/sites/default/files/pcmr2011.pdf",
        "jurisdiction": "IN",
        "category": "MANDATORY_DECLARATION",
        "is_test_rule": False,
        "is_active": True,
        "severity": RuleSeverity.MANDATORY,
        "effective_from": datetime(2011, 4, 1, 0, 0, 0, tzinfo=timezone.utc),
        "applicability_conditions": {"commodity_scope": "ALL_RETAIL_PACKAGES"},
        "exemptions": {"exempt_under_10g_or_10ml": True},
        "parameters": {"enforce_metric_units": True},
        "evaluation_logic": {"type": "NET_QUANTITY_DECLARATION"},
        "evidence_requirements": {"required_fields": ["NET_QUANTITY"]},
    },
    {
        "rule_code": "PCR-2011-R06-1-D",
        "version": "1.0.0",
        "legal_act": "Legal Metrology Act, 2009",
        "rule_reference": "Rule 6(1)(d)",
        "clause_reference": "Sub-rule (1) Clause (d)",
        "title": "Month and Year of Manufacture or Packing",
        "description": "The month and year in which the commodity is manufactured or pre-packed or imported shall be clearly indicated on the package.",
        "source_document": "G.S.R. 202(E) dated 7th March 2011",
        "source_url": "https://consumeraffairs.gov.in/sites/default/files/pcmr2011.pdf",
        "jurisdiction": "IN",
        "category": "MANDATORY_DECLARATION",
        "is_test_rule": False,
        "is_active": True,
        "severity": RuleSeverity.MANDATORY,
        "effective_from": datetime(2011, 4, 1, 0, 0, 0, tzinfo=timezone.utc),
        "applicability_conditions": {"commodity_scope": "ALL_RETAIL_PACKAGES"},
        "exemptions": {},
        "parameters": {"require_month_year": True},
        "evaluation_logic": {"type": "DATE_DECLARATION"},
        "evidence_requirements": {"required_fields": ["MFG_DATE"]},
    },
    {
        "rule_code": "PCR-2011-R06-1-DA",
        "version": "1.0.0",
        "legal_act": "Legal Metrology Act, 2009",
        "rule_reference": "Rule 6(1)(da)",
        "clause_reference": "Sub-rule (1) Clause (da)",
        "title": "Maximum Retail Price (MRP) Inclusive of All Taxes",
        "description": "The retail sale price of the package shall clearly indicate that it is the maximum retail price inclusive of all taxes in the form 'MRP Rs. / INR ... incl. of all taxes'.",
        "source_document": "G.S.R. 202(E) dated 7th March 2011",
        "source_url": "https://consumeraffairs.gov.in/sites/default/files/pcmr2011.pdf",
        "jurisdiction": "IN",
        "category": "MANDATORY_DECLARATION",
        "is_test_rule": False,
        "is_active": True,
        "severity": RuleSeverity.MANDATORY,
        "effective_from": datetime(2011, 4, 1, 0, 0, 0, tzinfo=timezone.utc),
        "applicability_conditions": {"commodity_scope": "ALL_RETAIL_PACKAGES"},
        "exemptions": {},
        "parameters": {"require_tax_inclusive": True},
        "evaluation_logic": {"type": "MRP_DECLARATION"},
        "evidence_requirements": {"required_fields": ["MRP"]},
    },
    {
        "rule_code": "PCR-2011-R06-1-E",
        "version": "1.0.0",
        "legal_act": "Legal Metrology Act, 2009",
        "rule_reference": "Rule 6(1)(e)",
        "clause_reference": "Sub-rule (1) Clause (e)",
        "title": "Consumer Care Details for Consumer Complaints",
        "description": "Every package shall bear the name, address, telephone number and email address of that person or of the office which may be contacted in case of the consumer complaints.",
        "source_document": "G.S.R. 202(E) dated 7th March 2011",
        "source_url": "https://consumeraffairs.gov.in/sites/default/files/pcmr2011.pdf",
        "jurisdiction": "IN",
        "category": "MANDATORY_DECLARATION",
        "is_test_rule": False,
        "is_active": True,
        "severity": RuleSeverity.MANDATORY,
        "effective_from": datetime(2011, 4, 1, 0, 0, 0, tzinfo=timezone.utc),
        "applicability_conditions": {"commodity_scope": "ALL_RETAIL_PACKAGES"},
        "exemptions": {},
        "parameters": {},
        "evaluation_logic": {"type": "CONSUMER_CARE"},
        "evidence_requirements": {"required_fields": ["CONSUMER_CARE_PHONE", "CONSUMER_CARE_EMAIL"]},
    },
    {
        "rule_code": "PCR-2011-R06-1-F",
        "version": "1.0.0",
        "legal_act": "Legal Metrology Act, 2009",
        "rule_reference": "Rule 6(1)(f)",
        "clause_reference": "Sub-rule (1) Clause (f)",
        "title": "Country of Origin for Imported Products",
        "description": "The name of the country of origin or manufacture or assembly in case of imported products shall be clearly mentioned on the package.",
        "source_document": "G.S.R. 202(E) dated 7th March 2011",
        "source_url": "https://consumeraffairs.gov.in/sites/default/files/pcmr2011.pdf",
        "jurisdiction": "IN",
        "category": "MANDATORY_DECLARATION",
        "is_test_rule": False,
        "is_active": True,
        "severity": RuleSeverity.MANDATORY,
        "effective_from": datetime(2011, 4, 1, 0, 0, 0, tzinfo=timezone.utc),
        "applicability_conditions": {"commodity_scope": "IMPORTED_COMMODITY", "requires_imported": True},
        "exemptions": {},
        "parameters": {},
        "evaluation_logic": {"type": "COUNTRY_OF_ORIGIN"},
        "evidence_requirements": {"required_fields": ["COUNTRY_OF_ORIGIN"]},
    },
    {
        "rule_code": "PCR-2011-R06-1-G",
        "version": "1.0.0",
        "legal_act": "Legal Metrology Act, 2009",
        "rule_reference": "Rule 6(1)(g)",
        "clause_reference": "Sub-rule (1) Clause (g)",
        "title": "Unit Sale Price on Pre-packaged Commodities",
        "description": "The unit sale price shall be declared on every package where package net quantity exceeds statutory threshold as prescribed by amendment.",
        "source_document": "G.S.R. 779(E) dated 2nd November 2021",
        "source_url": "https://consumeraffairs.gov.in/sites/default/files/pcmr_amend_2021.pdf",
        "jurisdiction": "IN",
        "category": "MANDATORY_DECLARATION",
        "is_test_rule": False,
        "is_active": True,
        "severity": RuleSeverity.MANDATORY,
        "effective_from": datetime(2022, 12, 1, 0, 0, 0, tzinfo=timezone.utc),
        "applicability_conditions": {"commodity_scope": "ALL_RETAIL_PACKAGES", "check_usp_applicability": True},
        "exemptions": {},
        "parameters": {"min_base_quantity": 1000.0},  # Threshold: > 1kg / 1L
        "evaluation_logic": {"type": "UNIT_SALE_PRICE"},
        "evidence_requirements": {"required_fields": ["UNIT_SALE_PRICE"]},
    },
    {
        "rule_code": "PCR-2011-R07-1",
        "version": "1.0.0",
        "legal_act": "Legal Metrology Act, 2009",
        "rule_reference": "Rule 7(1)",
        "clause_reference": "Sub-rule (1) Table 1",
        "title": "Minimum Height of Numerals and Letters on Principal Display Panel",
        "description": "The height of any numeral and letter in the declaration on the principal display panel shall not be less than the minimum height specified in Table 1 according to the area of the principal display panel.",
        "source_document": "G.S.R. 202(E) dated 7th March 2011",
        "source_url": "https://consumeraffairs.gov.in/sites/default/files/pcmr2011.pdf",
        "jurisdiction": "IN",
        "category": "PDP_GEOMETRY",
        "is_test_rule": False,
        "is_active": True,
        "severity": RuleSeverity.MANDATORY,
        "effective_from": datetime(2011, 4, 1, 0, 0, 0, tzinfo=timezone.utc),
        "applicability_conditions": {"commodity_scope": "ALL_RETAIL_PACKAGES", "requires_front_pdp": True},
        "exemptions": {},
        "parameters": {"target_field": "NET_QUANTITY", "min_height_mm": 2.0},
        "evaluation_logic": {"type": "PDP_GEOMETRY_PLACEMENT_AND_SIZE"},
        "evidence_requirements": {"requires_calibration": True, "target_field": "NET_QUANTITY"},
    }
]

# Explicitly Tagged Test / Non-Production Rules
TEST_NON_PRODUCTION_RULES: List[Dict[str, Any]] = [
    {
        "rule_code": "TEST-LMR-MANDATORY-PLACEHOLDER",
        "version": "1.0.0",
        "legal_act": "NON_PRODUCTION_TEST_HARNESS",
        "rule_reference": "TestSection 101",
        "clause_reference": "Test Clause A",
        "title": "TEST / NON_PRODUCTION (REQUIRES_AUTHORITATIVE_VERIFICATION) - Placeholder Mandatory Test",
        "description": "Test rule fixture to verify deterministic failure and pass mechanics under controlled unit testing.",
        "source_document": "INTERNAL_TEST_HARNESS_V1",
        "source_url": None,
        "jurisdiction": "IN",
        "category": "TEST_CATEGORY",
        "is_test_rule": True,
        "is_active": True,
        "severity": RuleSeverity.MANDATORY,
        "effective_from": None,
        "applicability_conditions": {"commodity_scope": "ALL_RETAIL_PACKAGES"},
        "exemptions": {},
        "parameters": {},
        "evaluation_logic": {"type": "MANDATORY_DECLARATION_PRESENCE"},
        "evidence_requirements": {"required_fields": ["NET_QUANTITY"]},
    }
]

class RuleRegistry:
    """
    Registry and loader for declarative, versioned Legal Metrology rules.
    Loads and seeds rules into PostgreSQL database idempotently.
    Enforces strict segregation between Authoritative Legal Rules and Test Rules.
    """
    AUTHORITATIVE_RULES = AUTHORITATIVE_RULES
    TEST_NON_PRODUCTION_RULES = TEST_NON_PRODUCTION_RULES

    @classmethod
    async def seed_rules(cls, db: AsyncSession, include_test_rules: bool = True) -> int:
        """Idempotently seed authoritative statutory rules and test fixtures."""
        all_rules = list(AUTHORITATIVE_RULES)
        if include_test_rules:
            all_rules.extend(TEST_NON_PRODUCTION_RULES)

        count = 0
        for r_dict in all_rules:
            res = await db.execute(
                select(RuleDefinition).where(
                    RuleDefinition.rule_code == r_dict["rule_code"],
                    RuleDefinition.version == r_dict["version"],
                )
            )
            existing = res.scalar_one_or_none()
            if not existing:
                new_rule = RuleDefinition(**r_dict)
                db.add(new_rule)
                count += 1
            else:
                existing.evaluation_logic = r_dict.get("evaluation_logic", {})
                existing.evidence_requirements = r_dict.get("evidence_requirements", {})
                existing.title = r_dict.get("title", existing.title)
                existing.description = r_dict.get("description", existing.description)
                existing.parameters = r_dict.get("parameters", {})
                db.add(existing)
                count += 1

        if count > 0:
            await db.commit()

        return count
