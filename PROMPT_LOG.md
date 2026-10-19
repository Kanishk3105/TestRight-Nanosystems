# AI Prompt Log

## Initial Prompt

The initial assessment prompt requested a chart script that must “Rotate device labels appropriately when necessary,” “Prevent overlapping labels, clipped titles, and unreadable tick labels,” and “Ensure the chart remains readable for long device IDs and numerous devices.” It also required the title “Average Temperature by Device,” the specified axis labels, and generation of `temperature_chart.png`.

## First Attempt Review

The initial chart with short fixture device IDs rendered correctly. When stress-tested with eight synthetic device IDs, each 158 characters long, `plot_results.py` emitted Matplotlib's warning: `Tight layout not applied. The bottom and top margins cannot be made large enough to accommodate all Axes decorations.` Inspection of the rendered PNG showed the plot squeezed to the right, excessive blank space, and very long diagonal tick labels. This was an actual long-label layout failure.

## Follow-up Prompt

The actual follow-up prompt was: “Stress-test plot_results.py using temporary synthetic JSON with multiple long device IDs. Generate and inspect the actual chart. If you observe a real layout problem, correct it, add a regression test, and record the actual initial prompt, observed problem, actual follow-up prompt, correction, and verification.”

## Correction

Wrapped long device labels at 18 characters, kept the wrapped labels horizontal and readable, and increased figure height according to the maximum wrapped label line count. This prevents the long rotated tick labels from forcing the plot area to collapse. Added a regression test using eight 158-character device IDs; it verifies no tight-layout warning and checks that the resulting chart is wider than it is tall.

## Verification

The pre-correction command `python .\plot_results.py --input C:\Users\kanis\AppData\Local\Temp\device-chart-stress-g89bpkk4\long-device-ids.json --output C:\Users\kanis\AppData\Local\Temp\device-chart-stress-g89bpkk4\long-device-ids-chart.png` produced a 254,732-byte PNG and the warning/layout failure described above. After correction, the same input was rendered to `long-device-ids-chart-fixed.png` (63,523 bytes; 1514 × 1093 pixels); it emitted no tight-layout warning and was inspected in the image viewer. `python -m unittest tests.test_plot_results.PlotResultsTests.test_long_device_ids_fit_without_tight_layout_warning -v` passed. The final full run `python -m unittest discover -s tests -v` completed with 23 tests passed and 0 failures. `python -m py_compile main.py sanitize.py plot_results.py tests\__init__.py tests\test_main.py tests\test_plot_results.py` succeeded. The deliverable `temperature_chart.png` was regenerated from `summary.json`, which is based on the clearly identified synthetic fixture, not official assessment data.

## AI Usage Summary

AI assistance is used for Sections 2 and 3, their tests, and project documentation. `sanitize.py` contains only a placeholder for Section 1; no Section 1 solution or tests are provided.
