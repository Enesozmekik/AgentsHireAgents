from __future__ import annotations

import json
import random
import time
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class MockWorkResult:
    summary: str
    confidence: float
    output_json: dict


class MockWorkerLogic:
    """
    Simulates worker-agent labor for demo mode.
    - waits 2-3 seconds
    - returns structured JSON payload
    """

    def __init__(self, min_delay_sec: float = 2.0, max_delay_sec: float = 3.0) -> None:
        if min_delay_sec <= 0 or max_delay_sec <= 0 or min_delay_sec > max_delay_sec:
            raise ValueError("Invalid delay range")
        self.min_delay_sec = min_delay_sec
        self.max_delay_sec = max_delay_sec

    def run(self, prompt: str) -> MockWorkResult:
        if not prompt or not prompt.strip():
            raise ValueError("Prompt is required")

        time.sleep(random.uniform(self.min_delay_sec, self.max_delay_sec))

        normalized = " ".join(prompt.strip().split())
        summary = f"Task analyzed and completed for: {normalized[:120]}"
        confidence = 0.92
        output = {
            "task": normalized,
            "status": "completed",
            "result": {
                "headline": "Mock worker finished execution",
                "artifacts": ["analysis.txt", "result.json"],
                "notes": "Generated in demo mode by MockWorkerLogic",
            },
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        }
        return MockWorkResult(summary=summary, confidence=confidence, output_json=output)


def format_delivery_uri(payload: dict) -> str:
    """
    For demo-only usage: returns a pseudo URI that can be pushed to submitWork.
    """
    encoded = json.dumps(payload, separators=(",", ":"))
    return f"mock://delivery/{encoded}"


if __name__ == "__main__":
    worker = MockWorkerLogic()
    result = worker.run("Create a concise market summary for agent economy.")
    print("Is tamamlandi:")
    print(json.dumps(result.output_json, indent=2, ensure_ascii=False))
    print("Delivery URI:")
    print(format_delivery_uri(result.output_json))
