#!/usr/bin/env python3
"""Render readiness reports from synthetic aggregate feedback metrics JSON."""
from __future__ import annotations

import argparse
from pathlib import Path

from app.services.action_feedback_readiness import main as readiness_main


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Convert aggregate offline feedback metrics JSON into a readiness report."
    )
    parser.add_argument("--metrics-json", required=True, type=Path, help="Aggregate metrics JSON input")
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    parser.add_argument("--output", type=Path, default=None, help="Optional report output path")
    args = parser.parse_args(argv)

    readiness_args = [
        "--metrics-json",
        str(args.metrics_json),
        "--format",
        args.format,
    ]
    if args.output is not None:
        readiness_args.extend(["--output", str(args.output)])
    return readiness_main(readiness_args)


if __name__ == "__main__":
    raise SystemExit(main())
