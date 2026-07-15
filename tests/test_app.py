import json
from io import BytesIO

from app import app, validate_csv


RULES = {
    "fields": {
        "id": {"required": True, "type": "integer"},
        "email": {"required": True, "type": "email"},
        "status": {"required": True, "allowed": ["active", "inactive"]},
    }
}


def test_valid_document():
    result = validate_csv("id,email,status\n1,a@example.com,active\n", RULES)
    assert result["valid"] is True
    assert result["rows_processed"] == 1


def test_reports_row_and_field_errors():
    result = validate_csv("id,email,status\nx,invalid,pending\n", RULES)
    assert result["valid"] is False
    assert result["issue_count"] == 3
    assert {issue["field"] for issue in result["issues"]} == {"id", "email", "status"}


def test_upload_endpoint():
    client = app.test_client()
    response = client.post(
        "/api/validate",
        data={
            "csv": (BytesIO(b"id,email,status\n1,a@example.com,active\n"), "sample.csv"),
            "rules": (BytesIO(json.dumps(RULES).encode()), "rules.json"),
        },
        content_type="multipart/form-data",
    )
    assert response.status_code == 200
    assert response.get_json()["valid"] is True
