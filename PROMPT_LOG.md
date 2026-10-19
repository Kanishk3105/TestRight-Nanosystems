# AI Prompt Log

## Initial Prompt

The initial user request supplied the full coding-assessment requirements. The chart-specific instruction was to create `plot_results.py` that validates Section 2 JSON, plots every retained device's average temperature with labeled axes and the title “Average Temperature by Device,” handles long labels/readability, and saves a verified PNG. The same request explicitly reserved Section 1 for independent candidate work.

## First Attempt Review

No separate earlier chart implementation or rendered image existed in the workspace. The first synthetic CLI run displayed the terminal table's degree symbol as a replacement character in captured PowerShell output (`Average Temperature (�C)`), reducing readability in that environment. The chart image itself was later rendered and inspected; its title, axes, and device labels were legible and no clipping was observed.

## Follow-up Prompt

No distinct follow-up prompt was issued. The original assessment request asked for a readable terminal table and a chart with an axis labeled in °C; there was no separate prompt after observing the output. This log does not invent a prompt or a prompt-driven event.

## Correction

Changed the terminal table header to ASCII `Average Temperature (C)` so it displays reliably in the captured Windows PowerShell output. The chart retains its required °C axis label. Also report oversized JSON integer temperatures as validation errors instead of allowing float conversion to escape as an uncaught overflow. The chart uses a device-count-aware figure width, rotated right-aligned labels, a y-axis grid, `tight_layout()`, and a tight saved bounding box.

## Verification

Ran `python -m unittest discover -s tests -v`: 22 tests passed, 0 failed. Ran `python -m py_compile main.py sanitize.py plot_results.py tests\test_main.py tests\test_plot_results.py` successfully. Ran `python .\main.py --input .\tests\fixtures\sample_device_telemetry.csv --output .\summary.json` and `python .\plot_results.py --input .\summary.json --output .\temperature_chart.png`; the output had four input/valid rows, no rejected rows, and one excluded device. The retained averages were 45.0 °C for DEV_A and exactly 80.0 °C for DEV_B; DEV_A had one ERROR record. Reloading the JSON confirmed these expected values and counts. The PNG exists and is 33,246 bytes. The generated chart was inspected in the workspace image viewer; the title, axis labels, bars, and rotated device IDs were visible without apparent clipping. The terminal table now renders its temperature unit as readable ASCII `(C)`.

## AI Usage Summary

AI assistance is used for Sections 2 and 3, their tests, and project documentation. `sanitize.py` contains only a placeholder for Section 1; no Section 1 solution or tests are provided.
