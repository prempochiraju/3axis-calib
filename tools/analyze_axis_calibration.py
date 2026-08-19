#!/usr/bin/env python3
"""Create per-axis calibration evidence files and SVG plots from a six-pose capture."""

import argparse
import csv
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path


# Physical fixture mapping inferred from the dominant gravity component.
# Original capture labels are retained in every output row for traceability.
POSE_MAP = {
    "+X": "-Y",
    "-X": "+Y",
    "+Y": "-X",
    "-Y": "+X",
    "+Z": "+Z",
    "-Z": "-Z",
}

AXES = ("x", "y", "z")
POSE_ORDER = ("+X", "-X", "+Y", "-Y", "+Z", "-Z")
COLORS = {"raw": "#6B7280", "corrected": "#1565C0", "ideal": "#17212B"}


def ideal(axis: str, pose: str) -> float:
    if pose[1].lower() != axis:
        return 0.0
    return 1.0 if pose[0] == "+" else -1.0


def write_plot(path: Path, axis: str, rows: list[dict], block_size: int = 10) -> None:
    blocks = []
    for start in range(0, len(rows), block_size):
        chunk = rows[start:start + block_size]
        blocks.append({
            "pose": chunk[0]["orientation"],
            "raw": statistics.fmean(row[f"raw_{axis}"] for row in chunk),
            "corrected": statistics.fmean(row[f"corrected_{axis}"] for row in chunk),
            "ideal": statistics.fmean(ideal(axis, row["orientation"]) for row in chunk),
        })

    width, height = 1400, 560
    x0, y0, plot_w, plot_h = 90, 90, 1240, 365
    low, high = -1.35, 1.45

    def px(index: float) -> float:
        return x0 + index / max(1, len(blocks) - 1) * plot_w

    def py(value: float) -> float:
        return y0 + plot_h - (value - low) / (high - low) * plot_h

    def points(key: str) -> str:
        return " ".join(f"{px(i):.1f},{py(row[key]):.1f}" for i, row in enumerate(blocks))

    regions = []
    start = 0
    for i in range(1, len(blocks) + 1):
        if i == len(blocks) or blocks[i]["pose"] != blocks[start]["pose"]:
            regions.append((start, i, blocks[start]["pose"]))
            start = i

    elements = [f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
<rect width="100%" height="100%" fill="white"/>
<style>text{{font-family:Arial,sans-serif;fill:#17212B}} .title{{font-size:26px;font-weight:bold}} .label{{font-size:16px}} .small{{font-size:14px}}</style>
<text x="70" y="40" class="title">ADXL362 {axis.upper()} axis: raw vs calibrated at 12.5 Hz</text>
<text x="70" y="67" class="label">1,000 samples per pose; plotted lines use non-overlapping 10-sample means.</text>
<rect x="{x0}" y="{y0}" width="{plot_w}" height="{plot_h}" fill="none" stroke="#9AA5AF"/>''']

    for index, (start, end, pose) in enumerate(regions):
        left, right = px(start), px(end - 1)
        if index % 2 == 0:
            elements.append(f'<rect x="{left:.1f}" y="{y0}" width="{max(1, right-left):.1f}" height="{plot_h}" fill="#E9EEF3" opacity="0.55"/>')
        if start:
            elements.append(f'<line x1="{left:.1f}" y1="{y0}" x2="{left:.1f}" y2="{y0+plot_h}" stroke="#B7C0C8"/>')
        elements.append(f'<text x="{(left+right)/2:.1f}" y="{y0+plot_h+28}" text-anchor="middle" class="label">{pose}</text>')

    for tick in (-1.0, -0.5, 0.0, 0.5, 1.0):
        y = py(tick)
        elements.append(f'<line x1="{x0}" y1="{y:.1f}" x2="{x0+plot_w}" y2="{y:.1f}" stroke="#D3D9DE"/>')
        elements.append(f'<text x="{x0-12}" y="{y+5:.1f}" text-anchor="end" class="small">{tick:.1f}</text>')

    elements.extend([
        f'<polyline points="{points("ideal")}" fill="none" stroke="{COLORS["ideal"]}" stroke-width="2" stroke-dasharray="7 5"/>',
        f'<polyline points="{points("raw")}" fill="none" stroke="{COLORS["raw"]}" stroke-width="2.4"/>',
        f'<polyline points="{points("corrected")}" fill="none" stroke="{COLORS["corrected"]}" stroke-width="2.4"/>',
        f'<text x="30" y="{y0+plot_h/2:.1f}" transform="rotate(-90 30 {y0+plot_h/2:.1f})" text-anchor="middle" class="label">{axis.upper()} acceleration (g)</text>',
        '<line x1="320" y1="535" x2="350" y2="535" stroke="#6B7280" stroke-width="4"/><text x="360" y="541" class="label">Raw</text>',
        '<line x1="510" y1="535" x2="540" y2="535" stroke="#1565C0" stroke-width="4"/><text x="550" y="541" class="label">Calibrated</text>',
        '<line x1="750" y1="535" x2="780" y2="535" stroke="#17212B" stroke-width="2" stroke-dasharray="7 5"/><text x="790" y="541" class="label">Ideal response</text>',
        '</svg>',
    ])
    path.write_text("\n".join(elements), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    with args.input.open(newline="", encoding="utf-8-sig") as handle:
        source = list(csv.DictReader(handle))
    if not source:
        raise ValueError("input contains no samples")

    rows = []
    grouped = defaultdict(list)
    for sample_index, row in enumerate(source):
        original_pose = row["orientation"]
        pose = POSE_MAP[original_pose]
        item = {
            "sample_index": sample_index,
            "original_orientation": original_pose,
            "orientation": pose,
            "time_ms": int(row["time_ms"]),
            **{f"raw_{axis}": float(row[axis]) for axis in AXES},
        }
        rows.append(item)
        grouped[pose].append(item)

    missing = [pose for pose in POSE_ORDER if pose not in grouped]
    if missing:
        raise ValueError(f"missing poses: {missing}")

    coefficients = {}
    for axis in AXES:
        positive = statistics.fmean(row[f"raw_{axis}"] for row in grouped[f"+{axis.upper()}"])
        negative = statistics.fmean(row[f"raw_{axis}"] for row in grouped[f"-{axis.upper()}"])
        offset = (positive + negative) / 2.0
        scale = 2.0 / (positive - negative)
        coefficients[axis] = {"positive_mean_g": positive, "negative_mean_g": negative,
                              "offset_g": offset, "scale": scale}

    for row in rows:
        for axis in AXES:
            coeff = coefficients[axis]
            row[f"corrected_{axis}"] = (row[f"raw_{axis}"] - coeff["offset_g"]) * coeff["scale"]
        row["raw_magnitude"] = math.sqrt(sum(row[f"raw_{axis}"] ** 2 for axis in AXES))
        row["corrected_magnitude"] = math.sqrt(sum(row[f"corrected_{axis}"] ** 2 for axis in AXES))

    args.output_dir.mkdir(parents=True, exist_ok=True)

    relabeled_path = args.output_dir / "relabeled_six_position.csv"
    with relabeled_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["original_orientation", "orientation", "time_ms", "x", "y", "z"])
        writer.writeheader()
        for row in rows:
            writer.writerow({"original_orientation": row["original_orientation"], "orientation": row["orientation"],
                             "time_ms": row["time_ms"], **{axis: f'{row[f"raw_{axis}"]:.9f}' for axis in AXES}})

    for axis in AXES:
        path = args.output_dir / f"{axis}_axis_calibrated_data.csv"
        fields = ["sample_index", "original_orientation", "orientation", "time_ms",
                  f"raw_{axis}_g", f"corrected_{axis}_g", f"ideal_{axis}_g",
                  "raw_signed_error_g", "corrected_signed_error_g"]
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            for row in rows:
                expected = ideal(axis, row["orientation"])
                writer.writerow({
                    "sample_index": row["sample_index"],
                    "original_orientation": row["original_orientation"],
                    "orientation": row["orientation"],
                    "time_ms": row["time_ms"],
                    f"raw_{axis}_g": f'{row[f"raw_{axis}"]:.9f}',
                    f"corrected_{axis}_g": f'{row[f"corrected_{axis}"]:.9f}',
                    f"ideal_{axis}_g": f"{expected:.1f}",
                    "raw_signed_error_g": f'{row[f"raw_{axis}"] - expected:.9f}',
                    "corrected_signed_error_g": f'{row[f"corrected_{axis}"] - expected:.9f}',
                })
        write_plot(args.output_dir / f"{axis}_axis_raw_vs_calibrated.svg", axis, rows)

    summary_rows = []
    for axis in AXES:
        active_rows = grouped[f"+{axis.upper()}"] + grouped[f"-{axis.upper()}"]
        raw_mae = statistics.fmean(abs(row[f"raw_{axis}"] - ideal(axis, row["orientation"])) for row in active_rows)
        corrected_mae = statistics.fmean(abs(row[f"corrected_{axis}"] - ideal(axis, row["orientation"])) for row in active_rows)
        summary_rows.append({"axis": axis.upper(), **coefficients[axis],
                             "active_pose_raw_mae_g": raw_mae,
                             "active_pose_corrected_mae_g": corrected_mae})

    with (args.output_dir / "axis_calibration_summary.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summary_rows[0]))
        writer.writeheader()
        writer.writerows(summary_rows)

    report = {
        "input": str(args.input),
        "samples": len(rows),
        "samples_per_original_pose": {pose: sum(row["original_orientation"] == pose for row in rows) for pose in POSE_ORDER},
        "pose_mapping": POSE_MAP,
        "model": "corrected_axis = (raw_axis - offset_axis) * scale_axis",
        "coefficients": coefficients,
        "axis_summary": summary_rows,
        "magnitude_mae_mg": {
            "raw": statistics.fmean(abs(row["raw_magnitude"] - 1.0) for row in rows) * 1000.0,
            "corrected_fitting_data": statistics.fmean(abs(row["corrected_magnitude"] - 1.0) for row in rows) * 1000.0,
        },
        "caution": "Corrected metrics use the fitting dataset; independent validation is still required.",
    }
    (args.output_dir / "axis_calibration_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
