"""
Unit and API tests for /api/v1/convert/text endpoint.
"""

import pytest


def test_convert_text_valid_content(client):
    """Test text conversion with basic headings and paragraphs."""
    payload = {
        "raw_text": "<h1>Executive Summary</h1><p>This is a test paragraph with <strong>bold</strong> text.</p>",
        "pipeline_type": "text_normalize",
        "options": {
            "extract_tables": True,
            "extract_math": True,
            "generate_toc": False,
        },
    }
    response = client.post("/api/v1/convert/text", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert data["pipeline"] == "text_normalize"
    assert "# Executive Summary" in data["markdown"]
    assert "**bold**" in data["markdown"]
    assert "metadata" in data
    assert data["metadata"]["word_count"] > 0


def test_convert_text_html_table(client):
    """Test HTML table conversion into standard GFM table format."""
    html = """
    <table>
        <tr><th>Metric</th><th>Q1</th><th>Q2</th></tr>
        <tr><td>Revenue</td><td>$1.2M</td><td>$1.5M</td></tr>
    </table>
    """
    payload = {
        "raw_text": html,
        "pipeline_type": "text_normalize",
    }
    response = client.post("/api/v1/convert/text", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    markdown = data["markdown"]
    assert "| Metric | Q1 | Q2 |" in markdown
    assert "|---|---|---|" in markdown
    assert "| Revenue | $1.2M | $1.5M |" in markdown


def test_convert_text_toc_generation(client):
    """Test automatic Table of Contents generation when requested."""
    text = (
        "<h1>Overview</h1><p>Some text</p>"
        "<h2>Architecture</h2><p>Arch details</p>"
        "<h2>Security</h2><p>Security details</p>"
    )
    payload = {
        "raw_text": text,
        "options": {
            "generate_toc": True,
        },
    }
    response = client.post("/api/v1/convert/text", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert "Table of Contents" in data["markdown"]
    assert "[Overview](#overview)" in data["markdown"]
    assert "[Architecture](#architecture)" in data["markdown"]


def test_convert_text_empty_payload(client):
    """Verify HTTP 400 Bad Request on empty raw text."""
    payload = {"raw_text": ""}
    response = client.post("/api/v1/convert/text", json=payload)
    assert response.status_code == 400
    data = response.json()
    assert data["code"] == "EMPTY_TEXT_PAYLOAD"


def test_convert_text_whitespace_only_payload(client):
    """Verify HTTP 400 Bad Request on whitespace-only text."""
    payload = {"raw_text": "   \n\t  "}
    response = client.post("/api/v1/convert/text", json=payload)
    assert response.status_code == 400
    data = response.json()
    assert data["code"] == "EMPTY_TEXT_PAYLOAD"
