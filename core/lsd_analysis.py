"""LSD basic analysis framework.

Provides profile analysis, RV fitting, noise (null test) statistics, and
mean longitudinal magnetic field computation from a saved LSD profile file.

See docs/physics.md §7-8 for the underlying equations.
"""

import warnings

import numpy as np
import scipy.special as specialf
from scipy.optimize import OptimizeWarning, curve_fit

# NumPy ≥ 2.0 renamed trapz → trapezoid; support both.
_trapz = getattr(np, 'trapezoid', getattr(np, 'trapz', None))

# Speed of light in km/s
c = 2.99792458e5

# Coefficient for Bl first-moment formula (see docs/physics.md §Bl)
# Bl [G] = -_BL_COEFF * int(v V dv) / (g_eff * lambda_A * c * int((1-I) dv))
_BL_COEFF = 2.14e11

# Detection probability thresholds from Donati et al. (1997), see docs/physics.md §7.
# FAP < 1e-4 → definite detection; FAP < 1e-2 → marginal detection.
_FAP_DEFINITE = 1e-4
_FAP_MARGINAL = 1e-2

# Minimum sigma_V value to consider the V channel as containing real data
# (distinguishes zero-filled I-only spectra from actual Stokes V measurements).
_MIN_SIGMA_V = 1e-20


def load_lsd_profile(fname):
    """Load an LSD profile .dat file into numpy arrays.

    File format (written by prof.save()):
      Line 1: comment header
      Line 2: npix stokes_code
      Columns: vel(km/s)  I/Ic  sigI  V/Ic  sigV  N1/Ic  sigN1

    Returns a dict with keys:
      vel, specI_Ic, specSigI, specV, specSigV, specN1, specSigN1
    """
    data = np.loadtxt(fname, skiprows=2)
    if data.ndim == 1:
        data = data.reshape(1, -1)
    return {
        'vel': data[:, 0],
        'specI_Ic': data[:, 1],
        'specSigI': data[:, 2],
        'specV': data[:, 3],
        'specSigV': data[:, 4],
        'specN1': data[:, 5],
        'specSigN1': data[:, 6],
    }


def _estimate_line_region(specI_Ic, specSigI):
    """Identify velocity pixels inside and outside the absorption line.

    Mirrors the logic of estimateLineRange in core/lsd_report.py but works
    directly on I/Ic arrays and returns index vectors rather than slices.

    Returns (i_in, i_out) — 1-D integer index arrays.
    """
    depth = 1.0 - specI_Ic
    n = len(depth)
    pad = 2

    if n < 2 * (20 + pad):
        # Short profile: threshold at half the peak depth
        thresh = 0.5 * np.max(depth)
        i_in = np.where(depth > thresh)[0]
        i_out = np.where(depth <= thresh)[0]
        return i_in, i_out

    outer_depth = np.concatenate([depth[pad:20 + pad], depth[-20 - pad:-pad]])
    outer_sig = np.concatenate([specSigI[pad:20 + pad], specSigI[-20 - pad:-pad]])
    approx_cont = float(np.mean(outer_depth))
    approx_err = float(np.std(outer_depth))
    mean_err = float(np.mean(outer_sig))

    scale = 1.0
    if (approx_err > 1.1 * mean_err and mean_err > 0):
        scale = approx_err / mean_err

    interior = np.arange(pad, n - pad)
    above = depth[interior] > approx_cont + 4.0 * scale * specSigI[interior]
    i_in = interior[above]
    i_out = interior[~above]
    return i_in, i_out


def _gaussian(x, amplitude, center, sigma_g):
    return amplitude * np.exp(-0.5 * ((x - center) / sigma_g) ** 2)


def _profile_stats(vel, specI_Ic, specSigI, i_in):
    """Compute basic profile statistics (depth, EW, centroid, FWHM, SNR)."""
    depth = 1.0 - specI_Ic
    max_depth = float(np.max(depth))

    # EW and centroid use the in-line region if identified; otherwise full range
    region = i_in if len(i_in) > 0 else np.arange(len(vel))

    ew_kms = float(_trapz(depth[region], vel[region]))

    total_depth = float(np.sum(depth[region]))
    if (total_depth > 0):
        centroid_kms = float(np.sum(vel[region] * depth[region]) / total_depth)
    else:
        centroid_kms = float(vel[len(vel) // 2])

    # FWHM: find velocity extent at half-maximum depth
    half_max = 0.5 * max_depth
    above_half = depth >= half_max
    fwhm_kms = None
    if (np.any(above_half)):
        left_idx = int(np.argmax(above_half))
        right_idx = int(len(above_half) - 1 - np.argmax(above_half[::-1]))
        if (right_idx > left_idx):
            fwhm_kms = float(vel[right_idx] - vel[left_idx])

    # Per-pixel SNR estimates
    med_sigI = float(np.median(specSigI))
    snr_I = float(max_depth / med_sigI) if (med_sigI > 0) else None

    line_vel_min = float(vel[i_in[0]]) if len(i_in) > 0 else None
    line_vel_max = float(vel[i_in[-1]]) if len(i_in) > 0 else None

    return {
        'n_pixels': int(len(vel)),
        'vel_range': [float(vel[0]), float(vel[-1])],
        'line_depth': max_depth,
        'line_ew_kms': ew_kms,
        'centroid_kms': centroid_kms,
        'fwhm_kms': fwhm_kms,
        'line_vel_range': [line_vel_min, line_vel_max],
        'snr_I': snr_I,
    }


def _fit_rv_gaussian(vel, specI_Ic, specSigI):
    """Fit a Gaussian to the Stokes I absorption depth profile.

    Returns a dict with fitting results.  'success' is False if the fit fails.
    """
    depth = 1.0 - specI_Ic
    center_guess = float(vel[np.argmax(depth)])
    max_depth = float(np.max(depth))

    try:
        sigma_arg = specSigI if np.any(specSigI > 0) else None
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', OptimizeWarning)
            popt, pcov = curve_fit(
                _gaussian,
                vel,
                depth,
                p0=[max_depth, center_guess, 5.0],
                sigma=sigma_arg,
                absolute_sigma=True,
                maxfev=5000,
            )
        perr = np.sqrt(np.diag(pcov))
        return {
            'center_kms': float(popt[1]),
            'sigma_center_kms': float(perr[1]),
            'depth': float(abs(popt[0])),
            'sigma_kms': float(abs(popt[2])),
            'fwhm_kms': float(2.3548 * abs(popt[2])),
            'success': True,
        }
    except Exception as exc:
        return {
            'center_kms': None,
            'sigma_center_kms': None,
            'depth': None,
            'sigma_kms': None,
            'fwhm_kms': None,
            'success': False,
            'error': str(exc),
        }


def _null_test(vel, specV, specSigV, specN1, specSigN1, i_in, i_out):
    """Compute null-test chi² and FAP statistics for V and N1.

    Follows the method in lsd_report.nullTest (see docs/algorithm.md §14).
    Returns a dict with statistics.
    """
    # If sigma arrays are all zero the null test is not applicable
    if (not np.any(specSigV > 0) or not np.any(specSigN1 > 0)):
        return {
            'chi2_V_in': None,
            'reduced_chi2_V_in': None,
            'chi2_V_out': None,
            'fap_V_in': None,
            'detection_V': 'not applicable',
            'chi2_N1_in': None,
            'reduced_chi2_N1_in': None,
            'chi2_N1_out': None,
            'fap_N1_in': None,
            'detection_N1': 'not applicable',
            'n_pixels_in': int(len(i_in)),
            'n_pixels_out': int(len(i_out)),
            'line_vel_range': [None, None],
        }

    # Fall-back line region if not identified
    if (len(i_in) == 0):
        i_in = np.arange(len(vel) // 4, 3 * len(vel) // 4)
    if (len(i_out) == 0):
        mask_in = np.zeros(len(vel), dtype=bool)
        mask_in[i_in] = True
        i_out = np.where(~mask_in)[0]

    # Weighted continuum estimate from in-line pixels (same convention as nullTest)
    def _weighted_mean(arr, sig):
        w = 1.0 / np.maximum(sig, 1e-300) ** 2
        return float(np.sum(arr * w) / np.sum(w))

    contV = _weighted_mean(specV[i_in], specSigV[i_in])
    contN1 = _weighted_mean(specN1[i_in], specSigN1[i_in])

    sig_V_in = np.maximum(specSigV[i_in], 1e-300)
    sig_V_out = np.maximum(specSigV[i_out], 1e-300)
    sig_N1_in = np.maximum(specSigN1[i_in], 1e-300)
    sig_N1_out = np.maximum(specSigN1[i_out], 1e-300)

    chi2_V_in = float(np.sum(((specV[i_in] - contV) / sig_V_in) ** 2))
    chi2_V_out = float(np.sum(((specV[i_out] - contV) / sig_V_out) ** 2))
    chi2_N1_in = float(np.sum(((specN1[i_in] - contN1) / sig_N1_in) ** 2))
    chi2_N1_out = float(np.sum(((specN1[i_out] - contN1) / sig_N1_out) ** 2))

    dof_in = float(max(len(i_in) - 1, 1))
    dof_out = float(max(len(i_out) - 1, 1))

    prob_V_in = float(specialf.gammainc(dof_in / 2.0, chi2_V_in / 2.0))
    prob_N1_in = float(specialf.gammainc(dof_in / 2.0, chi2_N1_in / 2.0))

    fap_V_in = 1.0 - prob_V_in
    fap_N1_in = 1.0 - prob_N1_in

    def _label(fap):
        # Donati et al. (1997) detection criteria — see docs/physics.md §7
        if (fap < _FAP_DEFINITE):
            return 'definite'
        elif (fap < _FAP_MARGINAL):
            return 'marginal'
        return 'non-detection'

    return {
        'chi2_V_in': chi2_V_in,
        'reduced_chi2_V_in': chi2_V_in / dof_in,
        'chi2_V_out': chi2_V_out,
        'fap_V_in': fap_V_in,
        'detection_V': _label(fap_V_in),
        'chi2_N1_in': chi2_N1_in,
        'reduced_chi2_N1_in': chi2_N1_in / dof_in,
        'chi2_N1_out': chi2_N1_out,
        'fap_N1_in': fap_N1_in,
        'detection_N1': _label(fap_N1_in),
        'n_pixels_in': int(len(i_in)),
        'n_pixels_out': int(len(i_out)),
        'line_vel_range': [float(vel[i_in[0]]), float(vel[i_in[-1]])] if len(i_in) > 0 else [None, None],
    }


def _magnetic_field(vel, depth, specV, specSigV, norm_wave_nm, norm_lande):
    """Compute mean longitudinal magnetic field Bl via the first moment of V.

    Bl [G] = -2.14e11 * int(v V dv) / (g_eff * lambda_A * c * int((1-I) dv))

    lambda_A: norm_wave_nm converted to Angstroms (×10).
    c       : speed of light in km/s.

    Error propagation uses only the sigma_V contribution (dominant term).
    See docs/physics.md §7 and Donati et al. 1997.
    """
    lambda_A = norm_wave_nm * 10.0  # nm → Angstrom
    g_eff = norm_lande

    num = float(_trapz(vel * specV, vel))
    denom = float(_trapz(depth, vel))

    if (abs(denom) < _MIN_SIGMA_V):
        return {
            'Bl_gauss': None,
            'sigma_Bl_gauss': None,
            'has_stokes_v': True,
            'error': 'Line depth integral is near zero; cannot compute Bl.',
        }

    Bl = -_BL_COEFF * num / (g_eff * lambda_A * c * denom)

    # Error from sigma_V (trapezoidal rule: dnum/dV_i ≈ v_i * dv)
    dv = float(abs(np.median(np.diff(vel))))
    dBl_dV = (-_BL_COEFF * vel * dv) / (g_eff * lambda_A * c * denom)
    sigma_Bl = float(np.sqrt(np.sum((dBl_dV * specSigV) ** 2)))

    return {
        'Bl_gauss': float(Bl),
        'sigma_Bl_gauss': sigma_Bl,
        'has_stokes_v': True,
    }


def analyze_profile(profile_file, norm_wave_nm=500.0, norm_lande=1.2):
    """Run the LSD basic analysis framework on a saved profile file.

    Parameters
      profile_file  : path to the LSD profile .dat file
      norm_wave_nm  : normalisation wavelength in nm  (used for Bl)
      norm_lande    : effective Landé g-factor         (used for Bl)

    Returns a dict with keys:
      'profile'        — profile statistics
      'rv_fit'         — Gaussian RV fit results
      'noise'          — null-test chi² / FAP / detection labels
      'magnetic_field' — Bl result (only present when V data are non-trivial)
    """
    p = load_lsd_profile(profile_file)
    vel = p['vel']
    specI_Ic = p['specI_Ic']
    specSigI = p['specSigI']
    specV = p['specV']
    specSigV = p['specSigV']
    specN1 = p['specN1']
    specSigN1 = p['specSigN1']
    depth = 1.0 - specI_Ic

    # Identify in-line / out-of-line velocity pixels
    i_in, i_out = _estimate_line_region(specI_Ic, specSigI)

    result = {
        'profile': _profile_stats(vel, specI_Ic, specSigI, i_in),
        'rv_fit': _fit_rv_gaussian(vel, specI_Ic, specSigI),
        'noise': _null_test(vel, specV, specSigV, specN1, specSigN1, i_in, i_out),
    }

    # Include Bl only when Stokes V data are present (non-trivial)
    has_stokes_v = bool(np.any(specSigV > _MIN_SIGMA_V))
    if (has_stokes_v):
        result['magnetic_field'] = _magnetic_field(
            vel, depth, specV, specSigV, norm_wave_nm, norm_lande)

    return result
