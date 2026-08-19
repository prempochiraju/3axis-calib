#!/usr/bin/env python3
"""Create a meeting-ready SVG showing each axis and gravity magnitude by pose."""

import argparse
import csv
from pathlib import Path


SERIES = {
    "X": ("raw_x", "corrected_x", "#276FBF"),
    "Y": ("raw_y", "corrected_y", "#D97706"),
    "Z": ("raw_z", "corrected_z", "#159570"),
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path, default=Path("outputs/hardware_axis_comparison.svg"))
    args = parser.parse_args()

    rows = list(csv.DictReader(args.input.open(newline="", encoding="utf-8-sig")))
    if not rows:
        raise ValueError("input contains no samples")

    # Average small blocks so the meeting graphic remains readable and compact.
    block = 10
    groups = []
    for start in range(0, len(rows), block):
        chunk = rows[start:start + block]
        groups.append({
            "orientation": chunk[0]["orientation"],
            **{
                key: sum(float(row[key]) for row in chunk) / len(chunk)
                for key in (
                    "raw_x", "raw_y", "raw_z", "corrected_x", "corrected_y",
                    "corrected_z", "raw_magnitude", "corrected_magnitude"
                )
            },
        })

    regions = []
    region_start = 0
    for i in range(1, len(groups) + 1):
        if i == len(groups) or groups[i]["orientation"] != groups[region_start]["orientation"]:
            regions.append((region_start, i, groups[region_start]["orientation"]))
            region_start = i

    width, height = 1400, 980
    x0, plot_w = 95, 1220
    panels = [(105, 235, "Uncalibrated axis output", "raw"),
              (400, 235, "Calibrated axis output", "corrected"),
              (695, 190, "Gravity-vector magnitude", "magnitude")]

    def px(index: float) -> float:
        return x0 + (index / max(1, len(groups) - 1)) * plot_w

    def path(values, top, panel_h, low, high):
        def py(value):
            return top + panel_h - ((value - low) / (high - low)) * panel_h
        return " ".join(f"{px(i):.1f},{py(value):.1f}" for i, value in enumerate(values))

    parts = [f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
<rect width="100%" height="100%" fill="white"/>
<style>
text{{font-family:Arial,sans-serif;fill:#17212B}} .title{{font-size:27px;font-weight:bold}}
.panel{{font-size:20px;font-weight:bold}} .label{{font-size:16px}} .small{{font-size:14px}}
</style>
<text x="70" y="42" class="title">ADXL362 six-position calibration: axis-by-axis result</text>
<text x="70" y="70" class="label">Each shaded region contains 500 stationary samples; expected active axis is +1 g or -1 g.</text>''']

    for top, panel_h, title, kind in panels:
        low, high = (-1.35, 1.45) if kind != "magnitude" else (0.65, 1.36)
        parts.append(f'<text x="{x0}" y="{top-15}" class="panel">{title}</text>')
        parts.append(f'<rect x="{x0}" y="{top}" width="{plot_w}" height="{panel_h}" fill="none" stroke="#9AA5AF"/>')
        for r_index, (start, end, label) in enumerate(regions):
            left = px(start)
            right = px(end - 1)
            if r_index % 2 == 0:
                parts.append(f'<rect x="{left:.1f}" y="{top}" width="{max(1,right-left):.1f}" height="{panel_h}" fill="#E9EEF3" opacity="0.55"/>')
            if kind == "magnitude":
                parts.append(f'<text x="{(left+right)/2:.1f}" y="{top+panel_h+25}" text-anchor="middle" class="label">{label}</text>')
            if start:
                parts.append(f'<line x1="{left:.1f}" y1="{top}" x2="{left:.1f}" y2="{top+panel_h}" stroke="#B7C0C8"/>')

        def py(value):
            return top + panel_h - ((value - low) / (high - low)) * panel_h

        ticks = [-1, 0, 1] if kind != "magnitude" else [0.75, 1.0, 1.25]
        for tick in ticks:
            y = py(tick)
            parts.append(f'<line x1="{x0}" y1="{y:.1f}" x2="{x0+plot_w}" y2="{y:.1f}" stroke="#CFD6DC"/>')
            parts.append(f'<text x="{x0-12}" y="{y+5:.1f}" text-anchor="end" class="small">{tick:g}</text>')
        parts.append(f'<text x="{x0-58}" y="{top+panel_h/2:.1f}" transform="rotate(-90 {x0-58} {top+panel_h/2:.1f})" text-anchor="middle" class="label">Acceleration (g)</text>')

        if kind == "magnitude":
            parts.append(f'<line x1="{x0}" y1="{py(1):.1f}" x2="{x0+plot_w}" y2="{py(1):.1f}" stroke="#17212B" stroke-width="2" stroke-dasharray="8 6"/>')
            for key, color, label in (("raw_magnitude", "#6B7280", "Uncalibrated magnitude"),
                                      ("corrected_magnitude", "#7C3AED", "Calibrated magnitude")):
                values = [group[key] for group in groups]
                parts.append(f'<polyline points="{path(values, top, panel_h, low, high)}" fill="none" stroke="{color}" stroke-width="2.5"/>')
        else:
            prefix = "raw" if kind == "raw" else "corrected"
            for axis, (_, _, color) in SERIES.items():
                values = [group[f"{prefix}_{axis.lower()}"] for group in groups]
                parts.append(f'<polyline points="{path(values, top, panel_h, low, high)}" fill="none" stroke="{color}" stroke-width="2.2"/>')

    parts.append('''
<line x1="95" y1="947" x2="125" y2="947" stroke="#276FBF" stroke-width="4"/><text x="135" y="953" class="label">X axis</text>
<line x1="225" y1="947" x2="255" y2="947" stroke="#D97706" stroke-width="4"/><text x="265" y="953" class="label">Y axis</text>
<line x1="355" y1="947" x2="385" y2="947" stroke="#159570" stroke-width="4"/><text x="395" y="953" class="label">Z axis</text>
<line x1="490" y1="947" x2="520" y2="947" stroke="#6B7280" stroke-width="4"/><text x="530" y="953" class="label">Uncalibrated magnitude</text>
<line x1="755" y1="947" x2="785" y2="947" stroke="#7C3AED" stroke-width="4"/><text x="795" y="953" class="label">Calibrated magnitude</text>
<line x1="1035" y1="947" x2="1065" y2="947" stroke="#17212B" stroke-width="2" stroke-dasharray="8 6"/><text x="1075" y="953" class="label">Expected 1 g</text>
</svg>''')

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(parts), encoding="utf-8")
    print(f"Saved: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
