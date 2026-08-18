#!/usr/bin/env python3
"""Create a dependency-free SVG calibration comparison plot."""

import argparse
import csv
from pathlib import Path

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path, help="corrected CSV from adxl_calibration.py")
    parser.add_argument("--output", type=Path, default=Path("outputs/calibration_comparison.svg"))
    args = parser.parse_args()

    raw = []
    corrected = []
    with args.input.open(newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            raw.append(float(row["raw_magnitude"]))
            corrected.append(float(row["corrected_magnitude"]))

    if not raw:
        raise ValueError("input contains no samples")

    raw_mae = sum(abs(value - 1.0) for value in raw) / len(raw)
    corrected_mae = sum(abs(value - 1.0) for value in corrected) / len(corrected)

    width, height = 1200, 520
    x0, y0, plot_w, plot_h = 70, 80, 700, 350
    all_values = raw + corrected + [1.0]
    lower = min(all_values) - 0.02
    upper = max(all_values) + 0.02
    if upper - lower < 0.1:
        lower, upper = 0.9, 1.1

    def px(index: int) -> float:
        return x0 + (index / max(1, len(raw) - 1)) * plot_w

    def py(value: float) -> float:
        return y0 + plot_h - ((value - lower) / (upper - lower)) * plot_h

    def points(values: list[float]) -> str:
        return " ".join(f"{px(i):.1f},{py(v):.1f}" for i, v in enumerate(values))

    max_mae_mg = max(raw_mae, corrected_mae) * 1000.0
    bar_scale = 250.0 / max(max_mae_mg, 1.0)
    raw_h = raw_mae * 1000.0 * bar_scale
    corrected_h = corrected_mae * 1000.0 * bar_scale
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
<rect width="100%" height="100%" fill="white"/>
<style>text{{font-family:Arial,sans-serif;fill:#17212B}} .small{{font-size:15px}} .title{{font-size:24px;font-weight:bold}}</style>
<text x="70" y="38" class="title">ADXL362: uncalibrated vs calibrated</text>
<line x1="{x0}" y1="{y0}" x2="{x0}" y2="{y0+plot_h}" stroke="#65717C"/>
<line x1="{x0}" y1="{y0+plot_h}" x2="{x0+plot_w}" y2="{y0+plot_h}" stroke="#65717C"/>
<line x1="{x0}" y1="{py(1.0):.1f}" x2="{x0+plot_w}" y2="{py(1.0):.1f}" stroke="#17212B" stroke-dasharray="7 5"/>
<polyline points="{points(raw)}" fill="none" stroke="#65717C" stroke-width="1.5" opacity="0.8"/>
<polyline points="{points(corrected)}" fill="none" stroke="#147D64" stroke-width="1.5" opacity="0.85"/>
<text x="{x0}" y="{y0-12}" class="small">Magnitude (g)</text>
<text x="{x0+plot_w-100}" y="{y0+plot_h+28}" class="small">Sample</text>
<line x1="90" y1="470" x2="120" y2="470" stroke="#65717C" stroke-width="3"/><text x="130" y="476" class="small">Uncalibrated</text>
<line x1="260" y1="470" x2="290" y2="470" stroke="#147D64" stroke-width="3"/><text x="300" y="476" class="small">Calibrated</text>
<line x1="410" y1="470" x2="440" y2="470" stroke="#17212B" stroke-dasharray="7 5"/><text x="450" y="476" class="small">Expected 1 g</text>
<text x="825" y="80" class="title">Mean absolute error</text>
<rect x="865" y="{420-raw_h:.1f}" width="100" height="{raw_h:.1f}" fill="#65717C"/>
<rect x="1030" y="{420-corrected_h:.1f}" width="100" height="{corrected_h:.1f}" fill="#147D64"/>
<text x="915" y="{405-raw_h:.1f}" text-anchor="middle" class="small">{raw_mae*1000.0:.2f} mg</text>
<text x="1080" y="{405-corrected_h:.1f}" text-anchor="middle" class="small">{corrected_mae*1000.0:.2f} mg</text>
<text x="915" y="450" text-anchor="middle" class="small">Uncalibrated</text>
<text x="1080" y="450" text-anchor="middle" class="small">Calibrated</text>
</svg>'''
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(svg, encoding="utf-8")
    print(f"Saved: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
