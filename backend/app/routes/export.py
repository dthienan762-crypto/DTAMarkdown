"""
DTAMarkdown Studio - Export REST Endpoints.
Endpoint: /api/v1/export/pdf
Conforms to docs/specs/api_contract.yaml.
"""

from __future__ import annotations

import logging
from fastapi import APIRouter, HTTPException, Response, status

from backend.app.schemas import PdfExportRequest
from backend.app.services.pdf_exporter import PdfExportService
from backend.app.services.temp_manager import sanitize_filename

logger = logging.getLogger("dtamarkdown.routes.export")

router = APIRouter(prefix="/api/v1/export", tags=["export"])


@router.post(
    "/pdf",
    summary="Compile Markdown to PDF binary",
    response_class=Response,
    responses={
        200: {
            "content": {"application/pdf": {}},
            "description": "Rendered PDF document.",
        },
        400: {"description": "Empty Markdown payload or bad request."},
        500: {"description": "PDF compilation failure."},
    },
)
async def export_pdf(payload: PdfExportRequest):
    """
    Accepts Markdown text with optional KaTeX and table markup, compiles it into
    a print-ready PDF binary, and returns it with Content-Disposition attachment headers.
    """
    if not payload.markdown or not payload.markdown.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "EMPTY_MARKDOWN_PAYLOAD", "message": "Markdown content cannot be empty."},
        )

    title = payload.title or "Document"
    page_size = payload.page_size or "A4"
    orientation = payload.orientation or "portrait"
    include_styles = payload.include_styles if payload.include_styles is not None else True

    try:
        pdf_bytes = PdfExportService.compile_markdown_to_pdf(
            markdown=payload.markdown,
            title=title,
            page_size=page_size,
            orientation=orientation,
            include_styles=include_styles,
        )
    except Exception as e:
        logger.error("Failed to compile Markdown to PDF: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "PDF_COMPILATION_ERROR", "message": f"PDF compilation failed: {str(e)}"},
        )

    import unicodedata
    import urllib.parse

    ascii_title = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode("ascii")
    safe_ascii = sanitize_filename(ascii_title).replace(".bin", "").strip() or "document"
    utf8_filename = urllib.parse.quote(f"{title}.pdf")

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{safe_ascii}.pdf"; filename*=UTF-8\'\'{utf8_filename}',
            "Content-Length": str(len(pdf_bytes)),
        },
    )
