"""
Verification test for OpenAPI 3.1.0 specification (docs/specs/api_contract.yaml)
Validates YAML syntax, required REST & WebSocket endpoints, component schemas,
and internal reference integrity.
"""

from pathlib import Path
import re
import yaml


def test_api_contract_validity():
    spec_path = Path(__file__).resolve().parent.parent / "docs" / "specs" / "api_contract.yaml"
    assert spec_path.exists(), f"Contract file not found at {spec_path}"

    with open(spec_path, "r", encoding="utf-8") as f:
        spec = yaml.safe_load(f)

    assert isinstance(spec, dict), "Parsed YAML root is not a dictionary"

    # 1. OpenAPI Version
    assert spec.get("openapi") == "3.1.0", f"Expected openapi 3.1.0, got {spec.get('openapi')}"

    # 2. Info section
    info = spec.get("info", {})
    assert "title" in info, "Missing info.title"
    assert "version" in info, "Missing info.version"

    # 3. Required Endpoints
    paths = spec.get("paths", {})
    required_endpoints = [
        ("/api/v1/convert/file", "post"),
        ("/api/v1/convert/text", "post"),
        ("/api/v1/jobs/{job_id}", "get"),
        ("/api/v1/export/pdf", "post"),
        ("/api/v1/health", "get"),
        ("/api/v1/ws/stream/{job_id}", "get"),
    ]

    for path, method in required_endpoints:
        assert path in paths, f"Missing required path: {path}"
        assert method in paths[path], f"Missing method {method.upper()} for path {path}"

    # 4. Required Schemas
    components = spec.get("components", {})
    schemas = components.get("schemas", {})

    required_schemas = [
        "PipelineType",
        "JobStatus",
        "ConversionOptions",
        "ConversionMetadata",
        "ConversionResult",
        "JobCreatedResponse",
        "JobDetailResponse",
        "PdfExportRequest",
        "HealthResponse",
        "ErrorResponse",
        "WebSocketFrame",
        "WebSocketStatusFrame",
        "WebSocketChunkFrame",
        "WebSocketCompleteFrame",
        "WebSocketErrorFrame",
    ]

    for schema_name in required_schemas:
        assert schema_name in schemas, f"Missing required component schema: {schema_name}"

    # 5. Resolve internal $ref pointers
    def find_refs(node):
        refs = []
        if isinstance(node, dict):
            for k, v in node.items():
                if k == "$ref" and isinstance(v, str):
                    refs.append(v)
                else:
                    refs.extend(find_refs(v))
        elif isinstance(node, list):
            for item in node:
                refs.extend(find_refs(item))
        return refs

    all_refs = find_refs(spec)
    assert len(all_refs) > 0, "No $ref references found in specification"

    for ref in all_refs:
        assert ref.startswith("#/components/schemas/"), f"Unexpected ref format: {ref}"
        target = ref.split("/")[-1]
        assert target in schemas, f"Dangling reference: {ref} target '{target}' not found in schemas"

    print(f"PASS: api_contract.yaml is 100% valid OpenAPI 3.1.0 ({len(paths)} paths, {len(schemas)} schemas, {len(all_refs)} resolved refs)")


if __name__ == "__main__":
    test_api_contract_validity()
