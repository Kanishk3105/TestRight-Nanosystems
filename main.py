"""Summarize device telemetry CSV data into a JSON report."""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sys
import tempfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TextIO

REQUIRED_COLUMNS = ("device_id", "status", "temperature")
MAX_AVERAGE_TEMPERATURE = 80.0


class ProcessingError(Exception):
    """Raised when input data cannot be processed into a trustworthy report."""


def _read_and_aggregate(input_path: Path) -> dict[str, Any]:
    if not input_path.is_file():
        raise ProcessingError(f"Input CSV not found: {input_path}")

    totals: dict[str, dict[str, float | int]] = defaultdict(
        lambda: {"total_records": 0, "temperature_sum": 0.0, "error_count": 0}
    )
    total_input_rows = 0
    rejected_rows = 0

    try:
        with input_path.open("r", encoding="utf-8-sig", newline="") as csv_file:
            reader = csv.DictReader(csv_file, strict=True)
            if reader.fieldnames is None:
                raise ProcessingError("Input CSV is empty and has no header row.")

            reader.fieldnames = [name.strip() if name is not None else "" for name in reader.fieldnames]
            if len(reader.fieldnames) != len(set(reader.fieldnames)):
                raise ProcessingError("Input CSV contains duplicate column names.")

            missing_columns = [name for name in REQUIRED_COLUMNS if name not in reader.fieldnames]
            if missing_columns:
                raise ProcessingError(
                    "Input CSV is missing required column(s): " + ", ".join(missing_columns)
                )

            for row in reader:
                total_input_rows += 1
                if None in row or any(row.get(column) is None for column in REQUIRED_COLUMNS):
                    rejected_rows += 1
                    continue

                device_id = row["device_id"].strip()
                status = row["status"].strip()
                raw_temperature = row["temperature"].strip()
                if not device_id or not status or not raw_temperature:
                    rejected_rows += 1
                    continue

                try:
                    temperature = float(raw_temperature)
                except ValueError:
                    rejected_rows += 1
                    continue
                if not math.isfinite(temperature):
                    rejected_rows += 1
                    continue

                device = totals[device_id]
                device["total_records"] += 1
                device["temperature_sum"] += temperature
                if status.casefold() == "error":
                    device["error_count"] += 1
    except (OSError, UnicodeError, csv.Error) as exc:
        raise ProcessingError(f"Could not read CSV file '{input_path}': {exc}") from exc

    devices = []
    excluded_devices = 0
    valid_rows = sum(int(values["total_records"]) for values in totals.values())
    for device_id in sorted(totals):
        values = totals[device_id]
        count = int(values["total_records"])
        average = float(values["temperature_sum"]) / count
        if average > MAX_AVERAGE_TEMPERATURE:
            excluded_devices += 1
            continue
        devices.append(
            {
                "device_id": device_id,
                "total_records": count,
                "average_temperature": average,
                "error_count": int(values["error_count"]),
            }
        )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_file": str(input_path),
        "filter": {
            "max_average_temperature": MAX_AVERAGE_TEMPERATURE,
            "comparison": "less_than_or_equal",
        },
        "devices": devices,
        "metadata": {
            "total_input_rows": total_input_rows,
            "valid_rows": valid_rows,
            "rejected_rows": rejected_rows,
            "excluded_devices": excluded_devices,
        },
    }


def _write_json(summary: dict[str, Any], output_path: Path) -> None:
    temporary_path: Path | None = None
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=output_path.parent,
            prefix=f".{output_path.name}.",
            suffix=".tmp",
            delete=False,
        ) as output_file:
            temporary_path = Path(output_file.name)
            json.dump(summary, output_file, ensure_ascii=False, indent=2, allow_nan=False)
            output_file.write("\n")
            output_file.flush()
            os.fsync(output_file.fileno())
        os.replace(temporary_path, output_path)
    except (OSError, TypeError, ValueError):
        if temporary_path is not None:
            try:
                temporary_path.unlink()
            except FileNotFoundError:
                pass
        raise


def process_csv(input_path: str | Path, output_path: str | Path) -> dict[str, Any]:
    """Process a CSV, write a JSON summary, and return the report."""
    source = Path(input_path)
    destination = Path(output_path)
    summary = _read_and_aggregate(source)
    _write_json(summary, destination)
    return summary


def print_summary(summary: dict[str, Any], stream: TextIO = sys.stdout) -> None:
    devices = summary["devices"]
    metadata = summary["metadata"]

    if metadata["total_input_rows"] == 0:
        print("No input records found (the CSV contains a header only).", file=stream)
    elif not devices and metadata["valid_rows"] == 0:
        print("No devices have valid temperature measurements.", file=stream)
    elif not devices:
        print("No devices met the average-temperature threshold.", file=stream)
    else:
        headers = ("Device ID", "Total Records", "Average Temperature (C)", "ERROR Count")
        rows = [
            (
                device["device_id"],
                str(device["total_records"]),
                f'{device["average_temperature"]:.2f}',
                str(device["error_count"]),
            )
            for device in devices
        ]
        widths = [
            max(len(headers[index]), *(len(row[index]) for row in rows))
            for index in range(len(headers))
        ]
        print("  ".join(value.ljust(widths[index]) for index, value in enumerate(headers)), file=stream)
        print("  ".join("-" * width for width in widths), file=stream)
        for row in rows:
            print("  ".join(value.ljust(widths[index]) for index, value in enumerate(row)), file=stream)

    print(
        "Rows: "
        f'{metadata["total_input_rows"]} input, '
        f'{metadata["valid_rows"]} valid, '
        f'{metadata["rejected_rows"]} rejected; '
        f'{metadata["excluded_devices"]} device(s) excluded.',
        file=stream,
    )


def build_parser() -> argparse.ArgumentParser:
    project_directory = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description="Summarize device telemetry from a CSV file.")
    parser.add_argument(
        "--input",
        type=Path,
        default=project_directory / "device_telemetry.csv",
        help="input CSV path (default: device_telemetry.csv beside main.py)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=project_directory / "summary.json",
        help="output JSON path (default: summary.json beside main.py)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    try:
        summary = process_csv(arguments.input, arguments.output)
    except (ProcessingError, OSError, TypeError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print_summary(summary)
    print(f"Summary written to: {arguments.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
