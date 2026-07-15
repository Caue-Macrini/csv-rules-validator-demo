from __future__ import annotations

import csv
import io
import json
import re
from decimal import Decimal, InvalidOperation
from typing import Any

from flask import Flask, jsonify, request


app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def validate_value(value: str, rule: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    normalized = value.strip()

    if rule.get("required") and not normalized:
        return ["required value is missing"]
    if not normalized:
        return errors

    kind = rule.get("type", "text")
    if kind == "integer":
        try:
            int(normalized)
        except ValueError:
            errors.append("must be an integer")
    elif kind == "decimal":
        try:
            Decimal(normalized)
        except InvalidOperation:
            errors.append("must be a decimal number")
    elif kind == "email" and not EMAIL_PATTERN.fullmatch(normalized):
        errors.append("must be a valid email")

    allowed = rule.get("allowed")
    if allowed and normalized not in allowed:
        errors.append(f"must be one of: {', '.join(map(str, allowed))}")

    max_length = rule.get("max_length")
    if max_length and len(normalized) > int(max_length):
        errors.append(f"must contain at most {max_length} characters")
    return errors


def validate_csv(csv_text: str, rules: dict[str, Any]) -> dict[str, Any]:
    reader = csv.DictReader(io.StringIO(csv_text))
    if reader.fieldnames is None:
        raise ValueError("CSV header is missing")

    configured_fields = rules.get("fields", {})
    missing_headers = [name for name in configured_fields if name not in reader.fieldnames]
    issues: list[dict[str, Any]] = []

    for name in missing_headers:
        issues.append({"row": 1, "field": name, "message": "configured column is missing"})

    row_count = 0
    for row_number, row in enumerate(reader, start=2):
        row_count += 1
        for field, rule in configured_fields.items():
            for message in validate_value(row.get(field, ""), rule):
                issues.append({"row": row_number, "field": field, "message": message})

    return {
        "valid": not issues,
        "rows_processed": row_count,
        "issue_count": len(issues),
        "issues": issues,
    }


@app.get("/health")
def health():
    return jsonify({"status": "ok"})


@app.post("/api/validate")
def validate_upload():
    csv_file = request.files.get("csv")
    rules_file = request.files.get("rules")
    if csv_file is None or rules_file is None:
        return jsonify({"error": "send 'csv' and 'rules' files"}), 400

    try:
        csv_text = csv_file.read().decode("utf-8-sig")
        rules = json.loads(rules_file.read().decode("utf-8"))
        return jsonify(validate_csv(csv_text, rules))
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        return jsonify({"error": str(exc)}), 400


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
