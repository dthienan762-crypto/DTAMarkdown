"""
DTAMarkdown Studio - PDF Exporter Service.
Compiles Markdown into formatted PDF binary using ReportLab with PyMuPDF fallback.
"""

from __future__ import annotations

import io
import logging
import re
from typing import Optional

logger = logging.getLogger("dtamarkdown.pdf_exporter")


class PdfExportService:
    """Service to render Markdown documents into high-fidelity PDF binaries."""

    @classmethod
    def compile_markdown_to_pdf(
        cls,
        markdown: str,
        title: str = "Document",
        page_size: str = "A4",
        orientation: str = "portrait",
        include_styles: bool = True,
    ) -> bytes:
        """
        Compile markdown text to a PDF binary buffer.
        """
        if not markdown or not markdown.strip():
            raise ValueError("Markdown content cannot be empty.")

        try:
            return cls._render_reportlab(markdown, title, page_size, orientation, include_styles)
        except Exception as e:
            logger.warning("ReportLab PDF generation encountered an issue (%s), attempting PyMuPDF fallback...", e)
            return cls._render_pymupdf(markdown, title)

    @classmethod
    def _render_reportlab(
        cls,
        markdown: str,
        title: str,
        page_size_name: str,
        orientation: str,
        include_styles: bool,
    ) -> bytes:
        """Render using ReportLab."""
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4, LETTER, LEGAL, landscape
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.platypus import (
            SimpleDocTemplate,
            Paragraph,
            Spacer,
            Table,
            TableStyle,
            Preformatted,
            HRFlowable,
        )

        buffer = io.BytesIO()

        # Select page size
        sizes = {"A4": A4, "LETTER": LETTER, "LEGAL": LEGAL}
        selected_size = sizes.get(page_size_name.upper(), A4)
        if orientation.lower() == "landscape":
            selected_size = landscape(selected_size)

        doc = SimpleDocTemplate(
            buffer,
            pagesize=selected_size,
            rightMargin=0.75 * inch,
            leftMargin=0.75 * inch,
            topMargin=0.75 * inch,
            bottomMargin=0.75 * inch,
            title=title,
        )

        import os
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont

        font_name = "Helvetica"
        arial_path = "C:/Windows/Fonts/arial.ttf"
        arial_bold_path = "C:/Windows/Fonts/arialbd.ttf"
        arial_italic_path = "C:/Windows/Fonts/ariali.ttf"
        arial_bi_path = "C:/Windows/Fonts/arialbi.ttf"

        if os.path.exists(arial_path):
            try:
                pdfmetrics.registerFont(TTFont("Arial", arial_path))
                pdfmetrics.registerFont(TTFont("Arial-Bold", arial_bold_path if os.path.exists(arial_bold_path) else arial_path))
                pdfmetrics.registerFont(TTFont("Arial-Italic", arial_italic_path if os.path.exists(arial_italic_path) else arial_path))
                pdfmetrics.registerFont(TTFont("Arial-BoldItalic", arial_bi_path if os.path.exists(arial_bi_path) else arial_path))
                pdfmetrics.registerFontFamily("Arial", normal="Arial", bold="Arial-Bold", italic="Arial-Italic", boldItalic="Arial-BoldItalic")
                font_name = "Arial"
            except Exception as fe:
                logger.warning("Could not register Arial font for PDF: %s", fe)

        styles = getSampleStyleSheet()
        normal_style = styles["Normal"]
        normal_style.fontName = font_name
        body_style = styles["BodyText"]
        body_style.fontName = font_name
        body_style.fontSize = 10
        body_style.leading = 14

        h1_font = "Arial-Bold" if font_name == "Arial" else "Helvetica-Bold"
        h1_style = styles["Heading1"]
        h1_style.fontName = h1_font
        h1_style.fontSize = 18
        h1_style.leading = 22

        h2_style = styles["Heading2"]
        h2_style.fontName = h1_font
        h2_style.fontSize = 14
        h2_style.leading = 18

        h3_style = styles["Heading3"]
        h3_style.fontName = h1_font
        h3_style.fontSize = 11
        h3_style.leading = 15

        code_style = styles["Code"]
        code_style.fontSize = 8.5
        code_style.leading = 11

        story = []

        # Add Title if present
        if title:
            story.append(Paragraph(cls._escape_xml(title), h1_style))
            story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#6366f1"), spaceBefore=6, spaceAfter=14))

        # Parse markdown lines/blocks
        lines = markdown.split("\n")
        in_code_block = False
        code_buffer = []
        table_buffer = []

        for line in lines:
            trimmed = line.strip()

            # Handle code blocks
            if trimmed.startswith("```"):
                if in_code_block:
                    # Closing code block
                    code_text = "\n".join(code_buffer)
                    story.append(Preformatted(code_text, code_style))
                    story.append(Spacer(1, 8))
                    code_buffer = []
                    in_code_block = False
                else:
                    in_code_block = True
                continue

            if in_code_block:
                code_buffer.append(line)
                continue

            # Handle Markdown tables
            if trimmed.startswith("|") and trimmed.endswith("|"):
                table_buffer.append(trimmed)
                continue
            else:
                if table_buffer:
                    t_flowable = cls._build_reportlab_table(table_buffer, body_style, font_name)
                    if t_flowable:
                        story.append(t_flowable)
                        story.append(Spacer(1, 10))
                    table_buffer = []

            # Handle Headings
            if trimmed.startswith("# "):
                heading_text = cls._escape_xml(trimmed[2:])
                story.append(Paragraph(heading_text, h1_style))
                story.append(Spacer(1, 8))
            elif trimmed.startswith("## "):
                heading_text = cls._escape_xml(trimmed[3:])
                story.append(Paragraph(heading_text, h2_style))
                story.append(Spacer(1, 6))
            elif trimmed.startswith("### "):
                heading_text = cls._escape_xml(trimmed[4:])
                story.append(Paragraph(heading_text, h3_style))
                story.append(Spacer(1, 4))
            elif trimmed.startswith(">"):
                # Callout / blockquote
                quote_text = cls._escape_xml(trimmed.lstrip("> "))
                quote_font = "Arial-Italic" if font_name == "Arial" else "Helvetica-Oblique"
                quote_style = ParagraphStyle(
                    'QuoteStyle',
                    parent=body_style,
                    textColor=colors.HexColor("#4b5563"),
                    leftIndent=14,
                    fontName=quote_font,
                )
                story.append(Paragraph(quote_text, quote_style))
                story.append(Spacer(1, 4))
            elif trimmed == "" or trimmed == "---":
                if trimmed == "---":
                    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#d1d5db"), spaceBefore=6, spaceAfter=8))
                else:
                    story.append(Spacer(1, 6))
            else:
                # Regular paragraph
                para_html = cls._format_inline_markdown(trimmed)
                story.append(Paragraph(para_html, body_style))
                story.append(Spacer(1, 4))

        # Flush any remaining table
        if table_buffer:
            t_flowable = cls._build_reportlab_table(table_buffer, body_style, font_name)
            if t_flowable:
                story.append(t_flowable)

        # Flush any unclosed code block
        if code_buffer:
            code_text = "\n".join(code_buffer)
            story.append(Preformatted(code_text, code_style))

        doc.build(story)
        return buffer.getvalue()

    @classmethod
    def _build_reportlab_table(cls, table_lines: list[str], style, font_name: str = "Helvetica"):
        """Parse GFM table lines into a ReportLab Table."""
        from reportlab.lib import colors
        from reportlab.platypus import Table, TableStyle, Paragraph

        header_font = "Arial-Bold" if font_name == "Arial" else "Helvetica-Bold"

        data = []
        for line in table_lines:
            cells = [c.strip() for c in line.split("|")[1:-1]]
            # Skip delimiter separator row (e.g. |---|---|)
            if all(re.match(r"^:?-+:?$", c) for c in cells if c):
                continue
            row_flowables = [Paragraph(cls._escape_xml(c), style) for c in cells]
            if row_flowables:
                data.append(row_flowables)

        if not data:
            return None

        t = Table(data, hAlign='LEFT')
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor("#0f172a")),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), header_font),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ]))
        return t

    @classmethod
    def _escape_xml(cls, text: str) -> str:
        """Escape XML entities for ReportLab Paragraphs."""
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )

    @classmethod
    def _format_inline_markdown(cls, text: str) -> str:
        """Convert basic inline Markdown (*italic*, **bold**, `code`) into ReportLab XML."""
        t = cls._escape_xml(text)
        # Bold: **bold** or __bold__
        t = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', t)
        t = re.sub(r'__(.+?)__', r'<b>\1</b>', t)
        # Italic: *italic* or _italic_
        t = re.sub(r'\*(.+?)\*', r'<i>\1</i>', t)
        t = re.sub(r'_(.+?)_', r'<i>\1</i>', t)
        # Inline code: `code`
        t = re.sub(r'`(.+?)`', r'<font face="Courier">\1</font>', t)
        return t

    @classmethod
    def _render_pymupdf(cls, markdown: str, title: str) -> bytes:
        """Fallback PDF rendering via PyMuPDF."""
        import pymupdf
        doc = pymupdf.open()
        page = doc.new_page()

        y = 72
        # Title
        page.insert_text((50, y), title, fontsize=18, color=(0.1, 0.2, 0.6))
        y += 30

        # Lines
        for line in markdown.splitlines():
            if y > 750:
                page = doc.new_page()
                y = 50
            if line.strip():
                page.insert_text((50, y), line[:100], fontsize=10)
                y += 14
            else:
                y += 8

        pdf_bytes = doc.tobytes()
        doc.close()
        return pdf_bytes
