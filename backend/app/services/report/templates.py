from reportlab.lib.colors import HexColor, white, black
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.pdfgen import canvas
import html

# Palette Tokens
NAVY = HexColor("#1A365D")
SLATE = HexColor("#2B6CB0")
TEAL = HexColor("#319795")
LIGHT_BG = HexColor("#F7FAFC")
ALT_ROW_BG = HexColor("#F8FAFC")
BORDER_COLOR = HexColor("#E2E8F0")
DARK_TEXT = HexColor("#2D3748")
MUTED_TEXT = HexColor("#718096")

# Status Badges
PASS_BG = HexColor("#C6F6D5")
PASS_TEXT = HexColor("#22543D")
PASS_BORDER = HexColor("#9AE6B4")

FAIL_BG = HexColor("#FED7D7")
FAIL_TEXT = HexColor("#742A2A")
FAIL_BORDER = HexColor("#FEB2B2")

REVIEW_BG = HexColor("#FEEBC8")
REVIEW_TEXT = HexColor("#744210")
REVIEW_BORDER = HexColor("#FBD38D")

INDETERMINATE_BG = HexColor("#EDF2F7")
INDETERMINATE_TEXT = HexColor("#4A5568")
INDETERMINATE_BORDER = HexColor("#CBD5E0")

NOT_APPLICABLE_BG = HexColor("#E2E8F0")
NOT_APPLICABLE_TEXT = HexColor("#4A5568")
NOT_APPLICABLE_BORDER = HexColor("#CBD5E0")

def sanitize_text(text: any) -> str:
    """Sanitize arbitrary strings for safe insertion into ReportLab Paragraphs."""
    if text is None:
        return ""
    s = str(text)
    return html.escape(s)

class NumberedCanvas(canvas.Canvas):
    """
    Two-pass canvas to dynamically compute and draw exact total page count
    along with running header and running footer on pages after the cover page.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []
        self.dossier_id = kwargs.get("dossier_id", "DOSSIER")
        self.inspection_number = kwargs.get("inspection_number", "")

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_decorations(self, page_count: int):
        # Skip header and footer on Page 1 (Cover page)
        if self._pageNumber == 1:
            return

        self.saveState()
        self.setFont("Helvetica", 7.5)
        self.setFillColor(HexColor("#718096"))

        # Header (Top of Page)
        top_y = 800
        header_text = "METRIXA - Legal Metrology Inspection Dossier (PCMR 2011)"
        if self.inspection_number:
            header_text += f" | {self.inspection_number}"
        self.drawString(54, top_y, header_text)
        
        right_text = f"Dossier: {self.dossier_id[:8]}"
        self.drawRightString(558, top_y, right_text)

        # Header Rule
        self.setStrokeColor(HexColor("#E2E8F0"))
        self.setLineWidth(0.5)
        self.line(54, top_y - 4, 558, top_y - 4)

        # Footer (Bottom of Page)
        bot_y = 36
        self.line(54, bot_y + 12, 558, bot_y + 12)
        footer_notice = "CONFIDENTIAL INSPECTION DOSSIER - NOT AN OFFICIAL GOVERNMENT CERTIFICATE"
        self.drawString(54, bot_y, footer_notice)
        
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(558, bot_y, page_str)

        self.restoreState()


def get_dossier_styles():
    """Build and return unified paragraph styles for the dossier."""
    base = getSampleStyleSheet()

    styles = {
        "Normal": base["Normal"],
        "CoverTitle": ParagraphStyle(
            "CoverTitle",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=24,
            leading=28,
            textColor=NAVY,
            alignment=TA_LEFT,
            spaceAfter=6,
        ),
        "CoverSubtitle": ParagraphStyle(
            "CoverSubtitle",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=16,
            textColor=SLATE,
            alignment=TA_LEFT,
            spaceAfter=15,
        ),
        "SectionHeading": ParagraphStyle(
            "SectionHeading",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=15,
            textColor=NAVY,
            spaceBefore=14,
            spaceAfter=6,
            keepWithNext=True,
        ),
        "SubSectionHeading": ParagraphStyle(
            "SubSectionHeading",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=13,
            textColor=SLATE,
            spaceBefore=8,
            spaceAfter=4,
            keepWithNext=True,
        ),
        "Body": ParagraphStyle(
            "Body",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=11,
            textColor=DARK_TEXT,
        ),
        "BodyBold": ParagraphStyle(
            "BodyBold",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8.5,
            leading=11,
            textColor=DARK_TEXT,
        ),
        "TableHead": ParagraphStyle(
            "TableHead",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=NAVY,
        ),
        "TableCell": ParagraphStyle(
            "TableCell",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=7.5,
            leading=9.5,
            textColor=DARK_TEXT,
        ),
        "TableCellBold": ParagraphStyle(
            "TableCellBold",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=7.5,
            leading=9.5,
            textColor=DARK_TEXT,
        ),
        "TableCellCode": ParagraphStyle(
            "TableCellCode",
            parent=base["Normal"],
            fontName="Courier",
            fontSize=6.5,
            leading=8,
            textColor=DARK_TEXT,
        ),
        "Disclaimer": ParagraphStyle(
            "Disclaimer",
            parent=base["Normal"],
            fontName="Helvetica-Oblique",
            fontSize=8,
            leading=11,
            textColor=MUTED_TEXT,
            alignment=TA_JUSTIFY,
        ),
        "BadgePass": ParagraphStyle(
            "BadgePass",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=PASS_TEXT,
            alignment=TA_CENTER,
        ),
        "BadgeFail": ParagraphStyle(
            "BadgeFail",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=FAIL_TEXT,
            alignment=TA_CENTER,
        ),
        "BadgeReview": ParagraphStyle(
            "BadgeReview",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=REVIEW_TEXT,
            alignment=TA_CENTER,
        ),
        "BadgeIndeterminate": ParagraphStyle(
            "BadgeIndeterminate",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=INDETERMINATE_TEXT,
            alignment=TA_CENTER,
        ),
        "BadgeNA": ParagraphStyle(
            "BadgeNA",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=NOT_APPLICABLE_TEXT,
            alignment=TA_CENTER,
        ),
    }

    return styles
