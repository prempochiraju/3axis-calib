# ADXL six-position calibration analysis tool

This PC-side tool turns six-position measurements into coefficients for the
existing firmware correction model:

```text
corrected_axis = (measured_axis - offset_axis) * scale_axis
```

It is a characterization aid, not production or clinical software.

## Input

Create a CSV with measurements expressed in **g**:

```csv
orientation,x,y,z
+X,1.012,-0.018,0.044
+X,1.010,-0.020,0.043
-X,-0.930,-0.017,0.041
```

The file must contain samples for `+X`, `-X`, `+Y`, `-Y`, `+Z`, and `-Z`.
Use multiple settled, stationary samples for every orientation. Keep raw,
immutable captures and the sensor configuration with the test evidence.

## Demonstration without hardware

From the repository root, use the approved Python environment:

```powershell
python tools/generate_synthetic_adxl_data.py outputs/synthetic_six_position.csv
python tools/adxl_calibration.py outputs/synthetic_six_position.csv `
    --report outputs/synthetic_calibration_report.json `
    --corrected outputs/synthetic_corrected_samples.csv
python -m unittest discover -s tests -v
```

The generator injects these known correction coefficients:

| Axis | Offset (g) | Scale |
|---|---:|---:|
| X | +0.040 | 1.030 |
| Y | -0.025 | 0.970 |
| Z | +0.060 | 1.050 |

The analysis should recover approximately those values, with small differences
caused by the deterministic simulated noise.

## Outputs

- JSON report containing coefficients and before/after statistics.
- CSV containing raw values, corrected values, and both vector magnitudes.
- Console summary suitable for a quick engineering status update.

## Important limitation

Six endpoint means fit independent bias and scale for each axis. They do not
identify a full cross-axis/misalignment matrix. Use separate intermediate
orientations for validation, and add a matrix model only if measured residual
error and requirements justify it.
