#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from app.services.offline_feedback_metrics import build_offline_feedback_metrics


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compute offline feedback outcome metrics from a synthetic JSON fixture."
    )
    parser.add_argument("fixture", type=Path, help="JSON file with actions and optional outcomes arrays")
    args = parser.parse_args()

    payload = _load_fixture(args.fixture)
    metrics = build_offline_feedback_metrics(
        actions=payload.get("actions", []),
        outcomes=payload.get("outcomes", []),
    )
    print(json.dumps(metrics, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def _load_fixture(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError("fixture must be a JSON object")
    return payload


if __name__ == "__main__":
    raise SystemExit(main())
