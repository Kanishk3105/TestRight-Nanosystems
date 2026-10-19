"""Create a readable temperature comparison chart from a summary JSON file."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from textwrap import fill
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


class ChartInputError(Exception):
    """Raised when a summary cannot produce a trustworthy chart."""


def load_summary(json_path: str | Path) -> list[tuple[str, float]]:
    path = Path(json_path)
    try:
        with path.open("r", encoding="utf-8") as input_file:
            summary: Any = json.load(input_file)
    except FileNotFoundError as exc:
        raise ChartInputError(f"Summary JSON not found: {path}") from exc
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ChartInputError(f"Could not read valid JSON from '{path}': {exc}") from exc

    if not isinstance(summary, dict):
        raise ChartInputError("Summary JSON must contain a JSON object.")
    devices = summary.get("devices")
    if not isinstance(devices, list):
        raise ChartInputError("Summary JSON must contain a 'devices' list.")
    if not devices:
        raise ChartInputError("Summary contains no devices to chart.")

    chart_data: list[tuple[str, float]] = []
    for index, device in enumerate(devices):
        if not isinstance(device, dict):
            raise ChartInputError(f"Device entry {index + 1} must be a JSON object.")
        device_id = device.get("device_id")
        temperature = device.get("average_temperature")
        if not isinstance(device_id, str) or not device_id.strip():
            raise ChartInputError(f"Device entry {index + 1} has a missing or invalid device_id.")
        if isinstance(temperature, bool) or not isinstance(temperature, (int, float)):
            raise ChartInputError(
                f"Device '{device_id}' has a missing or non-numeric average_temperature."
            )
        try:
            numeric_temperature = float(temperature)
        except OverflowError as exc:
            raise ChartInputError(
                f"Device '{device_id}' has an out-of-range average_temperature."
            ) from exc
        if not math.isfinite(numeric_temperature):
            raise ChartInputError(f"Device '{device_id}' has a non-finite average_temperature.")
        chart_data.append((device_id.strip(), numeric_temperature))
    return chart_data


def create_chart(json_path: str | Path, output_path: str | Path) -> Path:
    """Validate a summary and save a non-empty PNG chart."""
    chart_data = load_summary(json_path)
    destination = Path(output_path)
    labels, temperatures = zip(*chart_data)
    wrapped_labels = [fill(label, width=18, break_long_words=True) for label in labels]
    figure_width = max(8.0, min(24.0, 5.0 + len(labels) * 0.65))
    label_lines = max(label.count("\n") + 1 for label in wrapped_labels)
    figure_height = max(6.0, 5.0 + label_lines * 0.22)
    figure, axis = plt.subplots(figsize=(figure_width, figure_height))
    try:
        positions = range(len(labels))
        axis.bar(positions, temperatures, color="#4472C4")
        axis.set_xticks(list(positions), wrapped_labels)
        axis.set_xlabel("Device ID")
        axis.set_ylabel("Average Temperature (°C)")
        axis.set_title("Average Temperature by Device", pad=16)
        axis.grid(axis="y", linestyle="--", alpha=0.35)
        axis.set_axisbelow(True)
        axis.tick_params(axis="x", labelrotation=0, labelsize=8)
        figure.tight_layout()
        destination.parent.mkdir(parents=True, exist_ok=True)
        figure.savefig(destination, dpi=150, bbox_inches="tight")
    except OSError as exc:
        raise ChartInputError(f"Could not write chart to '{destination}': {exc}") from exc
    finally:
        plt.close(figure)

    try:
        if not destination.is_file() or destination.stat().st_size == 0:
            raise ChartInputError(f"Chart output was not created or is empty: {destination}")
    except OSError as exc:
        raise ChartInputError(f"Could not verify chart output '{destination}': {exc}") from exc
    return destination


def build_parser() -> argparse.ArgumentParser:
    project_directory = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description="Chart average device temperatures from a JSON summary.")
    parser.add_argument(
        "--input",
        type=Path,
        default=project_directory / "summary.json",
        help="summary JSON path (default: summary.json beside plot_results.py)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=project_directory / "temperature_chart.png",
        help="chart PNG path (default: temperature_chart.png beside plot_results.py)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    try:
        image_path = create_chart(arguments.input, arguments.output)
    except ChartInputError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    print(f"Temperature chart written to: {image_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
