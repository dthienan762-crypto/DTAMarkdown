"""
DTAMarkdown Studio - Milestone 1 Adversarial Challenge Test Suite
Empirical validation of:
1. docs/specs/api_contract.yaml
   - OpenAPI 3.1.0 schema validity
   - Exhaustive $ref resolution and schema dependency graph
   - Multipart file upload specifications (FastAPI / OpenAPI 3.1 standard: type: string, format: binary)
   - WebSocket frame schema simulation, serialization, and deserialization testing
2. Edge cases and architectural gaps:
   - Missing 413 Payload Too Large / file size constraints
   - Empty file handling (0-byte payload response codes)
   - WebSocket disconnection, close codes, and reconnection policies
   - Server crash tempfile cleanup & startup sweeping in core_principles.md
"""

from datetime import datetime
from pathlib import Path
import re
import uuid
import pytest
import yaml

SPEC_FILE = Path(__file__).resolve().parent.parent / "docs" / "specs" / "api_contract.yaml"
PRINCIPLES_FILE = Path(__file__).resolve().parent.parent / "docs" / "specs" / "core_principles.md"
PRODUCT_UX_FILE = Path(__file__).resolve().parent.parent / "docs" / "specs" / "product_ux.md"


@pytest.fixture(scope="module")
def api_spec():
    assert SPEC_FILE.exists(), f"Spec file missing: {SPEC_FILE}"
    with open(SPEC_FILE, "r", encoding="utf-8") as f:
        spec = yaml.safe_load(f)
    assert isinstance(spec, dict), "Parsed YAML root is not a dict"
    return spec


@pytest.fixture(scope="module")
def core_principles_text():
    assert PRINCIPLES_FILE.exists(), f"Core principles file missing: {PRINCIPLES_FILE}"
    return PRINCIPLES_FILE.read_text(encoding="utf-8")


# ----------------------------------------------------------------------
# 1. OpenAPI 3.1.0 Deep Reference & Structural Verification
# ----------------------------------------------------------------------

def test_openapi_root_and_metadata(api_spec):
    assert api_spec.get("openapi") == "3.1.0", f"Unexpected openapi version: {api_spec.get('openapi')}"
    assert "info" in api_spec and "title" in api_spec["info"] and "version" in api_spec["info"]
    assert "paths" in api_spec and len(api_spec["paths"]) >= 6
    assert "components" in api_spec and "schemas" in api_spec["components"]


def test_all_refs_resolve_strictly(api_spec):
    """Ensure every $ref in the entire specification resolves to an existing schema."""
    schemas = api_spec["components"]["schemas"]
    resolved_count = 0

    def check_node(node, path=""):
        nonlocal resolved_count
        if isinstance(node, dict):
            for k, v in node.items():
                curr_path = f"{path}.{k}"
                if k == "$ref":
                    assert isinstance(v, str), f"Non-string $ref at {curr_path}: {v}"
                    prefix = "#/components/schemas/"
                    assert v.startswith(prefix), f"Invalid $ref format at {curr_path}: {v}"
                    target_name = v[len(prefix):]
                    assert target_name in schemas, f"Dangling $ref at {curr_path}: '{target_name}' not in schemas"
                    resolved_count += 1
                else:
                    check_node(v, curr_path)
        elif isinstance(node, list):
            for idx, item in enumerate(node):
                check_node(item, f"{path}[{idx}]")

    check_node(api_spec)
    assert resolved_count >= 10, f"Expected at least 10 $ref references, found {resolved_count}"


def test_multipart_file_upload_spec(api_spec):
    """
    Validate that multipart file upload specifications match standard
    FastAPI / OpenAPI 3.1.0 specifications (type: string, format: binary).
    """
    convert_file = api_spec["paths"].get("/api/v1/convert/file")
    assert convert_file is not None, "Missing /api/v1/convert/file path"
    post_op = convert_file.get("post")
    assert post_op is not None, "Missing POST method on /api/v1/convert/file"

    req_body = post_op.get("requestBody")
    assert req_body is not None, "Missing requestBody for file upload"
    assert req_body.get("required") is True, "requestBody should be required"

    content = req_body.get("content", {})
    assert "multipart/form-data" in content, "Missing multipart/form-data content type"

    schema = content["multipart/form-data"].get("schema", {})
    assert schema.get("type") == "object", "multipart/form-data schema must be object"
    assert "file" in schema.get("required", []), "Property 'file' must be required in multipart upload"

    properties = schema.get("properties", {})
    assert "file" in properties, "Property 'file' missing in properties"
    file_prop = properties["file"]
    assert file_prop.get("type") == "string", f"Expected file type string, got {file_prop.get('type')}"
    assert file_prop.get("format") == "binary", f"Expected file format binary, got {file_prop.get('format')}"

    # Also verify options_json and pipeline_type
    assert "pipeline_type" in properties
    assert properties["pipeline_type"].get("$ref") == "#/components/schemas/PipelineType"


# ----------------------------------------------------------------------
# 2. WebSocket Payloads Simulation & Schema Deserialization Testing
# ----------------------------------------------------------------------

def validate_against_schema(data: dict, schema: dict, all_schemas: dict):
    """Lightweight pure-python OpenAPI 3.1 JSON schema validator."""
    # Handle $ref
    if "$ref" in schema:
        ref_name = schema["$ref"].split("/")[-1]
        schema = all_schemas[ref_name]

    # Required fields
    required_fields = schema.get("required", [])
    for field in required_fields:
        assert field in data, f"Missing required field '{field}' for schema"

    # Properties check
    properties = schema.get("properties", {})
    for k, v in data.items():
        if k not in properties:
            continue
        prop_spec = properties[k]
        if "$ref" in prop_spec:
            ref_name = prop_spec["$ref"].split("/")[-1]
            prop_spec = all_schemas[ref_name]

        expected_type = prop_spec.get("type")
        if expected_type == "string":
            assert isinstance(v, str), f"Field '{k}' expected string, got {type(v)}"
            # Format validation
            fmt = prop_spec.get("format")
            if fmt == "uuid":
                uuid.UUID(v)  # Will raise ValueError if invalid
            elif fmt == "date-time":
                # Validate ISO 8601
                assert v.endswith("Z") or "+" in v or "-" in v
                datetime.fromisoformat(v.replace("Z", "+00:00"))
            # Enum validation
            if "enum" in prop_spec:
                assert v in prop_spec["enum"], f"Field '{k}' value '{v}' not in allowed enum {prop_spec['enum']}"

        elif expected_type == "integer":
            assert isinstance(v, int) and not isinstance(v, bool), f"Field '{k}' expected int, got {type(v)}"
            if "minimum" in prop_spec:
                assert v >= prop_spec["minimum"], f"Field '{k}' ({v}) < minimum ({prop_spec['minimum']})"
            if "maximum" in prop_spec:
                assert v <= prop_spec["maximum"], f"Field '{k}' ({v}) > maximum ({prop_spec['maximum']})"

        elif expected_type == "number":
            assert isinstance(v, (int, float)) and not isinstance(v, bool), f"Field '{k}' expected number, got {type(v)}"
            if "minimum" in prop_spec:
                assert v >= prop_spec["minimum"], f"Field '{k}' ({v}) < minimum ({prop_spec['minimum']})"
            if "maximum" in prop_spec:
                assert v <= prop_spec["maximum"], f"Field '{k}' ({v}) > maximum ({prop_spec['maximum']})"

        elif expected_type == "boolean":
            assert isinstance(v, bool), f"Field '{k}' expected bool, got {type(v)}"

        elif expected_type == "object":
            if prop_spec.get("nullable") and v is None:
                continue
            assert isinstance(v, dict), f"Field '{k}' expected object, got {type(v)}"
            validate_against_schema(v, prop_spec, all_schemas)

        elif expected_type == "array":
            assert isinstance(v, list), f"Field '{k}' expected list, got {type(v)}"
            items_spec = prop_spec.get("items", {})
            for item in v:
                if items_spec.get("type") == "string":
                    assert isinstance(item, str)


def test_websocket_status_frame_simulation(api_spec):
    schemas = api_spec["components"]["schemas"]
    status_schema = schemas["WebSocketStatusFrame"]

    # Valid status frame
    valid_payload = {
        "event": "status",
        "job_id": str(uuid.uuid4()),
        "stage": "ocr_layout_analysis",
        "progress": 45,
        "message": "Extracting tables and KaTeX formulas...",
        "timestamp": "2026-11-04T16:15:00Z"
    }
    validate_against_schema(valid_payload, status_schema, schemas)

    # Adversarial: invalid event name
    with pytest.raises(AssertionError):
        bad = dict(valid_payload, event="unknown_event")
        validate_against_schema(bad, status_schema, schemas)

    # Adversarial: out-of-range progress (> 100)
    with pytest.raises(AssertionError):
        bad = dict(valid_payload, progress=150)
        validate_against_schema(bad, status_schema, schemas)

    # Adversarial: invalid uuid
    with pytest.raises(ValueError):
        bad = dict(valid_payload, job_id="not-a-valid-uuid")
        validate_against_schema(bad, status_schema, schemas)

    # Adversarial: missing required field 'stage'
    with pytest.raises(AssertionError):
        bad = dict(valid_payload)
        del bad["stage"]
        validate_against_schema(bad, status_schema, schemas)


def test_websocket_chunk_frame_simulation(api_spec):
    schemas = api_spec["components"]["schemas"]
    chunk_schema = schemas["WebSocketChunkFrame"]

    valid_payload = {
        "event": "chunk",
        "job_id": str(uuid.uuid4()),
        "delta": "| Col 1 | Col 2 |\n|---|---|\n| Val 1 | Val 2 |\n",
        "index": 4,
        "timestamp": "2026-11-04T16:15:01Z"
    }
    validate_against_schema(valid_payload, chunk_schema, schemas)

    # Adversarial: index < 0
    with pytest.raises(AssertionError):
        bad = dict(valid_payload, index=-1)
        validate_against_schema(bad, chunk_schema, schemas)

    # Adversarial: delta not string
    with pytest.raises(AssertionError):
        bad = dict(valid_payload, delta=12345)
        validate_against_schema(bad, chunk_schema, schemas)


def test_websocket_complete_frame_simulation(api_spec):
    schemas = api_spec["components"]["schemas"]
    complete_schema = schemas["WebSocketCompleteFrame"]

    valid_payload = {
        "event": "complete",
        "job_id": str(uuid.uuid4()),
        "markdown": "# Heading\n\nPreserved table content\n$$\nx^2 + y^2 = r^2\n$$",
        "metadata": {
            "word_count": 120,
            "character_count": 890,
            "estimated_read_time": "1 min",
            "duration_ms": 1420.5,
            "engine_used": "PyMuPDF Fast-Path",
            "tags": ["Technical Document", "Formulas"],
            "warnings": [],
            "toc": "- [Heading](#heading)"
        },
        "timestamp": "2026-11-04T16:15:05Z"
    }
    validate_against_schema(valid_payload, complete_schema, schemas)

    # Adversarial: missing metadata
    with pytest.raises(AssertionError):
        bad = dict(valid_payload)
        del bad["metadata"]
        validate_against_schema(bad, complete_schema, schemas)


def test_websocket_error_frame_simulation(api_spec):
    schemas = api_spec["components"]["schemas"]
    error_schema = schemas["WebSocketErrorFrame"]

    valid_payload = {
        "event": "error",
        "job_id": str(uuid.uuid4()),
        "code": "DEGRADED_IMAGE_CONTRAST",
        "message": "Image contrast too low for optical character recognition.",
        "recoverable": False,
        "timestamp": "2026-11-04T16:15:02Z"
    }
    validate_against_schema(valid_payload, error_schema, schemas)

    # Adversarial: recoverable not bool
    with pytest.raises(AssertionError):
        bad = dict(valid_payload, recoverable="false")
        validate_against_schema(bad, error_schema, schemas)


# ----------------------------------------------------------------------
# 3. Adversarial Edge Case Discovery & Gaps Evaluation
# ----------------------------------------------------------------------

def test_challenge_payload_size_limit_and_413_response(api_spec):
    """
    Challenge: Does /api/v1/convert/file specify 413 Payload Too Large
    or an explicit file size boundary limit?
    """
    convert_file_responses = api_spec["paths"]["/api/v1/convert/file"]["post"]["responses"]
    has_413 = "413" in convert_file_responses
    print(f"\n[CHALLENGE OBSERVATION] 413 Payload Too Large defined in /api/v1/convert/file: {has_413}")
    assert has_413 is True, "413 Payload Too Large response must be defined in /api/v1/convert/file"


def test_challenge_empty_file_specification(api_spec):
    """
    Challenge: Does the contract specify how empty (0-byte) files are handled?
    """
    convert_file = api_spec["paths"]["/api/v1/convert/file"]["post"]
    description = convert_file.get("description", "")
    responses = convert_file.get("responses", {})
    has_empty_file_spec = "empty" in description.lower() or any(
        "empty" in str(r).lower() for r in responses.values()
    )
    print(f"[CHALLENGE OBSERVATION] Empty file behavior explicitly documented in /api/v1/convert/file: {has_empty_file_spec}")
    assert has_empty_file_spec is True, "Empty 0-byte file handling must be documented in /api/v1/convert/file"


def test_challenge_websocket_disconnect_and_close_codes(api_spec):
    """
    Challenge: Does WebSocket spec (/api/v1/ws/stream/{job_id}) document standard
    WebSocket close codes (e.g. 1000, 1006, 1008, 1011, 4004, 4499)?
    """
    ws_endpoint = api_spec["paths"]["/api/v1/ws/stream/{job_id}"]["get"]
    desc = ws_endpoint.get("description", "")
    has_close_codes = any(code in desc for code in ["1000", "1006", "1008", "1011", "4499", "close code"])
    print(f"[CHALLENGE OBSERVATION] WebSocket close codes explicitly documented: {has_close_codes}")
    assert has_close_codes is True, "Standard WebSocket close codes must be documented in /api/v1/ws/stream/{job_id}"


def test_challenge_websocket_disconnect_detached_execution(core_principles_text):
    """
    Challenge: Does core_principles.md specify that if a WebSocket disconnects,
    background job execution continues detached for at least 60 seconds?
    """
    has_detached_60s = "60 second" in core_principles_text.lower() or "60-second" in core_principles_text.lower()
    print(f"[CHALLENGE OBSERVATION] 60-second detached background execution documented: {has_detached_60s}")
    assert has_detached_60s is True, "Section 2.3 must specify at least 60s detached execution on WebSocket disconnect"


def test_challenge_crash_tempfile_recovery_policy(core_principles_text):
    """
    Challenge: Does core_principles.md specify synchronous startup sweeping
    or crash recovery cleanup when the server boots up after a hard crash?
    """
    has_startup_sweep = any(term in core_principles_text.lower() for term in [
        "startup sweep", "server startup", "boot cleanup", "on startup", "lifespan", "crash recovery"
    ])
    print(f"[CHALLENGE OBSERVATION] Startup sweeping / crash recovery explicitly defined in core_principles.md: {has_startup_sweep}")
    assert has_startup_sweep is True, "Section 3.4 Startup Staging Sweep must be documented in core_principles.md"


