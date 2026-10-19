"""Section 2 tests for CSV processing and JSON output."""

from __future__ import annotations

import json
import io
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from main import ProcessingError, main, process_csv


class ProcessCsvTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        self.input_path = self.root / "input.csv"
        self.output_path = self.root / "nested" / "summary.json"

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def write_csv(self, content: str) -> None:
        self.input_path.write_text(content, encoding="utf-8")

    def process(self) -> dict:
        return process_csv(self.input_path, self.output_path)

    def test_multiple_devices_error_matching_filter_and_counts(self) -> None:
        self.write_csv(
            "device_id,status,temperature\n"
            "DEV_B,error,60\n"
            "DEV_A, ERROR ,40\n"
            "DEV_B,Error,80\n"
            "DEV_A,ok,50\n"
            "DEV_C,ok,90\n"
        )
        summary = self.process()

        self.assertEqual(
            [device["device_id"] for device in summary["devices"]],
            ["DEV_A", "DEV_B"],
        )
        self.assertEqual(summary["devices"][0]["total_records"], 2)
        self.assertEqual(summary["devices"][0]["average_temperature"], 45.0)
        self.assertEqual(summary["devices"][0]["error_count"], 1)
        self.assertEqual(summary["devices"][1]["average_temperature"], 70.0)
        self.assertEqual(summary["devices"][1]["error_count"], 2)
        self.assertEqual(summary["metadata"], {
            "total_input_rows": 5,
            "valid_rows": 5,
            "rejected_rows": 0,
            "excluded_devices": 1,
        })
        self.assertEqual(summary["filter"]["comparison"], "less_than_or_equal")
        self.assertTrue(self.output_path.is_file())
        self.assertEqual(json.loads(self.output_path.read_text(encoding="utf-8")), summary)

    def test_single_device_and_exact_threshold_are_retained(self) -> None:
        self.write_csv("device_id,status,temperature\nONE,ok,80\n")
        summary = self.process()
        self.assertEqual(len(summary["devices"]), 1)
        self.assertEqual(summary["devices"][0]["average_temperature"], 80.0)
        self.assertEqual(summary["devices"][0]["total_records"], 1)

    def test_mean_above_threshold_is_excluded(self) -> None:
        self.write_csv("device_id,status,temperature\nHOT,ok,80.1\nHOT,ok,90\n")
        summary = self.process()
        self.assertEqual(summary["devices"], [])
        self.assertEqual(summary["metadata"]["valid_rows"], 2)
        self.assertEqual(summary["metadata"]["excluded_devices"], 1)

    def test_header_only_is_empty_dataset(self) -> None:
        self.write_csv("device_id,status,temperature\n")
        summary = self.process()
        self.assertEqual(summary["devices"], [])
        self.assertEqual(summary["metadata"], {
            "total_input_rows": 0,
            "valid_rows": 0,
            "rejected_rows": 0,
            "excluded_devices": 0,
        })

    def test_missing_file_fails_without_creating_output(self) -> None:
        with self.assertRaisesRegex(ProcessingError, "not found"):
            process_csv(self.root / "missing.csv", self.output_path)
        self.assertFalse(self.output_path.exists())

    def test_missing_required_column_fails(self) -> None:
        self.write_csv("device_id,status\nD,ok\n")
        with self.assertRaisesRegex(ProcessingError, "temperature"):
            self.process()
        self.assertFalse(self.output_path.exists())

    def test_empty_file_without_header_fails(self) -> None:
        self.write_csv("")
        with self.assertRaisesRegex(ProcessingError, "no header"):
            self.process()

    def test_invalid_values_and_blank_fields_are_rejected(self) -> None:
        self.write_csv(
            "device_id,status,temperature\n"
            "A,ok,20\n"
            "A,ok,\n"
            "A,ok,not-a-number\n"
            "A,ok,NaN\n"
            "A,ok,Infinity\n"
            ",ok,1\n"
            "A,,1\n"
        )
        summary = self.process()
        self.assertEqual(summary["devices"], [{
            "device_id": "A",
            "total_records": 1,
            "average_temperature": 20.0,
            "error_count": 0,
        }])
        self.assertEqual(summary["metadata"]["total_input_rows"], 7)
        self.assertEqual(summary["metadata"]["valid_rows"], 1)
        self.assertEqual(summary["metadata"]["rejected_rows"], 6)

    def test_malformed_row_shapes_are_rejected(self) -> None:
        self.write_csv(
            "device_id,status,temperature\n"
            "A,ok,10\n"
            "B,ok\n"
            "C,ok,30,unexpected\n"
        )
        summary = self.process()
        self.assertEqual(summary["metadata"]["total_input_rows"], 3)
        self.assertEqual(summary["metadata"]["valid_rows"], 1)
        self.assertEqual(summary["metadata"]["rejected_rows"], 2)

    def test_all_invalid_rows_are_counted_and_not_aggregated(self) -> None:
        self.write_csv(
            "device_id,status,temperature\n"
            "A,ok,NaN\n"
            " ,ok,12\n"
        )
        summary = self.process()
        self.assertEqual(summary["devices"], [])
        self.assertEqual(summary["metadata"]["valid_rows"], 0)
        self.assertEqual(summary["metadata"]["rejected_rows"], 2)
        self.assertEqual(summary["metadata"]["excluded_devices"], 0)

    def test_output_path_write_error_is_reported(self) -> None:
        self.write_csv("device_id,status,temperature\nA,ok,10\n")
        blocked_output_path = self.root / "not-a-directory" / "summary.json"
        (self.root / "not-a-directory").write_text("block", encoding="utf-8")
        with self.assertRaises(OSError):
            process_csv(self.input_path, blocked_output_path)

    def test_cli_failure_does_not_print_success(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            exit_code = main(["--input", str(self.root / "missing.csv"), "--output", str(self.output_path)])
        self.assertEqual(exit_code, 1)
        self.assertIn("Error:", stderr.getvalue())
        self.assertNotIn("Summary written", stdout.getvalue())

    def test_malformed_quoting_is_fatal_without_report(self) -> None:
        self.write_csv('device_id,status,temperature\nA,"unterminated,20\n')
        with self.assertRaisesRegex(ProcessingError, "Could not read CSV"):
            self.process()
        self.assertFalse(self.output_path.exists())


if __name__ == "__main__":
    unittest.main()
