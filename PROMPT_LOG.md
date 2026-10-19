# AI Prompt Log

## Initial Prompt

**Verbatim extract from the initial chart-generation prompt:**

> “Rotate device labels appropriately when necessary.”
>
> “Prevent overlapping labels, clipped titles, and unreadable tick labels.”
>
> “Ensure the chart remains readable for long device IDs and numerous devices.”

The initial prompt also specified the title “Average Temperature by Device,” the required axis labels, and generation of `temperature_chart.png`.

## First Attempt Review

The review-only input contains six synthetic device IDs, each 158 characters long. Running `python .\review-only\chart-first-attempt\first_attempt_plot.py` produced `review-only\chart-first-attempt\first_attempt_chart.png` and emitted this Matplotlib warning: `Tight layout not applied. The bottom and top margins cannot be made large enough to accommodate all Axes decorations.` Visual inspection of that PNG showed the device labels clipped at the bottom and the x-axis label invisible.

## Follow-up Prompt

**Follow-up prompt recorded in the earlier committed version of this log:**

> Stress-test plot_results.py using temporary synthetic JSON with multiple long device IDs. Generate and inspect the actual chart. If you observe a real layout problem, correct it, add a regression test, and record the actual initial prompt, observed problem, actual follow-up prompt, correction, and verification.

## Correction

The production `plot_results.py` already wraps long IDs at 18 characters and adjusts the figure height for the wrapped labels. It continues to load chart data from JSON. No production code change was made during this review. The follow-up prompt is recorded above as historical prompt text; the verification below records what was actually rerun in this workspace.

## Verification

- Ran `python .\review-only\chart-first-attempt\first_attempt_plot.py`; it emitted the tight-layout warning quoted above. The resulting PNG was visually inspected and showed clipped device labels and no visible x-axis label.
- Ran `python .\plot_results.py --input .\review-only\chart-first-attempt\synthetic_device_summary.json --output .\review-only\chart-first-attempt\corrected_production_chart.png`; the command completed without a tight-layout warning. The generated PNG is 1319 × 1093 pixels and 58,644 bytes. Visual inspection confirmed all six 158-character IDs are wrapped and readable, the `Device ID` label and title are visible, and the temperature axis reads `Average Temperature (°C)`.
- Ran `python -m unittest tests.test_plot_results.PlotResultsTests.test_long_device_ids_fit_without_tight_layout_warning -v`; the test passed. This existing test exercises eight generated long IDs and checks for the tight-layout warning.
- The official `device_telemetry.csv` is not present in the workspace. The available chart input is synthetic and was used only for review.

## AI Usage Summary

AI assistance was used for the chart review and documentation. `sanitize.py` remains a placeholder. No Section 1 implementation or tests were generated; Section 1 remains the candidate's independent work.
