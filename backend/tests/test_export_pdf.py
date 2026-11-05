"""
Unit and API tests for /api/v1/export/pdf endpoint.
"""

import pytest


def test_export_pdf_valid_markdown(client):
    """Test generating PDF binary from Markdown containing tables and headers."""
    markdown = """
    # Quarterly Report

    This is an introductory paragraph explaining the results.

    | Metric | Target | Actual |
    |---|---|---|
    | Conversion | 85% | 92% |
    | Latency | <200ms | 110ms |

    ```python
    def calculate():
        return 42
    ```
    """
    payload = {
        "markdown": markdown,
        "title": "Quarterly Performance Report",
        "page_size": "A4",
        "orientation": "portrait",
    }
    response = client.post("/api/v1/export/pdf", json=payload)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert "attachment" in response.headers["content-disposition"]
    assert "Quarterly_Performance_Report.pdf" in response.headers["content-disposition"]

    # Verify standard PDF file signature
    pdf_bytes = response.content
    assert pdf_bytes.startswith(b"%PDF-")
    assert len(pdf_bytes) > 500


def test_export_pdf_empty_markdown_rejected(client):
    """Verify HTTP 400 Bad Request when markdown is empty."""
    payload = {"markdown": ""}
    response = client.post("/api/v1/export/pdf", json=payload)
    assert response.status_code == 400

    data = response.json()
    assert data["code"] == "EMPTY_MARKDOWN_PAYLOAD"


def test_export_pdf_landscape_orientation(client):
    """Verify export in landscape orientation works cleanly."""
    payload = {
        "markdown": "## Landscape Document\n\nWide layout test.",
        "title": "Landscape Document",
        "orientation": "landscape",
        "page_size": "Letter",
    }
    response = client.post("/api/v1/export/pdf", json=payload)
    assert response.status_code == 200
    assert response.content.startswith(b"%PDF-")
