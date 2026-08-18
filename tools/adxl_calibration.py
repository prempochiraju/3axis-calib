#!/usr/bin/env python3
"""Fit and validate a simple six-position ADXL calibration.

Input columns:
    orientation,x,y,z

Orientations must include +X, -X, +Y, -Y, +Z, and -Z. Values may be in g or
raw counts; use --reference for the expected magnitude in the same units.
The fitted model is:

    corrected_axis = (measured_axis - offset_axis) * scale_axis
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path


AXES = ("x", "y", "z")
ORIENTATIONS = ("+X", "-X", "+Y", "-Y", "+Z", "-Z")


@dataclass(frozen=True)
class Sample:
    orientation: str
    x: float
    y: float
    z: float


@dataclass(frozen=True)
class AxisCalibration:
    offset: float
    scale: float


@dataclass(frozen=True)
class Calibration:
    x: AxisCalibration
    y: AxisCalibration
    z: AxisCalibration


def normalize_orientation(value: str) -> str:
    normalized = value.strip().upper().replace(" ", "")
    if normalized not in ORIENTATIONS:
        raise ValueError(
            f"unsupported orientation {value!r}; expected one of {ORIENTATIONS}"
        )
    return normalized


def read_samples(path: Path) -> list[Sample]:
    samples: list[Sample] = []
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        required = {"orientation", "x", "y", "z"}
        if reader.fieldnames is None or not required.issubset(reader.fieldnames):
            raise ValueError(f"CSV must contain columns {sorted(required)}")
        for line_number, row in enumerate(reader, start=2):
            try:
                samples.append(
                    Sample(
                        orientation=normalize_orientation(row["orientation"]),
                        x=float(row["x"]),
                        y=float(row["y"]),
                        z=float(row["z"]),
                    )
                )
            except (TypeError, ValueError) as exc:
                raise ValueError(f"invalid data on CSV line {line_number}: {exc}") from exc
    if not samples:
        raise ValueError("CSV contains no samples")
    return samples


def group_samples(samples: list[Sample]) -> dict[str, list[Sample]]:
    groups: dict[str, list[Sample]] = defaultdict(list)
    for sample in samples:
        groups[sample.orientation].append(sample)
    missing = [orientation for orientation in ORIENTATIONS if not groups[orientation]]
    if missing:
        raise ValueError(f"missing required orientations: {', '.join(missing)}")
    return dict(groups)


def axis_value(sample: Sample, axis: str) -> float:
    return getattr(sample, axis)


def fit_calibration(samples: list[Sample], reference: float = 1.0) -> Calibration:
    if reference <= 0:
        raise ValueError("reference must be positive")
    groups = group_samples(samples)
    fitted: dict[str, AxisCalibration] = {}
    for axis in AXES:
        positive = statistics.fmean(axis_value(s, axis) for s in groups[f"+{axis.upper()}"])
        negative = statistics.fmean(axis_value(s, axis) for s in groups[f"-{axis.upper()}"])
        span = positive - negative
        if span <= 0:
            raise ValueError(
                f"invalid {axis.upper()} endpoints: +{axis.upper()} mean {positive:.6g} "
                f"must exceed -{axis.upper()} mean {negative:.6g}"
            )
        fitted[axis] = AxisCalibration(
            offset=(positive + negative) / 2.0,
            scale=(2.0 * reference) / span,
        )
    return Calibration(**fitted)


def apply_calibration(sample: Sample, calibration: Calibration) -> Sample:
    return Sample(
        orientation=sample.orientation,
        x=(sample.x - calibration.x.offset) * calibration.x.scale,
        y=(sample.y - calibration.y.offset) * calibration.y.scale,
        z=(sample.z - calibration.z.offset) * calibration.z.scale,
    )


def magnitude(sample: Sample) -> float:
    return math.sqrt(sample.x * sample.x + sample.y * sample.y + sample.z * sample.z)


def summarize(samples: list[Sample], reference: float) -> dict:
    groups = group_samples(samples)
    orientation_stats = {}
    magnitude_errors = []
    for orientation in ORIENTATIONS:
        group = groups[orientation]
        magnitudes = [magnitude(sample) for sample in group]
        magnitude_errors.extend(abs(value - reference) for value in magnitudes)
        orientation_stats[orientation] = {
            "samples": len(group),
            "mean": {axis: statistics.fmean(axis_value(s, axis) for s in group) for axis in AXES},
            "stdev": {
                axis: statistics.stdev(axis_value(s, axis) for s in group)
                if len(group) > 1
                else 0.0
                for axis in AXES
            },
            "mean_magnitude": statistics.fmean(magnitudes),
            "mean_abs_magnitude_error": statistics.fmean(
                abs(value - reference) for value in magnitudes
            ),
        }
    return {
        "orientation_statistics": orientation_stats,
        "overall": {
            "samples": len(samples),
            "mean_abs_magnitude_error": statistics.fmean(magnitude_errors),
            "maximum_abs_magnitude_error": max(magnitude_errors),
        },
    }


def write_corrected(path: Path, raw: list[Sample], corrected: list[Sample]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "orientation",
                "raw_x",
                "raw_y",
                "raw_z",
                "corrected_x",
                "corrected_y",
                "corrected_z",
                "raw_magnitude",
                "corrected_magnitude",
            ]
        )
        for before, after in zip(raw, corrected):
            writer.writerow(
                [
                    before.orientation,
                    f"{before.x:.9f}",
                    f"{before.y:.9f}",
                    f"{before.z:.9f}",
                    f"{after.x:.9f}",
                    f"{after.y:.9f}",
                    f"{after.z:.9f}",
                    f"{magnitude(before):.9f}",
                    f"{magnitude(after):.9f}",
                ]
            )


def run(input_path: Path, report_path: Path, corrected_path: Path, reference: float) -> dict:
    samples = read_samples(input_path)
    calibration = fit_calibration(samples, reference)
    corrected = [apply_calibration(sample, calibration) for sample in samples]
    report = {
        "model": "corrected_axis = (measured_axis - offset_axis) * scale_axis",
        "input": str(input_path),
        "reference": reference,
        "coefficients": {axis: asdict(getattr(calibration, axis)) for axis in AXES},
        "before_calibration": summarize(samples, reference),
        "after_calibration": summarize(corrected, reference),
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    write_corrected(corrected_path, samples, corrected)
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="six-position CSV input")
    parser.add_argument("--reference", type=float, default=1.0, help="expected +/- endpoint magnitude (default: 1.0 g)")
    parser.add_argument("--report", type=Path, default=Path("calibration_report.json"), help="JSON report output")
    parser.add_argument("--corrected", type=Path, default=Path("corrected_samples.csv"), help="corrected CSV output")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    report = run(args.input, args.report, args.corrected, args.reference)
    print("Fitted coefficients:")
    for axis in AXES:
        values = report["coefficients"][axis]
        print(f"  {axis.upper()}: offset={values['offset']:.8f}, scale={values['scale']:.8f}")
    before = report["before_calibration"]["overall"]
    after = report["after_calibration"]["overall"]
    print(f"Mean |magnitude-reference|: {before['mean_abs_magnitude_error']:.8f} -> {after['mean_abs_magnitude_error']:.8f}")
    print(f"Report: {args.report}")
    print(f"Corrected samples: {args.corrected}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
