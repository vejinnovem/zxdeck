"""Pure-Python touchscreen calibration model and robust fitting."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from itertools import combinations
import json
from pathlib import Path
import statistics


@dataclass(frozen=True, slots=True)
class TouchCalibration:
    version: int
    x_axis: str
    y_axis: str
    x_slope: float
    x_offset: float
    y_slope: float
    y_offset: float

    def map(self, raw_x: int, raw_y: int, width: int, height: int) -> tuple[int, int]:
        axes = {"raw_x": raw_x, "raw_y": raw_y}
        x = round(self.x_slope * axes[self.x_axis] + self.x_offset)
        y = round(self.y_slope * axes[self.y_axis] + self.y_offset)
        return max(0, min(width - 1, x)), max(0, min(height - 1, y))

    @classmethod
    def load(cls, path: str | Path) -> "TouchCalibration":
        data = json.loads(Path(path).expanduser().read_text(encoding="utf-8"))
        fields = {field: data[field] for field in cls.__dataclass_fields__}
        return cls(**fields)

    def save(self, path: str | Path) -> None:
        output = Path(path).expanduser()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(asdict(self), indent=2) + "\n", encoding="utf-8")


def _covariance(values: list[int], targets: list[int]) -> float:
    mean_value = statistics.fmean(values)
    mean_target = statistics.fmean(targets)
    return sum(
        (value - mean_value) * (target - mean_target)
        for value, target in zip(values, targets)
    )


def _linear_fit(raw: list[int], pixels: list[int]) -> tuple[float, float]:
    mean_raw = statistics.fmean(raw)
    mean_pixel = statistics.fmean(pixels)
    variance = sum((value - mean_raw) ** 2 for value in raw)
    if variance == 0:
        raise ValueError("calibration axis has no measurable range")
    slope = sum(
        (value - mean_raw) * (pixel - mean_pixel)
        for value, pixel in zip(raw, pixels)
    ) / variance
    return slope, mean_pixel - slope * mean_raw


def _robust_fit(raw: list[int], pixels: list[int]) -> tuple[float, float, set[int]]:
    best_inliers: set[int] = set()
    best_error = float("inf")
    for first, second in combinations(range(len(raw)), 2):
        raw_span = raw[second] - raw[first]
        pixel_span = pixels[second] - pixels[first]
        if abs(raw_span) < 500 or abs(pixel_span) < 80:
            continue
        slope = pixel_span / raw_span
        offset = pixels[first] - slope * raw[first]
        errors = [
            abs(slope * value + offset - pixel)
            for value, pixel in zip(raw, pixels)
        ]
        inliers = {index for index, error in enumerate(errors) if error <= 25}
        mean_error = statistics.fmean(errors[index] for index in inliers)
        if len(inliers) > len(best_inliers) or (
            len(inliers) == len(best_inliers) and mean_error < best_error
        ):
            best_inliers = inliers
            best_error = mean_error
    if len(best_inliers) < 3:
        raise ValueError("calibration points do not form a consistent axis")
    indices = sorted(best_inliers)
    slope, offset = _linear_fit(
        [raw[index] for index in indices],
        [pixels[index] for index in indices],
    )
    return slope, offset, best_inliers


def fit_calibration(
    targets: list[tuple[int, int]], samples: list[tuple[int, int]]
) -> tuple[TouchCalibration, set[int]]:
    if len(targets) != len(samples) or len(targets) < 3:
        raise ValueError("targets and samples must have the same length of at least three")
    raw_x = [sample[0] for sample in samples]
    raw_y = [sample[1] for sample in samples]
    target_x = [target[0] for target in targets]
    target_y = [target[1] for target in targets]
    if abs(_covariance(raw_x, target_x)) >= abs(_covariance(raw_y, target_x)):
        x_axis, y_axis = "raw_x", "raw_y"
        x_values, y_values = raw_x, raw_y
    else:
        x_axis, y_axis = "raw_y", "raw_x"
        x_values, y_values = raw_y, raw_x
    x_slope, x_offset, x_inliers = _robust_fit(x_values, target_x)
    y_slope, y_offset, y_inliers = _robust_fit(y_values, target_y)
    accepted = x_inliers & y_inliers
    calibration = TouchCalibration(
        version=1,
        x_axis=x_axis,
        y_axis=y_axis,
        x_slope=x_slope,
        x_offset=x_offset,
        y_slope=y_slope,
        y_offset=y_offset,
    )
    return calibration, set(range(len(targets))) - accepted

