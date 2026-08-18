# ADXL362 Three-Axis Calibration

Engineering evaluation project for collecting six-position ADXL362 data with
an nRF52840 DK and calculating independent X/Y/Z bias and scale corrections.

This is a learning and bench-characterization project. It is not production or
clinical firmware.

## Hardware assumption

- Nordic nRF52840 DK
- Analog Devices EVAL-ADXL362Z breakout board
- SPI wiring described in `firmware/OFFLINE_INSTRUCTIONS.txt`

Confirm the exact evaluation-board model and printed pin labels before applying
power. The larger ARDZ shield and ADXL362 datalogger board use different
connectors and setup.

## Repository contents

```text
firmware/   nRF Connect SDK application and offline operating guide
tools/      calibration, synthetic-data, and dependency-free plotting tools
tests/      PC-side calibration unit test
docs/       calibration-tool input and output description
```

## Firmware workflow

Open `firmware/` as an existing application in nRF Connect for VS Code.

Select the board target:

```text
nrf52840dk/nrf52840
```

Older SDK releases may call it:

```text
nrf52840dk_nrf52840
```

Build, flash, then open the DK virtual COM port at `115200 8N1`. The application
uses DK Button 1 to guide the operator through `+X`, `-X`, `+Y`, `-Y`, `+Z`, and
`-Z`. Each press starts a three-second settling period followed by five seconds
of CSV capture.

## Calibration model

For each axis:

```text
offset = (positive_endpoint + negative_endpoint) / 2
scale  = 2 g / (positive_endpoint - negative_endpoint)
corrected = (measured - offset) * scale
```

This diagonal model corrects independent bias and scale errors. It does not
estimate cross-axis misalignment, nonlinearity, or temperature dependence.

## PC-side demonstration

```powershell
python tools/generate_synthetic_adxl_data.py outputs/synthetic_six_position.csv
python tools/adxl_calibration.py outputs/synthetic_six_position.csv `
    --report outputs/synthetic_calibration_report.json `
    --corrected outputs/synthetic_corrected_samples.csv
python tools/plot_adxl_calibration.py outputs/synthetic_corrected_samples.csv `
    --output outputs/synthetic_comparison.svg
python -m unittest discover -s tests -v
```

For hardware, preserve the original serial capture and use a separate cleaned
CSV for analysis. Independent validation orientations should be collected after
fitting; improvement on fitting samples alone is not sufficient verification.

## Public references

- [ADXL362 product page and datasheet](https://www.analog.com/en/products/adxl362.html)
- [EVAL-ADXL362Z documentation](https://www.analog.com/en/resources/evaluation-hardware-and-software/evaluation-boards-kits/eval-adxl362z.html)
- [nRF52840 DK documentation](https://docs.zephyrproject.org/latest/boards/nordic/nrf52840dk/doc/index.html)
- [Nordic build workflow](https://docs.nordicsemi.com/r/bundle/nrf-connect-vscode/page/get_started/build_app_ncs.html/how-to-build-an-application)

