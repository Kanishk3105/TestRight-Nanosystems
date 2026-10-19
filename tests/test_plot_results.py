"""Section 3 tests for summary validation and chart generation."""

from __future__ import annotations

import json
import io
import tempfile
import unittest
import warnings
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from matplotlib.image import imread

from plot_results import ChartInputError, create_chart, load_summary, main


class PlotResultsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        self.json_path = self.root / "summary.json"
        self.output_path = self.root / "charts" / "temperatures.png"

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def write_summary(self, devices: object) -> None:
        self.json_path.write_text(json.dumps({"devices": devices}), encoding="utf-8")

    def test_valid_json_creates_nonempty_chart_at_requested_path(self) -> None:
        self.write_summary([
            {"device_id": "A", "average_temperature": 22.5},
            {"device_id": "A-device-with-long-name", "average_temperature": 80},
        ])
        result = create_chart(self.json_path, self.output_path)
        self.assertEqual(result, self.output_path)
        self.assertTrue(result.is_file())
        self.assertGreater(result.stat().st_size, 0)

    def test_long_device_ids_fit_without_tight_layout_warning(self) -> None:
        devices = [
            {
                "device_id": (
                    f"DEV_{index:02d}_"
                    + "north-facility-sensor-array-temperature-channel-" * 3
                    + f"ZONE_{index:02d}"
                ),
                "average_temperature": 20.0 + index * 5.0,
            }
            for index in range(1, 9)
        ]
        self.write_summary(devices)

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            result = create_chart(self.json_path, self.output_path)

        self.assertFalse(
            any("Tight layout not applied" in str(item.message) for item in caught),
            [str(item.message) for item in caught],
        )
        image = imread(result)
        self.assertGreater(image.shape[1], image.shape[0])
        self.assertGreater(result.stat().st_size, 0)

    def test_empty_devices_are_rejected_without_claiming_success(self) -> None:
        self.write_summary([])
        with self.assertRaisesRegex(ChartInputError, "no devices"):
            create_chart(self.json_path, self.output_path)
        self.assertFalse(self.output_path.exists())

    def test_missing_json_is_reported(self) -> None:
        with self.assertRaisesRegex(ChartInputError, "not found"):
            load_summary(self.root / "missing.json")

    def test_malformed_json_is_reported(self) -> None:
        self.json_path.write_text("{not json", encoding="utf-8")
        with self.assertRaisesRegex(ChartInputError, "valid JSON"):
            load_summary(self.json_path)

    def test_missing_device_fields_are_reported(self) -> None:
        self.write_summary([{"device_id": "A"}])
        with self.assertRaisesRegex(ChartInputError, "average_temperature"):
            load_summary(self.json_path)

    def test_invalid_temperature_values_are_reported(self) -> None:
        for value in ("hot", float("nan"), float("inf"), True, 10**1000):
            with self.subTest(value=value):
                self.write_summary([{"device_id": "A", "average_temperature": value}])
                with self.assertRaises(ChartInputError):
                    load_summary(self.json_path)

    def test_invalid_summary_does_not_create_chart(self) -> None:
        self.write_summary([{"device_id": "A", "average_temperature": "invalid"}])
        with self.assertRaises(ChartInputError):
            create_chart(self.json_path, self.output_path)
        self.assertFalse(self.output_path.exists())

    def test_cli_failure_does_not_claim_chart_was_written(self) -> None:
        self.write_summary([])
        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            exit_code = main(["--input", str(self.json_path), "--output", str(self.output_path)])
        self.assertEqual(exit_code, 1)
        self.assertIn("Error:", stderr.getvalue())
        self.assertNotIn("Temperature chart written", stdout.getvalue())
        self.assertFalse(self.output_path.exists())

    def test_missing_devices_list_is_reported(self) -> None:
        self.json_path.write_text('{"metadata": {}}', encoding="utf-8")
        with self.assertRaisesRegex(ChartInputError, "devices"):
            load_summary(self.json_path)


if __name__ == "__main__":
    unittest.main()
