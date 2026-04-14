import sys
import numpy as np
import scipy.constants
from pathlib import Path

c = scipy.constants.c * 1e-3

# Spectrum types that are already LSD profiles — cannot be used as input.
_LSD_TYPES = {'lsd_pol', 'lsd_i', 'lsd_i_simple'}


def classify_spectrum(fname):
    """Classify a spectrum file by column count and first-column range.

    Returns one of: 'spec_pol', 'spec_harps', 'spec_i', 'spec_i_simple',
                    'lsd_pol', 'lsd_i', 'lsd_i_simple', 'unknown'.

    Heuristic (mirrors utils_spectrum_viewer._heuristic_guess):
      - 15 cols → spec_harps
      - 6  cols → spec_pol  (Wav, Int, Pol, Null1, Null2, sigma)
      - 7  cols → lsd_pol   (RV, Int, Pol, Null1, Null2, sigI, sigV)
      - 3/2 cols → first-column range decides wavelength vs. velocity
    The first numeric 2-column row is treated as a metadata header (nLines,
    stokes_code) and skipped.
    """
    with open(fname, 'r') as fh:
        raw_lines = [ln for ln in fh if not ln.lstrip().startswith('*')]

    numeric_rows = []
    for ln in raw_lines:
        parts = ln.strip().split()
        if not parts:
            continue
        try:
            numeric_rows.append([float(p) for p in parts])
        except ValueError:
            continue
        if len(numeric_rows) >= 10:
            break

    if len(numeric_rows) < 2:
        return 'unknown'

    # Skip the 2-column metadata line (nLines stokes_code).
    start = 1 if len(numeric_rows[0]) == 2 else 0
    data_rows = numeric_rows[start:start + 5]
    if not data_rows:
        return 'unknown'

    ncol = len(data_rows[0])
    if ncol == 15:
        return 'spec_harps'
    if ncol == 6:
        return 'spec_pol'
    if ncol == 7:
        return 'lsd_pol'

    if ncol in (2, 3):
        x_vals = [row[0] for row in data_rows]
        xmin, xmax = min(x_vals), max(x_vals)
        is_wav = (xmin >= 200) and (xmax <= 5000)
        is_rv = (xmin < 0) or (abs(xmin) <= 10000 and abs(xmax) <= 10000
                               and xmax < 200)
        if ncol == 3:
            return 'spec_i' if is_wav else ('lsd_i' if is_rv else 'unknown')
        return 'spec_i_simple' if is_wav else (
            'lsd_i_simple' if is_rv else 'unknown')

    return 'unknown'


class observation:

    def __init__(self, fname):
        spec_type = classify_spectrum(fname)
        if spec_type in _LSD_TYPES:
            print('ERROR: input file "{}" is already an LSD profile '
                  '(detected type: {}).'.format(fname, spec_type))
            print('LSD cannot be run on an existing LSD profile. '
                  'Please provide a raw spectrum.')
            sys.exit(1)
        if spec_type == 'spec_harps':
            print('ERROR: HARPS multi-order format (15 columns) is not '
                  'supported. Please convert to a 6-column spectrum first.')
            sys.exit(1)
        if spec_type == 'unknown':
            print(
                'WARNING: could not classify "{}" — proceeding anyway.'.format(
                    fname))

        # Manual line-by-line read (~4x faster than np.loadtxt for large echelle files).
        fObs = open(fname, 'r')
        nLines = 0
        fObs.readline()
        fObs.readline()
        for line in fObs:
            words = line.split()
            if (nLines == 0):
                ncolumns = len(words)
                if (ncolumns != 6):
                    if (ncolumns == 3):
                        print('Apparent Stokes I only spectrum')
                        print('Generating place holder V and N columns')
                    else:
                        print('{:} column spectrum: unknown format!'.format(
                            ncolumns))
                        sys.exit()
            if len(words) == ncolumns:
                if ncolumns == 6:
                    if (float(words[1]) > 0. and float(words[5]) > 0.):
                        nLines += 1
                elif ncolumns == 3:
                    if (float(words[1]) > 0. and float(words[2]) > 0.):
                        nLines += 1
            else:
                print(
                    'ERROR: reading observation, line {:}, {:} columns :\n{:}'.
                    format(nLines, len(words), line))

        self.wlOrig = np.zeros(nLines)
        self.specIOrig = np.zeros(nLines)
        self.specVOrig = np.zeros(nLines)
        self.specN1Orig = np.zeros(nLines)
        self.specN2Orig = np.zeros(nLines)
        self.specSigOrig = np.zeros(nLines)

        i = 0
        #rewind to start then advance the file pointer 2 lines
        fObs.seek(0)
        fObs.readline()
        fObs.readline()
        for line in fObs:
            words = line.split()
            if (len(words) == ncolumns and ncolumns == 6):
                if (float(words[1]) > 0. and float(words[5]) > 0.):
                    self.wlOrig[i] = float(words[0])
                    self.specIOrig[i] = float(words[1])
                    self.specVOrig[i] = float(words[2])
                    self.specN1Orig[i] = float(words[3])
                    self.specN2Orig[i] = float(words[4])
                    self.specSigOrig[i] = float(words[5])
                    i += 1
            elif (len(words) == ncolumns and ncolumns == 3):
                if (float(words[1]) > 0. and float(words[2]) > 0.):
                    self.wlOrig[i] = float(words[0])
                    self.specIOrig[i] = float(words[1])
                    self.specSigOrig[i] = float(words[2])
                    self.specVOrig[i] = 0.
                    self.specN1Orig[i] = 0.
                    self.specN2Orig[i] = 0.
                    i += 1

        fObs.close()

        self.ind = np.argsort(self.wlOrig)

        self.wl = self.wlOrig[self.ind]
        self.specI = self.specIOrig[self.ind]
        self.specV = self.specVOrig[self.ind]
        self.specN1 = self.specN1Orig[self.ind]
        self.specN2 = self.specN2Orig[self.ind]
        self.specSig = self.specSigOrig[self.ind]
        self.nPixUsed = 0

    def setInRange(self, mask, prof):
        # Keep only observed pixels covered by at least one mask line.
        # Uses an extra 1-pixel buffer on each side of the profile velocity range.
        # See docs/algorithm.md §12 for the searchsorted approach.
        velStart = prof.vel[0] + (prof.vel[0] - prof.vel[1])
        velEnd = prof.vel[-1] + (prof.vel[-1] - prof.vel[-2])

        wlSort = np.sort(mask.wl)
        maskWlLow = wlSort + velStart / c * wlSort
        maskWlHigh = wlSort + velEnd / c * wlSort

        indNearestStart = np.searchsorted(maskWlLow, self.wl, side='left')
        indNearestEnd = np.searchsorted(maskWlHigh, self.wl, side='right')
        maskuse = (indNearestStart > indNearestEnd)

        self.wl = self.wl[maskuse]
        self.specI = self.specI[maskuse]
        self.specV = self.specV[maskuse]
        self.specN1 = self.specN1[maskuse]
        self.specN2 = self.specN2[maskuse]
        self.specSig = self.specSig[maskuse]

        if (self.wl.shape[0] <= 0):
            print(
                'ERROR: no lines in mask in wavelength range of observation!')

        return

    def sigmaClipI(self, prof, MI, sigmaLim):

        ptsBefore = self.wl.shape[0]
        modelSpecI = MI.dot(prof.specI)
        maskuse = (np.abs(self.specI - modelSpecI) / self.specSig < sigmaLim)

        self.wl = self.wl[maskuse]
        self.specI = self.specI[maskuse]
        self.specV = self.specV[maskuse]
        self.specN1 = self.specN1[maskuse]
        self.specN2 = self.specN2[maskuse]
        self.specSig = self.specSig[maskuse]
        ptsAfter = self.wl.shape[0]

        print('sigma clip rejecting {:n} points of {:n}'.format(
            ptsBefore - ptsAfter, ptsBefore))

        return


class mask:

    def __init__(self, fname):
        # 6 columns: wavelength(nm), element+ion*0.01, depth, excitation_pot, lande_g, use_flag
        # See docs/architecture.md for full column description.
        tmpMask = np.loadtxt(fname, skiprows=1, unpack=True)

        self.ind = np.argsort(tmpMask[0, :])

        self.wl = tmpMask[0, self.ind]
        self.element = tmpMask[1, self.ind]
        self.depth = tmpMask[2, self.ind]
        self.excite = tmpMask[3, self.ind]
        self.lande = tmpMask[4, self.ind]
        self.iuse = tmpMask[5, self.ind].astype(int)

        ind2 = np.where(self.iuse != 0)
        self.wl = self.wl[ind2]
        self.element = self.element[ind2]
        self.depth = self.depth[ind2]
        self.excite = self.excite[ind2]
        self.lande = self.lande[ind2]
        self.iuse = self.iuse[ind2]

    def setWeights(self, params):
        weighting_mode = int(getattr(params, 'weightingMode', 2))

        self.weightI = self.depth / params.normDepth

        if weighting_mode == 0:
            self.weightV = self.lande / params.normLande
        elif weighting_mode == 1:
            self.weightV = self.depth * self.lande / (params.normDepth *
                                                      params.normLande)
        elif weighting_mode == 2:
            self.weightV = self.depth * self.wl * self.lande / (
                params.normDepth * params.normWave * params.normLande)
        elif weighting_mode == 3:
            self.weightV = self.depth / params.normDepth
        elif weighting_mode == 4:
            self.weightV = self.depth * self.wl / (params.normDepth *
                                                   params.normWave)
        elif weighting_mode == 5:
            self.weightV = np.ones_like(self.depth)
        elif weighting_mode == 6:
            self.weightV = self.depth * (self.wl * self.lande)**2 / (
                params.normDepth * (params.normWave * params.normLande)**2)
        elif weighting_mode == 7:
            # Fixed threshold weighting (C-version style, high-noise robust)
            # Binary: low weight for deep lines, high weight otherwise
            threshold = getattr(params, 'weightingThreshold', 0.5)
            low_val = getattr(params, 'weightingLowValue', 0.1)
            high_val = getattr(params, 'weightingHighValue', 10.0)

            norm_depth = self.depth / params.normDepth

            # Apply binary weighting for I and V
            self.weightI = np.where(norm_depth < threshold, low_val, high_val)
            self.weightV = np.where(norm_depth < threshold, low_val, high_val)

            print(
                f'INFO: Using fixed threshold weighting (mode 7): threshold={threshold:.3f}, '
                f'low_weight={low_val:.3f}, high_weight={high_val:.3f}')
        else:
            print(
                'WARNING: unknown weighting mode {:}, fallback to mode 2 (lam*prof*g)'
                .format(weighting_mode))
            self.weightV = self.depth * self.wl * self.lande / (
                params.normDepth * params.normWave * params.normLande)

        # Saturation correction: down-weight lines in crowded ±5 km/s regions.
        # If total depth of all lines within window > 1, scale weights by 1/sum_all.
        # See docs/physics.md §5.
        c_speed = 299792.0  # km/s
        for i in range(len(self.wl)):
            delta_wl = self.wl[i] * 5.0 / c_speed
            in_window = ((self.wl > self.wl[i] - delta_wl) &
                         (self.wl < self.wl[i] + delta_wl))
            sum_all = np.sum(self.depth[in_window])
            if sum_all > 1.0:
                self.weightI[i] *= (1.0 / sum_all)
                self.weightV[i] *= (1.0 / sum_all)

        return

    def filterLines(self, obs, prof, verbose=True):
        # Remove lines in telluric bands and lines not fully covered by observation.
        # See docs/physics.md §6 and docs/algorithm.md §12.
        initial_count = len(self.wl)
        keep_mask = np.ones(initial_count, dtype=bool)
        c_speed = 299792.458  # km/s

        # 1. Telluric Rejection
        # Ranges from line_noplot.c: wtl/wtu (nm)
        # {627, 686, 716, 759, 813, 895} to {632, 697, 734, 770, 835, 986}
        tellurics = [(627.0, 632.0), (686.0, 697.0), (716.0, 734.0),
                     (759.0, 770.0), (813.0, 835.0), (895.0, 986.0)]

        num_telluric = 0
        for w_min, w_max in tellurics:
            # Check for lines within telluric bands
            in_telluric = (self.wl >= w_min) & (self.wl <= w_max)
            count = np.sum(in_telluric & keep_mask)
            if count > 0:
                keep_mask[in_telluric] = False
                num_telluric += count

        if verbose and num_telluric > 0:
            print(f"Telluric rejection: removed {num_telluric} lines.")

        # 2. Coverage rejection: gaps > 50× median pixel spacing mark order boundaries.
        wl_sep = np.diff(obs.wl)
        median_sep = np.median(wl_sep)
        gap_indices = np.where(wl_sep > 50 * median_sep)[0]

        segments = []
        last_idx = 0
        for gap_idx in gap_indices:
            segments.append((obs.wl[last_idx], obs.wl[gap_idx]))
            last_idx = gap_idx + 1
        segments.append((obs.wl[last_idx], obs.wl[-1]))

        velStart = prof.vel[0]
        velEnd = prof.vel[-1]

        line_min_req = self.wl * (1.0 + velStart / c_speed)
        line_max_req = self.wl * (1.0 + velEnd / c_speed)

        is_covered = np.zeros(initial_count, dtype=bool)
        for seg_min, seg_max in segments:
            covered_in_this_seg = (segment_min_check := (line_min_req >= seg_min)) & \
                                  (segment_max_check := (line_max_req <= seg_max))
            is_covered |= covered_in_this_seg

        not_covered_count = np.sum((~is_covered) & keep_mask)
        keep_mask &= is_covered

        if verbose:
            if not_covered_count > 0:
                print(
                    f"Coverage rejection: removed {not_covered_count} lines (partial/off-edge)."
                )
            print(
                f"Final mask: {np.sum(keep_mask)} lines used (of {initial_count})."
            )

        # Apply filtering
        self.wl = self.wl[keep_mask]
        self.element = self.element[keep_mask]
        self.depth = self.depth[keep_mask]
        self.excite = self.excite[keep_mask]
        self.lande = self.lande[keep_mask]
        self.iuse = self.iuse[keep_mask]

        # Filter weights if they exist
        if hasattr(self, 'weightI'):
            self.weightI = self.weightI[keep_mask]
        if hasattr(self, 'weightV'):
            self.weightV = self.weightV[keep_mask]


class prof:

    def __init__(self, params):
        self.vel = np.arange(
            params.velStart,
            params.velEnd + params.pixVel,
            params.pixVel,
        )
        self.npix = self.vel.shape[0]
        self.specI = np.ones(self.npix)
        self.specSigI = np.zeros(self.npix)
        self.specV = np.zeros(self.npix)
        self.specSigV = np.zeros(self.npix)
        self.specN1 = np.zeros(self.npix)
        self.specSigN1 = np.zeros(self.npix)
        self.specN2 = np.zeros(self.npix)
        self.specSigN2 = np.zeros(self.npix)

    def save(self, fname):
        # finally convert I from 1-I to full I/Ic units at output
        out_path = Path(fname)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        oFile = open(fname, 'w')
        starName = 'STAR'
        oFile.write('***Reduced spectrum of \'{:<8s}\'\n'.format(starName))
        oFile.write(' {:d} 6\n'.format(self.npix))
        for i in range(self.npix):
            oFile.write(
                '{:>12.6f} {:>13.6e} {:>13.6e} {:>13.6e} {:>13.6e} {:>13.6e} {:>13.6e}\n'
                .format(self.vel[i], 1. - self.specI[i], self.specSigI[i],
                        self.specV[i], self.specSigV[i], self.specN1[i],
                        self.specSigN1[i]))

        oFile.close()

    def lsdplot(self, fname):
        import matplotlib.pyplot as plt

        # Set up axes and put y-axis labels on the right
        fig, (ax1, ax2,
              ax3) = plt.subplots(3,
                                  sharex=True,
                                  gridspec_kw={'height_ratios': [1, 1, 3]})
        ax1.yaxis.set_label_position("right")
        ax2.yaxis.set_label_position("right")
        ax3.yaxis.set_label_position("right")

        # y-axis limits for V and N so on same scale - 1.05 time biggest divergence from zero
        plotVLims = np.max([
            np.abs(1.05 * np.min(self.specV)),
            np.abs(1.05 * np.max(self.specV)),
            np.abs(1.05 * np.min(self.specN1)),
            np.abs(1.05 * np.max(self.specN1)), 1.05 * np.max(self.specSigV)
        ])

        # Plot V - errorbars and data.  Setting limits to max/min vel and y-axis limit above
        ax1.errorbar(self.vel,
                     self.specV,
                     yerr=self.specSigV,
                     fmt='none',
                     ecolor='r',
                     alpha=0.4)
        ax1.scatter(self.vel, self.specV, marker='.', c='r')
        ax1.plot([np.min(self.vel), np.max(self.vel)], [0., 0.],
                 'k--',
                 alpha=0.5)
        ax1.set_xlim(xmin=np.min(self.vel), xmax=np.max(self.vel))
        ax1.set_ylim(ymin=-plotVLims, ymax=plotVLims)
        ax1.set_ylabel('$V/I_c$')

        # Plot N1 - errorbars and data.  Setting limits to max/min vel and y-axis limit above
        ax2.errorbar(self.vel,
                     self.specN1,
                     yerr=self.specSigN1,
                     fmt='none',
                     ecolor='m',
                     alpha=0.4)
        ax2.scatter(self.vel, self.specN1, marker='.', c='m')
        ax2.plot([np.min(self.vel), np.max(self.vel)], [0., 0.],
                 'k--',
                 alpha=0.5)
        ax2.set_ylabel('$N/I_c$')
        ax2.set_xlim(xmin=np.min(self.vel), xmax=np.max(self.vel))
        ax2.set_ylim(ymin=-plotVLims, ymax=plotVLims)

        #Optionally, plot smoothed versions of V and N1
        try:
            # Import smoothing filter
            from scipy.signal import savgol_filter
            # Apply Savitzky-Golay smoothing filter to V & N (window=9, order=5 - just random!)
            plotVhat = savgol_filter(self.specV, 9, 5)
            plotNhat = savgol_filter(self.specN1, 9, 5)
            ax1.plot(self.vel,
                     plotVhat,
                     'r',
                     lw=1.2,
                     label='Circular Polarisation')
            ax2.plot(self.vel,
                     plotNhat,
                     'm',
                     lw=1.2,
                     label='Null Polarisation Check')
        except:
            plotVhat = self.specV
            plotNhat = self.specN1

        # Plot I - errorbars and data.  Only setting x-limits
        ax3.errorbar(self.vel,
                     1. - self.specI,
                     yerr=self.specSigI,
                     fmt='none',
                     ecolor='b',
                     alpha=0.4)
        ax3.plot(self.vel,
                 1. - self.specI,
                 'b',
                 lw=1.2,
                 label='Unpolarised Line Profile')
        ax3.set_ylabel('$I/I_c$')
        ax3.set_xlabel('Velocity $(km s^{-1})$')
        ax3.plot([np.min(self.vel), np.max(self.vel)], [1., 1.],
                 'k--',
                 alpha=0.5)
        ax3.set_xlim(xmin=np.min(self.vel), xmax=np.max(self.vel))

        # fig.tight_layout()
        if fname != '':
            plt.savefig(fname)
        plt.show()
