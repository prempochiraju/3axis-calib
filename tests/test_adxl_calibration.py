import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from adxl_calibration import apply_calibration, fit_calibration, read_samples, run
from generate_synthetic_adxl_data import OFFSETS, SCALES, generate


class CalibrationToolTests(unittest.TestCase):
    def test_recovers_injected_coefficients_and_reduces_error(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            directory = Path(temp_dir)
            input_path = directory / "synthetic.csv"
            report_path = directory / "report.json"
            corrected_path = directory / "corrected.csv"
            generate(input_path, samples_per_orientation=500, noise_sigma=0.001, seed=362)

            samples = read_samples(input_path)
            fitted = fit_calibration(samples)
            for index, axis in enumerate(("x", "y", "z")):
                values = getattr(fitted, axis)
                self.assertAlmostEqual(values.offset, OFFSETS[index], delta=0.0002)
                self.assertAlmostEqual(values.scale, SCALES[index], delta=0.0003)

            report = run(input_path, report_path, corrected_path, reference=1.0)
            before = report["before_calibration"]["overall"]["mean_abs_magnitude_error"]
            after = report["after_calibration"]["overall"]["mean_abs_magnitude_error"]
            self.assertLess(after, before / 20.0)
            self.assertTrue(report_path.exists())
            self.assertTrue(corrected_path.exists())


if __name__ == "__main__":
    unittest.main()
