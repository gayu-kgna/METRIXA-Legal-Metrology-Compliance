import io
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from PIL import Image as PILImage

from reportlab.lib.pagesizes import letter
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image as RLImage,
    KeepTogether,
    PageBreak,
    HRFlowable,
)
from reportlab.lib.colors import white, HexColor

from app.models.inspection import Inspection
from app.models.surface import InspectionSurface
from app.models.ocr_run import OCRRun
from app.models.observation import Observation
from app.models.pdp_geometry import PDPGeometry
from app.models.rule_evaluation import RuleEvaluation
from app.models.audit_log import AuditLog
from app.models.enums import ObservationSource
from app.models.evidence import EvidenceSnapshot
from app.services.storage.base import BaseStorageService
from app.services.evidence.integrity import calculate_sha256
from app.services.report.models import DossierOptions, DossierGenerationResult
from app.services.report.templates import (
    NAVY,
    SLATE,
    TEAL,
    LIGHT_BG,
    ALT_ROW_BG,
    BORDER_COLOR,
    DARK_TEXT,
    MUTED_TEXT,
    PASS_BG,
    PASS_TEXT,
    PASS_BORDER,
    FAIL_BG,
    FAIL_TEXT,
    FAIL_BORDER,
    REVIEW_BG,
    REVIEW_TEXT,
    REVIEW_BORDER,
    INDETERMINATE_BG,
    INDETERMINATE_TEXT,
    INDETERMINATE_BORDER,
    NOT_APPLICABLE_BG,
    NOT_APPLICABLE_TEXT,
    NOT_APPLICABLE_BORDER,
    sanitize_text,
    NumberedCanvas,
    get_dossier_styles,
)

class DossierPDFGenerator:
    """
    High-Performance, Server-Side Explainable PDF Dossier Generator for Metrixa.
    Produces a 15-section, tamper-evident inspection dossier backed by the
    exact immutable perception and rule evaluation evidence snapshot.
    """

    def __init__(self, storage_service: Optional[BaseStorageService] = None):
        self.storage_service = storage_service
        self.styles = get_dossier_styles()

    async def generate_dossier(
        self,
        inspection: Inspection,
        surfaces: List[InspectionSurface],
        ocr_runs: List[OCRRun],
        observations: List[Observation],
        geometries: List[PDPGeometry],
        evaluations: List[RuleEvaluation],
        audit_logs: List[AuditLog],
        snapshot: EvidenceSnapshot,
        dossier_id: Optional[uuid.UUID] = None,
        report_version: int = 1,
        options: Optional[DossierOptions] = None,
    ) -> DossierGenerationResult:
        opts = options or DossierOptions()
        d_id = str(dossier_id or uuid.uuid4())
        now_iso = datetime.now(timezone.utc).isoformat()
        buffer = io.BytesIO()

        # Printable width for letter size (612 x 792) with 54pt (0.75 in) margins = 504pt
        page_width = 504

        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            leftMargin=54,
            rightMargin=54,
            topMargin=54,
            bottomMargin=54,
            title=f"Metrixa Inspection Dossier {inspection.inspection_number}",
            author="Metrixa Regulatory Platform",
        )

        story = []

        # =========================================================================
        # SECTION 1: Cover / Inspection Summary
        # =========================================================================
        story.append(Paragraph("METRIXA", self.styles["CoverTitle"]))
        story.append(Paragraph("Legal Metrology Inspection Dossier", self.styles["CoverSubtitle"]))
        story.append(HRFlowable(width="100%", thickness=2, color=NAVY, spaceBefore=2, spaceAfter=14))

        # Overall Status Badge
        overall_status_str = inspection.overall_status.value if hasattr(inspection.overall_status, "value") else str(inspection.overall_status)
        badge_style, badge_bg, badge_border = self._get_badge_format(overall_status_str)

        prod_name = "Not Associated"
        if inspection.product:
            prod_name = f"{inspection.product.brand_name} - {inspection.product.product_name}"

        inspector_name = inspection.inspector.full_name if inspection.inspector else "Unknown Inspector"
        inspector_role = inspection.inspector.role.value if inspection.inspector and hasattr(inspection.inspector.role, "value") else "OFFICER"

        cover_data = [
            [
                Paragraph("<b>Inspection Number:</b>", self.styles["Body"]),
                Paragraph(sanitize_text(inspection.inspection_number), self.styles["BodyBold"]),
                Paragraph("<b>Overall Status:</b>", self.styles["Body"]),
                self._create_badge_cell(overall_status_str, badge_style, badge_bg, badge_border),
            ],
            [
                Paragraph("<b>Product Under Test:</b>", self.styles["Body"]),
                Paragraph(sanitize_text(prod_name), self.styles["Body"]),
                Paragraph("<b>Dossier ID:</b>", self.styles["Body"]),
                Paragraph(sanitize_text(d_id[:18] + "..."), self.styles["TableCellCode"]),
            ],
            [
                Paragraph("<b>Inspection Date:</b>", self.styles["Body"]),
                Paragraph(sanitize_text(inspection.initiated_at.strftime("%Y-%m-%d %H:%M:%S UTC") if inspection.initiated_at else "N/A"), self.styles["Body"]),
                Paragraph("<b>Report Version:</b>", self.styles["Body"]),
                Paragraph(f"Version {report_version}", self.styles["BodyBold"]),
            ],
            [
                Paragraph("<b>Inspecting Officer:</b>", self.styles["Body"]),
                Paragraph(sanitize_text(f"{inspector_name} ({inspector_role})"), self.styles["Body"]),
                Paragraph("<b>Generated Timestamp:</b>", self.styles["Body"]),
                Paragraph(sanitize_text(now_iso[:19] + "Z"), self.styles["TableCellCode"]),
            ],
        ]

        t_cover = Table(cover_data, colWidths=[110, 150, 110, 134])
        t_cover.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("BACKGROUND", (0, 0), (-1, -1), LIGHT_BG),
            ("BOX", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ]))
        story.append(t_cover)
        story.append(Spacer(1, 14))

        # Legal Disclaimer Notice Box
        disclaimer_text = (
            "<b>LEGAL & EVIDENTIARY DISCLAIMER:</b><br/>"
            "This dossier is generated from Metrixa inspection evidence and is intended to support regulatory inspection review. "
            "It is <b>not</b> a government-issued certificate and does <b>not</b> by itself establish court admissibility. "
            "Statutory decisions remain subject to official verification and adjudication by authorized Legal Metrology officers "
            "in accordance with the Legal Metrology Act, 2009 and Legal Metrology (Packaged Commodities) Rules, 2011."
        )
        t_disc = Table([[Paragraph(disclaimer_text, self.styles["Disclaimer"])]], colWidths=[page_width])
        t_disc.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), HexColor("#FFFDF5")),
            ("BOX", (0, 0), (-1, -1), 1, HexColor("#ECC94B")),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ]))
        story.append(t_disc)
        story.append(Spacer(1, 14))

        # =========================================================================
        # SECTION 2: Inspection Metadata
        # =========================================================================
        story.append(Paragraph("1. Inspection Metadata", self.styles["SectionHeading"]))
        meta_data = [
            [
                Paragraph("Inspection ID", self.styles["TableHead"]),
                Paragraph(sanitize_text(str(inspection.id)), self.styles["TableCellCode"]),
                Paragraph("Retail Outlet", self.styles["TableHead"]),
                Paragraph(sanitize_text(inspection.retail_outlet_name or "Unspecified Outlet"), self.styles["TableCell"]),
            ],
            [
                Paragraph("Snapshot ID", self.styles["TableHead"]),
                Paragraph(sanitize_text(str(snapshot.id)), self.styles["TableCellCode"]),
                Paragraph("Outlet Address", self.styles["TableHead"]),
                Paragraph(sanitize_text(inspection.retail_outlet_address or "Unspecified Address"), self.styles["TableCell"]),
            ],
            [
                Paragraph("Evaluation Run ID", self.styles["TableHead"]),
                Paragraph(sanitize_text(str(snapshot.evaluation_run_id or "Active Run")), self.styles["TableCellCode"]),
                Paragraph("Geo-Coordinates", self.styles["TableHead"]),
                Paragraph(sanitize_text(str(inspection.geo_coordinates or "None Recorded")), self.styles["TableCellCode"]),
            ],
            [
                Paragraph("Surfaces Inspected", self.styles["TableHead"]),
                Paragraph(f"{len(surfaces)} Surface(s) Captured", self.styles["TableCellBold"]),
                Paragraph("Integrity Status", self.styles["TableHead"]),
                Paragraph("Cryptographically Sealed (SHA-256)", self.styles["TableCellBold"]),
            ],
        ]
        t_meta = Table(meta_data, colWidths=[105, 145, 105, 149])
        t_meta.setStyle(self._standard_table_style(has_header=False))
        story.append(t_meta)
        story.append(Spacer(1, 12))

        # =========================================================================
        # SECTION 3: Product Information
        # =========================================================================
        story.append(Paragraph("2. Product Information", self.styles["SectionHeading"]))
        prod_rows = [
            [
                Paragraph("Attribute", self.styles["TableHead"]),
                Paragraph("Observed / Raw Value", self.styles["TableHead"]),
                Paragraph("Normalized Statutory Value", self.styles["TableHead"]),
                Paragraph("Status", self.styles["TableHead"]),
                Paragraph("Conf.", self.styles["TableHead"]),
            ]
        ]

        obs_by_field = {o.field_type.value if hasattr(o.field_type, "value") else str(o.field_type): o for o in observations if o.is_latest}
        display_fields = [
            ("PRODUCT_NAME", "Product Name"),
            ("BRAND_NAME", "Brand Name"),
            ("NET_QUANTITY", "Net Quantity"),
            ("MRP", "Maximum Retail Price (MRP)"),
            ("UNIT_SALE_PRICE", "Unit Sale Price (USP)"),
            ("MANUFACTURER_NAME", "Manufacturer"),
            ("PACKER_NAME", "Packer"),
            ("IMPORTER_NAME", "Importer"),
            ("COUNTRY_OF_ORIGIN", "Country of Origin"),
            ("DATE_OF_MANUFACTURE", "Date of Manufacture"),
            ("CONSUMER_CARE_PHONE", "Consumer Care"),
        ]

        for f_key, f_label in display_fields:
            obs = obs_by_field.get(f_key)
            if obs:
                norm_str = str(obs.normalized_value) if obs.normalized_value else "N/A"
                if isinstance(obs.normalized_value, dict):
                    if "formatted" in obs.normalized_value:
                        norm_str = str(obs.normalized_value["formatted"])
                    elif "display" in obs.normalized_value:
                        norm_str = str(obs.normalized_value["display"])
                    elif "value" in obs.normalized_value:
                        norm_str = f"{obs.normalized_value['value']} {obs.normalized_value.get('unit', '')}".strip()

                status_val = obs.status.value if hasattr(obs.status, "value") else str(obs.status)
                prod_rows.append([
                    Paragraph(sanitize_text(f_label), self.styles["TableCellBold"]),
                    Paragraph(sanitize_text(obs.raw_value[:60]), self.styles["TableCell"]),
                    Paragraph(sanitize_text(norm_str[:60]), self.styles["TableCellBold"]),
                    Paragraph(sanitize_text(status_val), self.styles["TableCell"]),
                    Paragraph(f"{obs.confidence:.2f}", self.styles["TableCell"]),
                ])
            else:
                prod_rows.append([
                    Paragraph(sanitize_text(f_label), self.styles["TableCellBold"]),
                    Paragraph("<i>Not observed</i>", self.styles["TableCell"]),
                    Paragraph("<i>Indeterminate</i>", self.styles["TableCell"]),
                    Paragraph("MISSING", self.styles["TableCell"]),
                    Paragraph("0.00", self.styles["TableCell"]),
                ])

        t_prod = Table(prod_rows, colWidths=[120, 140, 130, 74, 40])
        t_prod.setStyle(self._standard_table_style(has_header=True))
        story.append(t_prod)
        story.append(Spacer(1, 14))

        # =========================================================================
        # SECTION 4: Package Surface Overview
        # =========================================================================
        story.append(Paragraph("3. Package Surface Overview (6-Surface Model)", self.styles["SectionHeading"]))
        surf_rows = [
            [
                Paragraph("Surface Face", self.styles["TableHead"]),
                Paragraph("Capture Status", self.styles["TableHead"]),
                Paragraph("Original SHA-256 Hash", self.styles["TableHead"]),
                Paragraph("Dimensions", self.styles["TableHead"]),
                Paragraph("File Size", self.styles["TableHead"]),
            ]
        ]

        all_faces = ["FRONT_PDP", "BACK", "LEFT", "RIGHT", "TOP", "BOTTOM"]
        surfaces_by_type = {s.surface_type.value if hasattr(s.surface_type, "value") else str(s.surface_type): s for s in surfaces}

        for face in all_faces:
            surf = surfaces_by_type.get(face)
            if surf:
                dims = f"{surf.image_width}x{surf.image_height} px" if surf.image_width else "Unknown"
                sz = f"{(surf.file_size_bytes or 0)/1024:.1f} KB"
                surf_rows.append([
                    Paragraph(sanitize_text(face), self.styles["TableCellBold"]),
                    Paragraph("<font color='#22543D'>CAPTURED</font>", self.styles["TableCellBold"]),
                    Paragraph(sanitize_text(surf.sha256_hash[:24] + "..."), self.styles["TableCellCode"]),
                    Paragraph(sanitize_text(dims), self.styles["TableCell"]),
                    Paragraph(sanitize_text(sz), self.styles["TableCell"]),
                ])
            else:
                surf_rows.append([
                    Paragraph(sanitize_text(face), self.styles["TableCell"]),
                    Paragraph("<font color='#718096'>Not captured</font>", self.styles["TableCell"]),
                    Paragraph("-", self.styles["TableCell"]),
                    Paragraph("-", self.styles["TableCell"]),
                    Paragraph("-", self.styles["TableCell"]),
                ])

        t_surf = Table(surf_rows, colWidths=[90, 84, 180, 85, 65])
        t_surf.setStyle(self._standard_table_style(has_header=True))
        story.append(t_surf)
        story.append(Spacer(1, 14))

        # =========================================================================
        # SECTION 5: Original Image Evidence
        # =========================================================================
        if opts.include_images and surfaces:
            story.append(Paragraph("4. Original Image Evidence", self.styles["SectionHeading"]))
            image_elements = []

            for s in surfaces:
                img_flowable = await self._load_scaled_image(s)
                face_name = s.surface_type.value if hasattr(s.surface_type, "value") else str(s.surface_type)
                img_caption = (
                    f"<b>Surface:</b> {face_name} | <b>SHA-256:</b> {s.sha256_hash}<br/>"
                    f"<b>Image ID:</b> {s.id} | <b>Dimensions:</b> {s.image_width or 0}x{s.image_height or 0} px"
                )
                cap_paragraph = Paragraph(img_caption, self.styles["TableCellCode"])

                block_table = Table([[img_flowable], [cap_paragraph]], colWidths=[page_width])
                block_table.setStyle(TableStyle([
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("BACKGROUND", (0, 0), (-1, -1), LIGHT_BG),
                    ("BOX", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
                ]))
                image_elements.append(block_table)
                image_elements.append(Spacer(1, 8))

            story.append(KeepTogether(image_elements[:4]))  # Keep up to 2 surfaces together cleanly
            story.append(Spacer(1, 10))

        # =========================================================================
        # SECTION 6: OCR Evidence
        # =========================================================================
        story.append(Paragraph("5. Modular OCR Evidence & Perception Trace", self.styles["SectionHeading"]))
        ocr_run_rows = [
            [
                Paragraph("OCR Run ID", self.styles["TableHead"]),
                Paragraph("Provider / Variant", self.styles["TableHead"]),
                Paragraph("Status", self.styles["TableHead"]),
                Paragraph("Regions", self.styles["TableHead"]),
                Paragraph("Duration", self.styles["TableHead"]),
            ]
        ]
        all_regions = []
        for r in ocr_runs:
            dur = f"{r.total_duration_ms:.1f} ms" if r.total_duration_ms else "N/A"
            ocr_run_rows.append([
                Paragraph(sanitize_text(str(r.id)[:18] + "..."), self.styles["TableCellCode"]),
                Paragraph(sanitize_text(f"{r.provider_name} ({r.preprocessing_variant})"), self.styles["TableCell"]),
                Paragraph(sanitize_text(r.status), self.styles["TableCellBold"]),
                Paragraph(str(r.total_regions_detected), self.styles["TableCell"]),
                Paragraph(dur, self.styles["TableCell"]),
            ])
            if hasattr(r, "regions") and r.regions:
                all_regions.extend(r.regions)

        t_ocr_runs = Table(ocr_run_rows, colWidths=[120, 164, 80, 60, 80])
        t_ocr_runs.setStyle(self._standard_table_style(has_header=True))
        story.append(t_ocr_runs)
        story.append(Spacer(1, 8))

        # Sample OCR tokens table
        if all_regions and opts.include_ocr_dump:
            story.append(Paragraph("OCR Tokens & Bounding Regions (Excerpt)", self.styles["SubSectionHeading"]))
            region_rows = [
                [
                    Paragraph("Raw OCR Detected Text", self.styles["TableHead"]),
                    Paragraph("Confidence", self.styles["TableHead"]),
                    Paragraph("Bounding Box (x, y, w, h)", self.styles["TableHead"]),
                    Paragraph("Source Region ID", self.styles["TableHead"]),
                ]
            ]
            for reg in all_regions[:opts.max_ocr_tokens]:
                bbox_str = str(reg.bounding_box) if reg.bounding_box else "{}"
                region_rows.append([
                    Paragraph(sanitize_text(reg.raw_text[:45]), self.styles["TableCellBold"]),
                    Paragraph(f"{reg.confidence:.2f}", self.styles["TableCell"]),
                    Paragraph(sanitize_text(bbox_str[:35]), self.styles["TableCellCode"]),
                    Paragraph(sanitize_text(str(reg.id)[:16] + "..."), self.styles["TableCellCode"]),
                ])

            t_reg = Table(region_rows, colWidths=[180, 64, 140, 120])
            t_reg.setStyle(self._standard_table_style(has_header=True))
            story.append(t_reg)
            story.append(Spacer(1, 14))

        # =========================================================================
        # SECTION 7: Extracted Declarations
        # =========================================================================
        story.append(Paragraph("6. Extracted Statutory Declarations (Observations)", self.styles["SectionHeading"]))
        obs_table_rows = [
            [
                Paragraph("Statutory Field", self.styles["TableHead"]),
                Paragraph("Raw OCR Text", self.styles["TableHead"]),
                Paragraph("Normalized Value", self.styles["TableHead"]),
                Paragraph("Conf.", self.styles["TableHead"]),
                Paragraph("Status", self.styles["TableHead"]),
            ]
        ]
        for obs in observations:
            ft_str = obs.field_type.value if hasattr(obs.field_type, "value") else str(obs.field_type)
            norm_str = str(obs.normalized_value) if obs.normalized_value else "-"
            if isinstance(obs.normalized_value, dict):
                norm_str = obs.normalized_value.get("formatted") or obs.normalized_value.get("display") or str(obs.normalized_value)

            stat_val = obs.status.value if hasattr(obs.status, "value") else str(obs.status)
            if hasattr(obs, "source") and obs.source == ObservationSource.OFFICER_INPUT:
                provenance_status = f"MANUAL ({stat_val})"
            elif getattr(obs, "revision", 1) > 1:
                provenance_status = f"CORRECTED (Rev {obs.revision})"
            else:
                provenance_status = f"ORIGINAL OCR ({stat_val})"

            obs_table_rows.append([
                Paragraph(sanitize_text(ft_str), self.styles["TableCellBold"]),
                Paragraph(sanitize_text(obs.raw_value[:50]), self.styles["TableCell"]),
                Paragraph(sanitize_text(str(norm_str)[:45]), self.styles["TableCellBold"]),
                Paragraph(f"{obs.confidence:.2f}", self.styles["TableCell"]),
                Paragraph(sanitize_text(provenance_status), self.styles["TableCell"]),
            ])

        t_obs = Table(obs_table_rows, colWidths=[110, 130, 124, 40, 100])
        t_obs.setStyle(self._standard_table_style(has_header=True))
        story.append(t_obs)
        story.append(Paragraph("<font size=7 color='#64748b'>Provenance Key: ORIGINAL OCR = Perception pipeline output | CORRECTED = Officer/Adjudicator verified revision | MANUAL = Officer declared observation</font>", self.styles["Normal"]))
        story.append(Spacer(1, 14))

        # =========================================================================
        # SECTION 8: PDP Geometry Measurements
        # =========================================================================
        story.append(Paragraph("7. Principal Display Panel (PDP) Geometry Measurements", self.styles["SectionHeading"]))
        geom_rows = [
            [
                Paragraph("Surface Face", self.styles["TableHead"]),
                Paragraph("PDP Status", self.styles["TableHead"]),
                Paragraph("Calibration", self.styles["TableHead"]),
                Paragraph("Pixel Area", self.styles["TableHead"]),
                Paragraph("Physical Area (sq cm)", self.styles["TableHead"]),
            ]
        ]
        for g in geometries:
            face_str = g.surface_type.value if hasattr(g.surface_type, "value") else str(g.surface_type)
            calib_str = "CALIBRATED" if g.has_calibration else "UNCALIBRATED"
            phys_area = f"{g.estimated_physical_area_sq_cm:.2f} sq cm" if (g.has_calibration and g.estimated_physical_area_sq_cm) else "Unavailable (No Calibration)"
            geom_rows.append([
                Paragraph(sanitize_text(face_str), self.styles["TableCellBold"]),
                Paragraph("PDP Candidate" if g.is_pdp_candidate else "Non-PDP", self.styles["TableCell"]),
                Paragraph(sanitize_text(calib_str), self.styles["TableCellBold"]),
                Paragraph(f"{g.pdp_pixel_area:.0f} px^2", self.styles["TableCell"]),
                Paragraph(sanitize_text(phys_area), self.styles["TableCell"]),
            ])

        if len(geom_rows) == 1:
            geom_rows.append([
                Paragraph("All Surfaces", self.styles["TableCell"]),
                Paragraph("No PDP geometry computed", self.styles["TableCell"]),
                Paragraph("UNCALIBRATED", self.styles["TableCell"]),
                Paragraph("-", self.styles["TableCell"]),
                Paragraph("Physical measurement unavailable - no valid calibration evidence.", self.styles["TableCell"]),
            ])

        t_geom = Table(geom_rows, colWidths=[90, 95, 95, 84, 140])
        t_geom.setStyle(self._standard_table_style(has_header=True))
        story.append(t_geom)
        story.append(Spacer(1, 14))

        # =========================================================================
        # SECTION 9: Legal Rule Evaluation Summary
        # =========================================================================
        story.append(Paragraph("8. Legal Rule Evaluation Summary (Deterministic Engine)", self.styles["SectionHeading"]))
        
        counts = {"PASS": 0, "FAIL": 0, "REVIEW": 0, "INDETERMINATE": 0, "NOT_APPLICABLE": 0}
        for ev in evaluations:
            oc = ev.outcome.value if hasattr(ev.outcome, "value") else str(ev.outcome)
            if oc in counts:
                counts[oc] += 1

        total_rules = len(evaluations)
        summary_cards = [
            [
                Paragraph("Total Evaluated", self.styles["TableHead"]),
                Paragraph("PASS", self.styles["BadgePass"]),
                Paragraph("FAIL", self.styles["BadgeFail"]),
                Paragraph("REVIEW", self.styles["BadgeReview"]),
                Paragraph("INDETERMINATE", self.styles["BadgeIndeterminate"]),
                Paragraph("NOT APPLICABLE", self.styles["BadgeNA"]),
            ],
            [
                Paragraph(str(total_rules), self.styles["CoverSubtitle"]),
                Paragraph(str(counts["PASS"]), self.styles["CoverSubtitle"]),
                Paragraph(str(counts["FAIL"]), self.styles["CoverSubtitle"]),
                Paragraph(str(counts["REVIEW"]), self.styles["CoverSubtitle"]),
                Paragraph(str(counts["INDETERMINATE"]), self.styles["CoverSubtitle"]),
                Paragraph(str(counts["NOT_APPLICABLE"]), self.styles["CoverSubtitle"]),
            ],
        ]
        t_summary = Table(summary_cards, colWidths=[84, 84, 84, 84, 84, 84])
        t_summary.setStyle(TableStyle([
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BACKGROUND", (0, 0), (0, -1), LIGHT_BG),
            ("BACKGROUND", (1, 0), (1, -1), PASS_BG),
            ("BACKGROUND", (2, 0), (2, -1), FAIL_BG),
            ("BACKGROUND", (3, 0), (3, -1), REVIEW_BG),
            ("BACKGROUND", (4, 0), (4, -1), INDETERMINATE_BG),
            ("BACKGROUND", (5, 0), (5, -1), NOT_APPLICABLE_BG),
            ("BOX", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(t_summary)
        story.append(Spacer(1, 14))

        # =========================================================================
        # SECTION 10: Detailed Rule Findings
        # =========================================================================
        story.append(Paragraph("9. Detailed Rule Findings & Statutory Explanations", self.styles["SectionHeading"]))
        
        for ev in evaluations:
            r_code = ev.rule_code or (ev.rule_definition.rule_code if ev.rule_definition else "RULE")
            r_title = ev.rule_definition.title if ev.rule_definition else r_code
            r_version = ev.rule_version or (ev.rule_definition.version if ev.rule_definition else "1.0")
            oc_str = ev.outcome.value if hasattr(ev.outcome, "value") else str(ev.outcome)

            badge_style, badge_bg, badge_border = self._get_badge_format(oc_str)

            rule_finding_data = [
                [
                    Paragraph(f"<b>{sanitize_text(r_code)}: {sanitize_text(r_title)}</b> (v{sanitize_text(r_version)})", self.styles["BodyBold"]),
                    self._create_badge_cell(oc_str, badge_style, badge_bg, badge_border),
                ],
                [
                    Paragraph(f"<b>Statutory Citation:</b> {sanitize_text(ev.statutory_citation)}", self.styles["TableCell"]),
                    Paragraph(f"<b>Evaluated:</b> {sanitize_text(ev.evaluated_at.strftime('%Y-%m-%d %H:%M UTC') if ev.evaluated_at else 'N/A')}", self.styles["TableCellCode"]),
                ],
                [
                    Paragraph(f"<b>Legal Rationale:</b> {sanitize_text(ev.legal_rationale)}", self.styles["TableCell"]),
                    Paragraph(f"<b>Evidence Refs:</b> {sanitize_text(str(len(ev.evidence_references.get('observation_ids', []))) + ' observation(s)')}", self.styles["TableCellCode"]),
                ],
            ]

            t_rule = Table(rule_finding_data, colWidths=[384, 120])
            t_rule.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BACKGROUND", (0, 0), (-1, -1), LIGHT_BG),
                ("BOX", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ]))
            story.append(t_rule)
            story.append(Spacer(1, 6))

        story.append(Spacer(1, 10))

        # =========================================================================
        # SECTION 11: Evidence Traceability
        # =========================================================================
        story.append(Paragraph("10. Backward Evidence Traceability Graph", self.styles["SectionHeading"]))
        trace_rows = [
            [
                Paragraph("Rule Evaluation", self.styles["TableHead"]),
                Paragraph("Observation ID", self.styles["TableHead"]),
                Paragraph("OCR Region ID", self.styles["TableHead"]),
                Paragraph("Surface Image SHA-256", self.styles["TableHead"]),
            ]
        ]
        
        obs_id_to_obs = {str(o.id): o for o in observations}
        surf_id_to_surf = {str(s.id): s for s in surfaces}

        for ev in evaluations:
            refs = ev.evidence_references or {}
            obs_ids = refs.get("observation_ids", [])
            r_code = ev.rule_code or (ev.rule_definition.rule_code if ev.rule_definition else "RULE")

            if obs_ids:
                for o_id in obs_ids:
                    obs_obj = obs_id_to_obs.get(str(o_id))
                    reg_id_str = str(obs_obj.ocr_region_id)[:14] + "..." if obs_obj and obs_obj.ocr_region_id else "N/A"
                    surf_obj = surf_id_to_surf.get(str(obs_obj.surface_id)) if obs_obj and obs_obj.surface_id else None
                    hash_str = surf_obj.sha256_hash[:18] + "..." if surf_obj else "Direct/Unlinked"

                    trace_rows.append([
                        Paragraph(sanitize_text(r_code), self.styles["TableCellBold"]),
                        Paragraph(sanitize_text(str(o_id)[:14] + "..."), self.styles["TableCellCode"]),
                        Paragraph(sanitize_text(reg_id_str), self.styles["TableCellCode"]),
                        Paragraph(sanitize_text(hash_str), self.styles["TableCellCode"]),
                    ])
            else:
                trace_rows.append([
                    Paragraph(sanitize_text(r_code), self.styles["TableCellBold"]),
                    Paragraph("<i>No observation linked</i>", self.styles["TableCell"]),
                    Paragraph("-", self.styles["TableCell"]),
                    Paragraph("-", self.styles["TableCell"]),
                ])

        t_trace = Table(trace_rows, colWidths=[120, 120, 120, 144])
        t_trace.setStyle(self._standard_table_style(has_header=True))
        story.append(t_trace)
        story.append(Spacer(1, 14))

        # =========================================================================
        # SECTION 12: Uncertainty / Review Items
        # =========================================================================
        story.append(Paragraph("11. Uncertainty, Conflicts & Review Items", self.styles["SectionHeading"]))
        review_items = [ev for ev in evaluations if ev.outcome in ("REVIEW", "INDETERMINATE")]

        if review_items:
            rev_rows = [
                [
                    Paragraph("Rule Code", self.styles["TableHead"]),
                    Paragraph("Outcome", self.styles["TableHead"]),
                    Paragraph("Reason for Review / Indeterminate State", self.styles["TableHead"]),
                ]
            ]
            for rev_ev in review_items:
                rc = rev_ev.rule_code or (rev_ev.rule_definition.rule_code if rev_ev.rule_definition else "RULE")
                oc = rev_ev.outcome.value if hasattr(rev_ev.outcome, "value") else str(rev_ev.outcome)
                rev_rows.append([
                    Paragraph(sanitize_text(rc), self.styles["TableCellBold"]),
                    Paragraph(sanitize_text(oc), self.styles["TableCellBold"]),
                    Paragraph(sanitize_text(rev_ev.legal_rationale), self.styles["TableCell"]),
                ])
            t_rev = Table(rev_rows, colWidths=[120, 94, 290])
            t_rev.setStyle(self._standard_table_style(has_header=True))
            story.append(t_rev)
        else:
            story.append(Paragraph("<i>No ambiguous, conflicting, or indeterminate findings recorded. All evaluated rules produced definitive outcomes.</i>", self.styles["Body"]))
        story.append(Spacer(1, 14))

        # =========================================================================
        # SECTION 13: Audit Information
        # =========================================================================
        story.append(Paragraph("12. Chain of Custody & Audit Information", self.styles["SectionHeading"]))
        audit_rows = [
            [
                Paragraph("Timestamp (UTC)", self.styles["TableHead"]),
                Paragraph("Action", self.styles["TableHead"]),
                Paragraph("Entity Type", self.styles["TableHead"]),
                Paragraph("Justification / Notes", self.styles["TableHead"]),
            ]
        ]
        for a in audit_logs[:10]:
            ts = a.performed_at.strftime("%Y-%m-%d %H:%M") if a.performed_at else "N/A"
            audit_rows.append([
                Paragraph(sanitize_text(ts), self.styles["TableCellCode"]),
                Paragraph(sanitize_text(a.action), self.styles["TableCellBold"]),
                Paragraph(sanitize_text(a.entity_type), self.styles["TableCell"]),
                Paragraph(sanitize_text(a.justification[:60]), self.styles["TableCell"]),
            ])

        if len(audit_rows) == 1:
            audit_rows.append([
                Paragraph(now_iso[:16], self.styles["TableCellCode"]),
                Paragraph("DOSSIER_GENERATED", self.styles["TableCellBold"]),
                Paragraph("InspectionReport", self.styles["TableCell"]),
                Paragraph("Automated tamper-evident dossier generation", self.styles["TableCell"]),
            ])

        t_audit = Table(audit_rows, colWidths=[110, 130, 110, 154])
        t_audit.setStyle(self._standard_table_style(has_header=True))
        story.append(t_audit)
        story.append(Spacer(1, 14))

        # =========================================================================
        # SECTION 14: Integrity Manifest / Hash Summary
        # =========================================================================
        story.append(Paragraph("13. Cryptographic Integrity Manifest (SHA-256)", self.styles["SectionHeading"]))
        manifest_rows = [
            [
                Paragraph("Artifact Category", self.styles["TableHead"]),
                Paragraph("Artifact Identifier", self.styles["TableHead"]),
                Paragraph("SHA-256 Digest (Hex)", self.styles["TableHead"]),
            ]
        ]
        # Manifest hash
        manifest_rows.append([
            Paragraph("EVIDENCE MANIFEST", self.styles["TableCellBold"]),
            Paragraph(sanitize_text(str(snapshot.id)[:18] + "..."), self.styles["TableCellCode"]),
            Paragraph(sanitize_text(snapshot.integrity_hash), self.styles["TableCellCode"]),
        ])
        # Original images
        for s in surfaces:
            fn = s.surface_type.value if hasattr(s.surface_type, "value") else str(s.surface_type)
            manifest_rows.append([
                Paragraph(f"IMAGE: {fn}", self.styles["TableCellBold"]),
                Paragraph(sanitize_text(str(s.id)[:18] + "..."), self.styles["TableCellCode"]),
                Paragraph(sanitize_text(s.sha256_hash), self.styles["TableCellCode"]),
            ])

        t_man = Table(manifest_rows, colWidths=[130, 130, 244])
        t_man.setStyle(self._standard_table_style(has_header=True))
        story.append(t_man)
        story.append(Spacer(1, 14))

        # =========================================================================
        # SECTION 15: Dossier Generation Metadata
        # =========================================================================
        story.append(Paragraph("14. Dossier Generation Metadata", self.styles["SectionHeading"]))
        meta_summary_rows = [
            [
                Paragraph("Dossier ID", self.styles["TableHead"]),
                Paragraph(sanitize_text(d_id), self.styles["TableCellCode"]),
            ],
            [
                Paragraph("Snapshot ID", self.styles["TableHead"]),
                Paragraph(sanitize_text(str(snapshot.id)), self.styles["TableCellCode"]),
            ],
            [
                Paragraph("Application Version", self.styles["TableHead"]),
                Paragraph(sanitize_text(opts.application_version), self.styles["TableCell"]),
            ],
            [
                Paragraph("Report Generator Version", self.styles["TableHead"]),
                Paragraph(sanitize_text(opts.generator_version), self.styles["TableCell"]),
            ],
            [
                Paragraph("Cryptographic Algorithm", self.styles["TableHead"]),
                Paragraph("SHA-256 (FIPS PUB 180-4 Standard)", self.styles["TableCellBold"]),
            ],
        ]
        t_gen_meta = Table(meta_summary_rows, colWidths=[150, 354])
        t_gen_meta.setStyle(self._standard_table_style(has_header=False))
        story.append(t_gen_meta)

        # Build PDF with dynamic NumberedCanvas
        def make_canvas(*args, **kwargs):
            return NumberedCanvas(
                *args,
                dossier_id=d_id,
                inspection_number=inspection.inspection_number,
                **kwargs
            )

        doc.build(story, canvasmaker=make_canvas)

        pdf_bytes = buffer.getvalue()
        pdf_hash = calculate_sha256(pdf_bytes)

        return DossierGenerationResult(
            pdf_bytes=pdf_bytes,
            sha256_hash=pdf_hash,
            file_size_bytes=len(pdf_bytes),
            generated_at=now_iso,
            dossier_id=d_id,
            snapshot_id=str(snapshot.id),
            inspection_id=str(inspection.id),
            report_version=report_version,
        )

    def _get_badge_format(self, outcome: str):
        """Return paragraph style, background color, and border color for outcome badges."""
        outcome = outcome.upper()
        if outcome in ("PASS", "COMPLIANT"):
            return self.styles["BadgePass"], PASS_BG, PASS_BORDER
        elif outcome in ("FAIL", "NON_COMPLIANT"):
            return self.styles["BadgeFail"], FAIL_BG, FAIL_BORDER
        elif outcome in ("REVIEW", "IN_REVIEW", "REVIEW_REQUIRED"):
            return self.styles["BadgeReview"], REVIEW_BG, REVIEW_BORDER
        elif outcome in ("NOT_APPLICABLE",):
            return self.styles["BadgeNA"], NOT_APPLICABLE_BG, NOT_APPLICABLE_BORDER
        else:
            return self.styles["BadgeIndeterminate"], INDETERMINATE_BG, INDETERMINATE_BORDER

    def _create_badge_cell(self, text: str, style, bg_color, border_color) -> Table:
        """Create a rounded pill/badge cell using a 1-cell Table."""
        t = Table([[Paragraph(f"<b>{sanitize_text(text)}</b>", style)]], colWidths=[100])
        t.setStyle(TableStyle([
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BACKGROUND", (0, 0), (-1, -1), bg_color),
            ("BOX", (0, 0), (-1, -1), 1, border_color),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ]))
        return t

    def _standard_table_style(self, has_header: bool = True) -> TableStyle:
        """Return standardized clean grid styling for dossier tables."""
        cmds = [
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("BOX", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
            ("ROWBACKGROUNDS", (0, 1 if has_header else 0), (-1, -1), [white, ALT_ROW_BG]),
        ]
        if has_header:
            cmds.append(("BACKGROUND", (0, 0), (-1, 0), LIGHT_BG))
            cmds.append(("LINEBELOW", (0, 0), (-1, 0), 1, NAVY))
        return TableStyle(cmds)

    async def _load_scaled_image(self, surface: InspectionSurface):
        """Safely retrieve image bytes from storage and produce a scaled ReportLab Image flowable."""
        if not self.storage_service or not surface.image_storage_path:
            return Paragraph(f"[Image not stored: {surface.surface_type}]", self.styles["TableCell"])

        try:
            img_bytes = await self.storage_service.retrieve(surface.image_storage_path)
            pil_img = PILImage.open(io.BytesIO(img_bytes))
            orig_w, orig_h = pil_img.size

            # Scale to fit max box of 240 x 180 pt while maintaining aspect ratio
            max_w, max_h = 240, 180
            aspect = orig_w / float(orig_h) if orig_h > 0 else 1.0

            if aspect >= (max_w / max_h):
                scaled_w = max_w
                scaled_h = max_w / aspect
            else:
                scaled_h = max_h
                scaled_w = max_h * aspect

            return RLImage(io.BytesIO(img_bytes), width=scaled_w, height=scaled_h)
        except Exception as e:
            return Paragraph(f"[Image unavailable: {sanitize_text(str(e))}]", self.styles["TableCell"])
