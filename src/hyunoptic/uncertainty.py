"""Reference-free geometric sensitivity analysis (research-only, not clinical uncertainty)."""
from __future__ import annotations
from dataclasses import asdict, dataclass
import numpy as np

@dataclass(frozen=True)
class PerturbationConfig:
    draws: int = 500
    seed: int = 42
    shared_log_sd: float = 0.02
    cup_log_sd: float = 0.03
    disc_log_sd: float = 0.03

    def validate(self) -> None:
        if not isinstance(self.draws, int) or not 30 <= self.draws <= 100_000:
            raise ValueError("draws must be an integer from 30 to 100000")
        if not isinstance(self.seed, int) or self.seed < 0:
            raise ValueError("seed must be a non-negative integer")
        for name in ("shared_log_sd", "cup_log_sd", "disc_log_sd"):
            value = getattr(self, name)
            if not np.isfinite(value) or not 0 <= value <= 0.5:
                raise ValueError(f"{name} must be finite between 0 and 0.5")

@dataclass(frozen=True)
class SensitivityResult:
    method: str
    nominal_continuous_vcdr: float
    simulated_mean_vcdr: float
    simulated_sd_vcdr: float
    simulated_percentile_2_5: float
    simulated_percentile_97_5: float
    q95_absolute_vcdr_change: float
    delta_method_variance_vcdr: float
    empirical_variance_vcdr: float
    covariance_cup_disc_vertical: float
    delta_method_variance_without_covariance: float
    implied_cup_disc_correlation: float | None
    sample_count: int
    settings: dict
    interpretation: str

    def to_dict(self) -> dict:
        return asdict(self)

def _vertical_extent(points_xy: np.ndarray, name: str) -> float:
    points = np.asarray(points_xy, dtype=np.float64)
    if points.ndim != 2 or points.shape[1] != 2 or points.shape[0] < 3:
        raise ValueError(f"{name} must contain at least three (x,y) points")
    if not np.isfinite(points).all():
        raise ValueError(f"{name} has non-finite coordinates")
    extent = float(np.ptp(points[:, 1]))
    if extent <= 0:
        raise ValueError(f"{name} has zero vertical extent")
    return extent

def analyze_vertical_sensitivity(
    disc_xy: np.ndarray, cup_xy: np.ndarray,
    config: PerturbationConfig | None = None,
) -> SensitivityResult:
    """Analyze one candidate reader only: shared and independent log-scale jitter.

    Continuous contour extrema (no inclusive pixel-mask rounding) are used.
    Percentiles describe ASSUMED geometric perturbations, not clinical CIs.
    """
    config = config or PerturbationConfig()
    config.validate()
    disc_extent = _vertical_extent(disc_xy, "disc_xy")
    cup_extent = _vertical_extent(cup_xy, "cup_xy")
    nominal = cup_extent / disc_extent
    rng = np.random.default_rng(config.seed)
    shared = rng.normal(0.0, config.shared_log_sd, config.draws)
    cup_factor = np.exp(shared + rng.normal(0.0, config.cup_log_sd, config.draws))
    disc_factor = np.exp(shared + rng.normal(0.0, config.disc_log_sd, config.draws))
    cups = cup_extent * cup_factor
    discs = disc_extent * disc_factor
    ratios = cups / discs
    cov = float(np.cov(cups, discs, ddof=1)[0, 1])
    var_cup = float(np.var(cups, ddof=1))
    var_disc = float(np.var(discs, ddof=1))
    mu_cup, mu_disc = float(np.mean(cups)), float(np.mean(discs))
    independent_var = var_cup / mu_disc**2 + mu_cup**2 * var_disc / mu_disc**4
    delta_var = independent_var - 2.0 * mu_cup * cov / mu_disc**3
    denominator = np.sqrt(var_cup * var_disc)
    corr = float(cov / denominator) if denominator > 0 else None
    lo, hi = np.percentile(ratios, (2.5, 97.5))
    return SensitivityResult(
        method="paired_lognormal_vertical_extent_sensitivity_v1",
        nominal_continuous_vcdr=nominal,
        simulated_mean_vcdr=float(np.mean(ratios)),
        simulated_sd_vcdr=float(np.std(ratios, ddof=1)),
        simulated_percentile_2_5=float(lo),
        simulated_percentile_97_5=float(hi),
        q95_absolute_vcdr_change=float(np.percentile(np.abs(ratios - nominal), 95)),
        delta_method_variance_vcdr=float(max(delta_var, 0.0)),
        empirical_variance_vcdr=float(np.var(ratios, ddof=1)),
        covariance_cup_disc_vertical=cov,
        delta_method_variance_without_covariance=float(independent_var),
        implied_cup_disc_correlation=corr,
        sample_count=config.draws,
        settings=asdict(config),
        interpretation=(
            "Synthetic geometric sensitivity, NOT medical prediction. "
            "2.5/97.5 percentiles are simulated sensitivity bounds, not clinical confidence intervals. "
            "Shared covariance is imposed by the perturbation model; not measured from experts."
        ),
    )
