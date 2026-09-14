import warnings

import numpy as np
import statsmodels.api as sm


def calibration_diagnostic(y: np.ndarray, probabilities: np.ndarray) -> dict:
    """Descriptive calibration GLM on evaluated outcomes, never applied to predictions."""
    unavailable = {"calibration_intercept": None, "calibration_slope": None}
    if len(y) < 100 or len(np.unique(y)) < 2 or probabilities.std() < 1e-6:
        return unavailable
    logits = np.log(probabilities / (1 - probabilities))
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            fit = sm.GLM(y, sm.add_constant(logits), family=sm.families.Binomial()).fit(maxiter=100)
        intercept, slope = fit.params
        if not fit.converged or not np.isfinite(fit.params).all():
            return unavailable
        return {"calibration_intercept": float(intercept), "calibration_slope": float(slope)}
    except (ValueError, np.linalg.LinAlgError):
        return unavailable
