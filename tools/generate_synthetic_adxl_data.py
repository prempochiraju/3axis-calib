#!/usr/bin/env python3
"""Generate deterministic six-position data for calibration-tool verification."""

from __future__ import annotations

import argparse
import csv
import random
from pathlib import Path


ORIENTATIONS = {
    "+X": (1.0, 0.0, 0.0),
    "-X": (-1.0, 0.0, 0.0),
    "+Y": (0.0, 1.0, 0.0),
    "-Y": (0.0, -1.0, 0.0),
    "+Z": (0.0, 0.0, 1.0),
    "-Z": (0.0, 0.0, -1.0),
}

# These are the known correction coefficients the fitting tool should recover.
OFFSETS = (0.040, -0.025, 0.060)
SCALES = (1.030, 0.970, 1.050)


def generate(path: Path, samples_per_orientation: int, noise_sigma: float, seed: int) -> None:
    if samples_per_orientation < 2:
        raise ValueError("samples per orientation must be at least 2")
    if noise_sigma < 0:
        raise ValueError("noise sigma cannot be negative")
    rng = random.Random(seed)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["orientation", "x", "y", "z"])
        for orientation, true_vector in ORIENTATIONS.items():
            for _ in range(samples_per_orientation):
                # Invert corrected=(raw-offset)*scale to synthesize raw data.
                raw = [
                    true_vector[i] / SCALES[i] + OFFSETS[i] + rng.gauss(0.0, noise_sigma)
                    for i in range(3)
                ]
                writer.writerow([orientation, *(f"{value:.9f}" for value in raw)])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--samples", type=int, default=200)
    parser.add_argument("--noise", type=float, default=0.002)
    parser.add_argument("--seed", type=int, default=362)
    args = parser.parse_args()
    generate(args.output, args.samples, args.noise, args.seed)
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
