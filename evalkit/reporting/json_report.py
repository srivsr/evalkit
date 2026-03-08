"""JSON report output — structured for programmatic consumption."""
import json
from datetime import datetime, timezone


def generate_json_report(evaluation: dict) -> str:
    report = {
        "report_format": "evalkit_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "evaluation": evaluation,
        "summary": {
            "verdict": evaluation.get("summary", {}).get("verdict"),
            "root_cause": evaluation.get("root_cause", {}).get("code"),
            "severity": evaluation.get("root_cause", {}).get("severity"),
            "anomaly_count": len(evaluation.get("anomalies", [])),
            "fix_count": len(evaluation.get("fix_suggestions", [])),
        },
    }
    return json.dumps(report, indent=2)
