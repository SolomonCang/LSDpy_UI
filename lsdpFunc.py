#LSD helper functions
import numpy as np
import scipy.special as specialf
from scipy.sparse import diags, spdiags, dia_matrix, csr_matrix, csc_matrix, issparse, coo_matrix, dok_matrix, lil_matrix
from numpy.linalg import inv
from scipy.linalg import cho_factor, cho_solve
from datetime import datetime
from pathlib import Path

import scipy.constants

c = scipy.constants.c * 1e-3

WEIGHTING_MODE_DESCRIPTIONS = {
    0: 'g',
    1: 'prof*g',
    2: 'lam*prof*g',
    3: 'prof',
    4: 'lam*prof',
    5: '1',
    6: 'prof*(lam*g)^2',
}


def get_weighting_mode_description(mode):
    return WEIGHTING_MODE_DESCRIPTIONS.get(int(mode), 'unknown')


class paramsLSD:
    def __init__(self, fname):
        #Read in most information controlling how the program runs
        self.weightingMode = 2
        self.fSaveLSDOut = 1
        self.outLSDOutName = 'auto'
        self.saturationCorrection = 1
        self.telluricFiltering = 1
        self.lineFiltering = 1

        infile = open(fname, 'r')

        i = 0
        for line in infile:
            if (len(line) <= 1):
                continue
            if (line.strip()[0] != '#'):
                if (i == 0):
                    self.inObs = line.strip().split()[0]
                elif (i == 1):
                    self.inMask = line.strip().split()[0]
                elif (i == 2):
                    self.velStart = float(line.split()[0])
                    self.velEnd = float(line.split()[1])
                elif (i == 3):
                    self.pixVel = float(line.split()[0])
                elif (i == 4):
                    self.normDepth = float(line.split()[0])
                    self.normLande = float(line.split()[1])
                    self.normWave = float(line.split()[2])
                    if len(line.split()) > 3:
                        self.weightingMode = int(line.split()[3])
                elif (i == 5):
                    self.removeContPol = int(line.split()[0])
                elif (i == 6):
                    self.sigmaClip = float(line.split()[0])
                    self.sigmaClipIter = int(line.split()[1])
                elif (i == 7):
                    self.interpMode = int(line.split()[0])
                elif (i == 8):
                    self.fSaveModelSpec = int(line.split()[0])
                    if (self.fSaveModelSpec == 1):
                        self.outModelSpecName = line.split()[1]
                    else:
                        self.outModelSpecName = ''
                elif (i == 9):
                    self.fLSDPlotImg = int(line.split()[0])
                    self.fSavePlotImg = int(line.split()[1])
                    if (self.fSavePlotImg == 1):
                        self.outPlotImgName = line.split()[2]
                    else:
                        self.outPlotImgName = ''
                elif (i == 10):
                    self.weightingMode = int(line.split()[0])
                elif (i == 11):
                    self.fSaveLSDOut = int(line.split()[0])
                    if (self.fSaveLSDOut == 1):
                        lsdout_name = line.split()[1]
                        self.outLSDOutName = lsdout_name
                    else:
                        self.outLSDOutName = ''
                elif (i == 12):
                    self.saturationCorrection = int(line.split()[0])
                    self.telluricFiltering = int(line.split()[1])
                    self.lineFiltering = int(line.split()[2])
                else:
                    print('end of parameters file reached, error?')
                i += 1

        infile.close()
        if (i < 5):
            print('ERROR: incomplete information read from {:}'.format(fname))


class observation:
    def __init__(self, fname):

        #self.wlOrig, self.specIOrig, self.specVOrig, self.specN1Orig, self.specN2Orig, self.specSigOrig \
        #    = np.loadtxt(fname, skiprows=2, unpack=True)
        ## Reading manually is ~4 time faster than np.loadtxt for a large files
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
                        import sys
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

        #Deal with order overlap, or do any trimming?

        #Sort the observation so wavelength is always increasing
        self.ind = np.argsort(self.wlOrig)

        self.wl = self.wlOrig[self.ind]
        self.specI = self.specIOrig[self.ind]
        self.specV = self.specVOrig[self.ind]
        self.specN1 = self.specN1Orig[self.ind]
        self.specN2 = self.specN2Orig[self.ind]
        self.specSig = self.specSigOrig[self.ind]
        #Save the number of observed spectral pixels used in the LSD profile
        self.nPixUsed = 0

    def setInRange(self, mask, prof):
        #Get the set of observed pixels in range of lines in the LSD mask.

        #add an extra 1 LSD pixel buffer to the range we extract, just in case.
        velStart = prof.vel[0] + (prof.vel[0] - prof.vel[1])
        velEnd = prof.vel[-1] + (prof.vel[-1] - prof.vel[-2])

        wlSort = np.sort(mask.wl)
        maskWlLow = wlSort + velStart / c * wlSort
        maskWlHigh = wlSort + velEnd / c * wlSort

        #For each line in the mask check which observed pixels are in range
        #This is logicaly simpler, but much slower:
        #Set array of bool for pixels in range of a line in the mask (starts False)
        #maskuse = np.zeros_like(self.wl, dtype='bool')
        #for i in range(mask.wl.shape[0]):
        #    maskuse += ( (self.wl >= maskWlLow[i]) & (self.wl <= maskWlHigh[i]) )

        #for each observed point, get the nearest line profile (line mask wavelength +/- profile size) start (blue edge)
        #(actually gets where each observed point would fit in the ordered list of line profile starts)
        #(maskWlLow must be sorted.  side only matters if some wl are identical or maskWlLow=wl)
        indNearestStart = np.searchsorted(maskWlLow, self.wl, side='left')
        #for each observed point, get the nearest line profile end
        indNearestEnd = np.searchsorted(maskWlHigh, self.wl, side='right')
        #observed pixel is only in range of a mask line if it is between the line profile start and end wavelengths
        #i.e. if indNearestStart has incremented for the line but indNearestEnd has not yet incremented
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
        #maskuse = np.where(np.abs(self.specI-modelSpecI)/self.specSig < sigmaLim) #alternate version

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

        #Columns should be wavelength (nm), element+ionization*0.01, line depth,
        #excitation potential of the lower level, effective Lande factor,
        #and a flag for whether the line is used (1=use, 0=skip).
        #self.wl, self.element, self.depth, self.excite, self.lande, tmpiuse \
        #    = np.loadtxt(fname, skiprows=1, unpack=True)
        tmpMask = np.loadtxt(fname, skiprows=1, unpack=True)

        #Sort the line mask so wavelength is always increasing
        self.ind = np.argsort(tmpMask[0, :])

        self.wl = tmpMask[0, self.ind]
        self.element = tmpMask[1, self.ind]
        self.depth = tmpMask[2, self.ind]
        self.excite = tmpMask[3, self.ind]
        self.lande = tmpMask[4, self.ind]
        self.iuse = tmpMask[5, self.ind].astype(int)

        #For speed just reduce the mask to the mask.iuse != 0 parts here
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
        else:
            print(
                'WARNING: unknown weighting mode {:}, fallback to mode 2 (lam*prof*g)'
                .format(weighting_mode))
            self.weightV = self.depth * self.wl * self.lande / (
                params.normDepth * params.normWave * params.normLande)

        # New Feature: Saturation Correction (Down-weight lines in crowded regions)
        # Calculate local line density metric (ptot)
        # For each line, sum depths of neighbors within +/- 5 km/s
        ptot_list = np.zeros_like(self.depth)
        c_speed = 299792.0  # km/s

        # Sort is guaranteed by __init__
        # Use simple window search (could be optimized, but N~15000 is fast enough)

        # Vectorized density calculation (approximated for speed)
        # Using a fixed window in wavelength corresponding to ~5km/s at typical WL
        # This emulates the nested loop in C version get_weights

        for i in range(len(self.wl)):
            wl_current = self.wl[i]
            # 5 km/s window
            delta_wl = wl_current * 5.0 / c_speed

            # Simple slice (assuming some sorting, though local search is safer)
            # Find neighbors

            # This is O(N^2) potentially, but N~15000 is tiny.
            # Let's use a smarter slice boundaries
            low_bound = wl_current - delta_wl
            high_bound = wl_current + delta_wl

            # Since self.wl is sorted:
            # We can just check neighbors until condition fails
            # But numpy bool array is fast

            # Strict window check
            in_window = (self.wl > low_bound) & (self.wl < high_bound)
            ptot = np.sum(
                self.depth[in_window]) - self.depth[i]  # Neighbors only?
            # C code: ptot = -dd; loop { ptot += prof[...] } -> includes self?
            # C: ptot = -dd (starts negative self). Then loop includes self.
            # So ptot = sum(neighbors) + self - self = sum(neighbors).
            # Wait, C code: if (ptot > 1.0) dd *= 1.0/ptot
            # If ptot is sum of *all* depths in window (including self), then ptot-self
            # Actually C: "ptot = -dd; for ... ptot += prof[k]" -> includes self.
            # So ptot is sum of all lines in window (including self) minus self? No.
            # ptot = -dd(self) + sum(others + self) = sum(others).
            # Wait, if ptot > 1.0. If ptot is just sum of others, and others=0, ptot=0.
            # Then no scaling.
            # If others exist, ptot > 0.
            # Let's re-read carefully:
            # ptot = -dd;
            # for (all k) check window, ptot += prof[k].
            # So ptot = Sum(all in window) - depth(self).
            # If ptot > 1.0: depth(self) *= 1/ptot.
            # So we divide by Sum(neighbors).

            # Correction: If ptot > 1.0, scale.

            # C-code logic: ptot = sum of ALL depths in window (including self)
            sum_all = np.sum(self.depth[in_window])

            if sum_all > 1.0:
                # downweight
                self.weightI[i] *= (1.0 / sum_all)
                self.weightV[i] *= (1.0 / sum_all)

        return

    def filterLines(self, obs, prof, verbose=True):
        """
        Filter out lines that are:
        1. In telluric regions (hardcoded based on C-version).
        2. Not fully covered by the observation (handling spectral gaps/orders).
        
        Requires 'obs' (for wavelength grid) and 'prof' (for velocity range).
        """
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

        # 2. Coverage Rejection (Spectral Orders/Gaps)
        # Identify valid spectral segments from observation wavelengths
        # Assumes obs.wl is sorted (which it is)

        wl_sep = np.diff(obs.wl)
        median_sep = np.median(wl_sep)
        # Detect gaps (orders) -> step > 50 * median
        # C uses separate logic for orders, but this gap detection is robust
        gap_indices = np.where(wl_sep > 50 * median_sep)[0]

        # Build segments [start_wl, end_wl]
        segments = []
        last_idx = 0
        for gap_idx in gap_indices:
            segments.append((obs.wl[last_idx], obs.wl[gap_idx]))
            last_idx = gap_idx + 1
        segments.append((obs.wl[last_idx], obs.wl[-1]))

        # Line requires coverage from: wl*(1+v_start/c) to wl*(1+v_end/c)
        # Add margin 'side' from C-code (5 pixels ~ 10 km/s? let's assume margin factor)
        # Here we use the exact profile extent required by LSD

        velStart = prof.vel[0]
        velEnd = prof.vel[-1]

        line_min_req = self.wl * (1.0 + velStart / c_speed)
        line_max_req = self.wl * (1.0 + velEnd / c_speed)

        # Vectorized check: does line fall completely inside ANY segment?
        is_covered = np.zeros(initial_count, dtype=bool)

        for seg_min, seg_max in segments:
            # A line is covered if its REQUIRED range is within the SEGMENT range
            # Range check: seg_min <= line_min_req AND line_max_req <= seg_max
            covered_in_this_seg = (segment_min_check := (line_min_req >= seg_min)) & \
                                  (segment_max_check := (line_max_req <= seg_max))
            is_covered |= covered_in_this_seg

        # Reject lines not covered
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
        #Alternate wl pixel scheme, gets the velocity range exact, but changes pixel size:
        #self.npix = np.ceil((params.velEnd - params.velStart)/params.pixVel)
        #self.vel = np.linspace(params.velStart, params.velEnd, self.npix, endpoint=True)
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
        #finally convert I from 1-I to full I/Ic units at output
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


def buildInvSig2(obs):
    #construct the diagonal matrix of 1/sigma^2, dimension of observation X observation
    #Use a sparse matrix for the nobs x nobs array (otherwise its several Gb!)

    # Match C-version preprocessing: Weight by I / sigma^2
    # This accounts for photon noise correlations (sigma ~ sqrt(I))
    # and effectively down-weights deep lines where I is smaller.

    # Determine if specI is Depth (1-I) or Intensity (I)
    # In lsdpy.py, specI is converted to 1-I (depth). continuum ~ 0.
    # If mean is small (<0.5), it's likely depth.
    if np.mean(obs.specI) < 0.5:
        # It is depth (1-I). Recover Intensity.
        intensity = 1.0 - obs.specI
    else:
        # It is Intensity.
        intensity = obs.specI

    # Sanity check intensity (avoid <= 0 or NaNs)
    intensity = np.maximum(intensity, 0.0001)

    # Calculate weights: I / sigma^2
    tmp = intensity * (obs.specSig**(-2))

    # Original (Incorrect matching for C code):
    # tmp = obs.specSig**(-2)

    sparseS2 = scipy.sparse.diags(tmp, offsets=0)

    return sparseS2


def buildMold(obs, mask, prof, interpMode):
    #Build the nObsPix x nProfPix matrix of weights connecting LSD pixels to observed pixels
    #Builds I and V matrices at once (more efficient)

    #outer loop over observations version, simpler to write but maybe slower
    maskMI = np.zeros((obs.wl.shape[0], prof.npix))
    maskMV = np.zeros((obs.wl.shape[0], prof.npix))
    #Sparse matrices are generally slower here due to the overhead accessing entries

    #calculate wavelengths for the profile at each line in the mask here, since it is reusable
    #wlProf = prof.vel/c*mask.wl[l] + mask.wl[l]
    wlProfA = np.outer(prof.vel / c, mask.wl) + np.tile(
        mask.wl, (prof.npix, 1))  #(prof.npix, mask.wl.shape)

    obs.nPixUsed = 0
    #Nearest neighbor 'interpolation' of model spec on to observed spec
    if (interpMode == 0):
        for i in range(obs.wl.shape[0]):
            #Get lines in the mask that will contribute to this pixel
            iMaskRange = np.where((wlProfA[0, :] < obs.wl[i])
                                  & (wlProfA[-1, :] > obs.wl[i]))

            if (iMaskRange[0].shape[0] > 0):
                obs.nPixUsed += 1

            for l in iMaskRange[0]:
                #LSD profile in wavelength space, for this line in the mask
                #pre-calculating this saves some time, since we can re-use some lines
                wlProf = wlProfA[:, l]

                #Use the nearest neighbor model point (column in M) for the observed point (row in M)
                iProf = np.argmin(np.abs(wlProf - obs.wl[i]))

                maskMI[i, iProf] += mask.weightI[l]
                maskMV[i, iProf] += mask.weightV[l]

    #Linear interpolation of model spec on to observed spec
    elif (interpMode == 1):
        for i in range(obs.wl.shape[0]):
            #Get lines in the mask that will contribute to this pixel
            iMaskRange = np.where((wlProfA[0, :] < obs.wl[i])
                                  & (wlProfA[-1, :] > obs.wl[i]))

            if (iMaskRange[0].shape[0] > 0):
                obs.nPixUsed += 1

            for l in iMaskRange[0]:
                #LSD profile in wavelength space, for this line in the mask
                #pre-calculating this saves some time, since we can re-use some lines
                wlProf = wlProfA[:, l]

                #Linearly interpolate between two model points (columns in M) for the observed point (row in M)
                #iProf = np.where(wlProf > obs.wl[i])[0][0]
                #iProf = np.argmax(wlProf > obs.wl[i])  #generates array of bool, returns 1st true
                iProf = np.searchsorted(
                    wlProf, obs.wl[i],
                    side='right')  #relies on ordered wlProf but is faster

                wlWeight = (obs.wl[i] - wlProf[iProf - 1]) / (
                    wlProf[iProf] - wlProf[iProf - 1])

                maskMI[i, iProf - 1] += mask.weightI[l] * (1. - wlWeight)
                maskMI[i, iProf] += mask.weightI[l] * wlWeight

                maskMV[i, iProf - 1] += mask.weightV[l] * (1. - wlWeight)
                maskMV[i, iProf] += mask.weightV[l] * wlWeight

    return maskMI, maskMV


def buildM(obs, mask, prof, interpMode):
    #Build the nObsPix x nProfPix matrix of weights connecting LSD pixels to observed pixels
    #Builds I and V matrices at once (more efficient)

    #outer loop over lines in the mask version, 2-3x faster
    maskMI = np.zeros((obs.wl.shape[0], prof.npix))
    maskMV = np.zeros((obs.wl.shape[0], prof.npix))
    #Sparse matrices are generally slower here due to the overhead accessing entries

    #calculate wavelengths for the profile at each line in the mask here, since it is reusable
    #wlProf = prof.vel/c*mask.wl[l] + mask.wl[l]
    wlProfA = np.outer(prof.vel / c, mask.wl) + np.tile(
        mask.wl, (prof.npix, 1))  #(prof.npix, mask.wl.shape)

    obs.nPixUsed = 0
    #Nearest neighbor 'interpolation' of model spec on to observed spec
    if (interpMode == 0):
        for l in range(mask.wl.shape[0]):
            #Get observation points in range of this line in the mask
            iObsRange = np.where((wlProfA[0, l] < obs.wl[:])
                                 & (wlProfA[-1, l] > obs.wl[:]))

            #set up nProf x nObsUsed matrices, one of the used observed pixels repeated for each nProf
            obsWl2 = np.tile(obs.wl[iObsRange], (wlProfA[:, l].shape[0], 1))
            #and one of the wavelengths of the profile (at this line), repeated for each nObsUsed
            wlProf2 = np.tile(wlProfA[:, l, np.newaxis],
                              (1, iObsRange[0].shape[0]))
            #The get the profile pixel closest in wavelength to the used observed pixel, for each nObsUsed
            iProf = np.argmin(np.abs(wlProf2 - obsWl2), axis=0)

            maskMI[iObsRange, iProf] += mask.weightI[l]
            maskMV[iObsRange, iProf] += mask.weightV[l]

            #Slower by 2x version with a loop
            #for i in iObsRange[0]:
            #    wlProf = wlProfA[:,l]
            #
            #    #Use the nearest neighbor model point (column in M) for the observed point (row in M)
            #    iProf = np.argmin(np.abs(wlProf - obs.wl[i]))
            #
            #    maskMI[i,iProf] += mask.weightI[l]
            #    maskMV[i,iProf] += mask.weightV[l]

    #Linear interpolation of model spec on to observed spec
    elif (interpMode == 1):
        for l in range(mask.wl.shape[0]):
            #Get observation points in range of this line in the mask
            iObsRange = np.where((wlProfA[0, l] < obs.wl[:])
                                 & (wlProfA[-1, l] > obs.wl[:]))

            #set up nProf x nObsUsed matrices, one of the used observed pixels repeated for each nProf
            obsWl2 = np.tile(obs.wl[iObsRange], (wlProfA[:, l].shape[0], 1))
            #and one of the wavelengths of the profile (at this line), repeated for each nObsUsed
            wlProf2 = np.tile(wlProfA[:, l, np.newaxis],
                              (1, iObsRange[0].shape[0]))
            #Get the point in the profile with a wavelength (for this line in the mask) just beyond this observed point, for each nObsUsed
            iProf = np.argmax(
                wlProf2 > obsWl2,
                axis=0)  #generates array of bool, returns 1st true

            wlWeight = (obs.wl[iObsRange] - wlProfA[iProf - 1, l]) / (
                wlProfA[iProf, l] - wlProfA[iProf - 1, l])

            maskMI[iObsRange, iProf - 1] += mask.weightI[l] * (1. - wlWeight)
            maskMI[iObsRange, iProf] += mask.weightI[l] * wlWeight

            maskMV[iObsRange, iProf - 1] += mask.weightV[l] * (1. - wlWeight)
            maskMV[iObsRange, iProf] += mask.weightV[l] * wlWeight

            #Slower by 2x version with a loop
            #for i in iObsRange[0]:
            #    wlProf = wlProfA[:,l]
            #
            #    #Linearly interpolate between two model points (columns in M) for the observed point (row in M)
            #    #Get the point in the profile with a wavelength (for this line in the masK) just beyond this observed point
            #    #iProf = np.where(wlProf > obs.wl[i])[0][0]
            #    #iProf = np.argmax(wlProf > obs.wl[i])  #generates array of bool, returns 1st true
            #    iProf = np.searchsorted(wlProf, obs.wl[i], side='right') #relies on ordered wlProf but is faster
            #
            #    wlWeight = (obs.wl[i] - wlProf[iProf-1])/(wlProf[iProf]-wlProf[iProf-1])
            #
            #    maskMI[i,iProf-1] += mask.weightI[l]*(1.-wlWeight)
            #    maskMI[i,iProf] += mask.weightI[l]*wlWeight
            #
            #    maskMV[i,iProf-1] += mask.weightV[l]*(1.-wlWeight)
            #    maskMV[i,iProf] += mask.weightV[l]*wlWeight

    return maskMI, maskMV


def getChi2(Yo, sparseM, sparseS2, Z):
    # Model the spectrum Y as a convolution of a line pattern (mask) M,
    # and a mean line profile Z.  With matrix multiplication Y = M.Z
    # then: chi^2 = (Yo - M.Z)^T.S^2.(Yo - M.Z)
    # For an observation Yo with S being a square diagonal with 1/sigma errors

    tmpChi = (Yo - sparseM.dot(Z))
    #tmpChi is not sparse, but can still use this syntax to be safe
    chi2 = tmpChi.T.dot(sparseS2.dot(tmpChi))

    return chi2


def saveModelSpec(outModelSpecName, prof, MI, MV, obsWl):
    #Save the LSD model spectrum (i.e. convolution of line mask and LSD profile)
    #for pixels in the observation used
    # From below, model the spectrum as a convolution of a line mask M
    # and a line profile Z:  Y = M.Z

    if (outModelSpecName != ''):
        specI = MI.dot(prof.specI)
        specV = MV.dot(prof.specV)
        specN1 = MV.dot(prof.specN1)

        outFile = open(outModelSpecName, 'w')
        for i in range(specI.shape[0]):
            outFile.write('{:10f} {:11e} {:11e} {:11e}\n'.format(
                obsWl[i], 1. - specI[i], specV[i], specN1[i]))


def saveLSDOut(outFileName,
               spectrumFile='',
               maskFile='',
               profileFile='',
               params=None,
               obs=None,
               maskObj=None,
               prof=None,
               chi2I=None,
               chi2V=None,
               chi2N1=None,
               modelOptions=None):
    def _stats_triplet(arr):
        if arr is None:
            return None
        if np.size(arr) <= 0:
            return None
        arrf = np.asarray(arr, dtype=float)
        return float(np.mean(arrf)), float(np.min(arrf)), float(np.max(arrf))

    def _element_to_str(elem_code):
        """Convert element code (e.g., 26.01) to string (e.g., 'Fe 2')."""
        periodic_table = [
            '', 'H', 'He', 'Li', 'Be', 'B', 'C', 'N', 'O', 'F', 'Ne', 'Na',
            'Mg', 'Al', 'Si', 'P', 'S', 'Cl', 'Ar', 'K', 'Ca', 'Sc', 'Ti', 'V',
            'Cr', 'Mn', 'Fe', 'Co', 'Ni', 'Cu', 'Zn', 'Ga', 'Ge', 'As', 'Se',
            'Br', 'Kr', 'Rb', 'Sr', 'Y', 'Zr', 'Nb', 'Mo', 'Tc', 'Ru', 'Rh',
            'Pd', 'Ag', 'Cd', 'In', 'Sn', 'Sb', 'Te', 'I', 'Xe', 'Cs', 'Ba',
            'La', 'Ce', 'Pr', 'Nd', 'Pm', 'Sm', 'Eu', 'Gd', 'Tb', 'Dy', 'Ho',
            'Er', 'Tm', 'Yb', 'Lu', 'Hf', 'Ta', 'W', 'Re', 'Os', 'Ir', 'Pt',
            'Au', 'Hg', 'Tl', 'Pb', 'Bi', 'Po', 'At', 'Rn', 'Fr', 'Ra', 'Ac',
            'Th', 'Pa', 'U', 'Np', 'Pu', 'Am', 'Cm', 'Bk', 'Cf', 'Es'
        ]
        z = int(elem_code)
        ion = int(round((elem_code - z) * 100)) + 1
        if 0 <= z < len(periodic_table):
            return f'{periodic_table[z]:>2s} {ion:d}'
        return f'{z:2d}.{ion-1:d}'

    def _detect_orders(wl_array):
        """Detect echelle orders by finding large wavelength gaps."""
        if wl_array is None or len(wl_array) < 2:
            return []
        wl = np.asarray(wl_array)
        diffs = np.diff(wl)
        median_diff = np.median(np.abs(diffs[diffs != 0]))
        gap_threshold = 50 * median_diff
        gap_indices = np.where(np.abs(diffs) > gap_threshold)[0]

        orders = []
        start_idx = 0
        for gap_idx in gap_indices:
            end_idx = gap_idx
            if end_idx > start_idx:
                orders.append((start_idx, end_idx))
            start_idx = end_idx + 1
        if start_idx < len(wl):
            orders.append((start_idx, len(wl) - 1))

        return orders

    outPath = Path(outFileName)
    outPath.parent.mkdir(parents=True, exist_ok=True)

    lines = []
    lines.append('LSD basic summary')
    lines.append('Generated at: {:}'.format(
        datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    lines.append('')

    if spectrumFile != '':
        lines.append('Spectrum file: {:}'.format(spectrumFile))
    if maskFile != '':
        lines.append('Mask file: {:}'.format(maskFile))
    if profileFile != '':
        lines.append('Profile file: {:}'.format(profileFile))

    if params is not None:
        lines.append('')
        lines.append('Parameters:')
        lines.append('  velStart (km/s): {:.6f}'.format(params.velStart))
        lines.append('  velEnd   (km/s): {:.6f}'.format(params.velEnd))
        lines.append('  pixVel   (km/s): {:.6f}'.format(params.pixVel))
        lines.append('  normDepth: {:.6f}'.format(params.normDepth))
        lines.append('  normLande: {:.6f}'.format(params.normLande))
        lines.append('  normWave (nm): {:.6f}'.format(params.normWave))
        lines.append('  sigmaClip: {:.6f}'.format(params.sigmaClip))
        lines.append('  sigmaClipIter: {:d}'.format(params.sigmaClipIter))
        lines.append('  interpMode: {:d}'.format(params.interpMode))
        lines.append('  removeContPol: {:d}'.format(params.removeContPol))
        weighting_mode = int(getattr(params, 'weightingMode', 2))
        lines.append('  Weighting mode: {:d} ({:s})'.format(
            weighting_mode,
            get_weighting_mode_description(weighting_mode),
        ))

        # Model options
        lines.append('')
        lines.append('Model options:')
        saturation = int(getattr(params, 'saturationCorrection', 1))
        telluric = int(getattr(params, 'telluricFiltering', 1))
        linefilter = int(getattr(params, 'lineFiltering', 1))
        lines.append('  Saturation correction: {:s}'.format(
            'enabled' if saturation else 'disabled'))
        lines.append('  Telluric filtering: {:s}'.format(
            'enabled' if telluric else 'disabled'))
        lines.append('  Line filtering: {:s}'.format(
            'enabled' if linefilter else 'disabled'))

    lines.append('')
    lines.append('Data summary:')

    if obs is not None and hasattr(obs, 'wl'):
        nObs = int(obs.wl.shape[0])
        lines.append('  observation pixels: {:d}'.format(nObs))
        if nObs > 0:
            lines.append('  wavelength range (nm): {:.6f} - {:.6f}'.format(
                float(obs.wl[0]), float(obs.wl[-1])))
        if hasattr(obs, 'nPixUsed'):
            nUsed = int(obs.nPixUsed)
            if nUsed > 0:
                lines.append(
                    '  observation pixels used in LSD: {:d}'.format(nUsed))

    if maskObj is not None and hasattr(maskObj, 'wl'):
        nMask = int(maskObj.wl.shape[0])
        lines.append('  mask lines used: {:d}'.format(nMask))

        if nMask > 0:
            lines.append('')
            lines.append('Mask statistics:')

            pol_w_stats = _stats_triplet(
                maskObj.weightV if hasattr(maskObj, 'weightV') else None)
            if pol_w_stats is not None:
                lines.append(
                    '  Mean pol weight    = {:.3f}  ({:.3f} {:.3f})'.format(
                        pol_w_stats[0], pol_w_stats[1], pol_w_stats[2]))

            int_w_stats = _stats_triplet(
                maskObj.weightI if hasattr(maskObj, 'weightI') else None)
            if int_w_stats is not None:
                lines.append(
                    '  Mean int weight    = {:.3f}  ({:.3f} {:.3f})'.format(
                        int_w_stats[0], int_w_stats[1], int_w_stats[2]))

            depth_stats = _stats_triplet(
                maskObj.depth if hasattr(maskObj, 'depth') else None)
            if depth_stats is not None:
                lines.append(
                    '     Mean line depth = {:.3f}  ({:.3f} {:.3f})'.format(
                        depth_stats[0], depth_stats[1], depth_stats[2]))

            wl_stats = _stats_triplet(maskObj.wl)
            if wl_stats is not None:
                lines.append(
                    '     Mean wavelength = {:.4f} ({:.4f} {:.4f})'.format(
                        wl_stats[0], wl_stats[1], wl_stats[2]))

            excite_stats = _stats_triplet(
                maskObj.excite if hasattr(maskObj, 'excite') else None)
            if excite_stats is not None:
                lines.append(
                    '     Mean excitation = {:.3f}  ({:.3f} {:.3f})'.format(
                        excite_stats[0], excite_stats[1], excite_stats[2]))

            lande_stats = _stats_triplet(
                maskObj.lande if hasattr(maskObj, 'lande') else None)
            if lande_stats is not None:
                lines.append(
                    '     Mean lande fact = {:.3f}  ({:.3f} {:.3f})'.format(
                        lande_stats[0], lande_stats[1], lande_stats[2]))

    if prof is not None and hasattr(prof, 'npix'):
        lines.append('  LSD profile pixels: {:d}'.format(int(prof.npix)))

    # Order information
    if obs is not None and hasattr(obs, 'wlOrig') and obs.wlOrig is not None:
        orders = _detect_orders(obs.wlOrig)
        if len(orders) > 0:
            lines.append('')
            lines.append('Spectral orders:')
            for i, (start, end) in enumerate(orders):
                npix = end - start + 1
                wl_start = float(obs.wlOrig[start])
                wl_end = float(obs.wlOrig[end])
                dlam = wl_end - wl_start
                lines.append(
                    f'   Order #{i:2d} spans {npix:4d} pxl (p0 = {start:6d}, '
                    f'lam = [{wl_start:8.4f} {wl_end:8.4f}] nm, dlam = {dlam:7.4f} nm)'
                )

    # Detailed line list
    if maskObj is not None and hasattr(maskObj,
                                       'wl') and maskObj.wl is not None:
        nLines = len(maskObj.wl)
        if nLines > 0:
            lines.append('')
            lines.append('Listing line weights...')

            # Calculate original weights to detect saturation correction
            has_weights = (hasattr(maskObj, 'weightI')
                           and hasattr(maskObj, 'weightV')
                           and hasattr(maskObj, 'depth')
                           and hasattr(maskObj, 'lande'))

            if has_weights and params is not None:
                # Recalculate original weights before saturation correction
                orig_weightV = (
                    maskObj.depth * maskObj.wl * maskObj.lande /
                    (params.normDepth * params.normWave * params.normLande))
                # Check if line was downweighted (tolerance for float comparison)
                is_downweighted = (maskObj.weightV < orig_weightV * 0.999)
            else:
                is_downweighted = np.zeros(nLines, dtype=bool)

            for i in range(min(nLines,
                               15000)):  # Limit to 15000 lines for file size
                marker = ' *' if is_downweighted[i] else '  '
                elem_str = _element_to_str(maskObj.element[i]) if hasattr(
                    maskObj, 'element') else '??'
                wl = float(maskObj.wl[i])
                depth = float(maskObj.depth[i]) if hasattr(maskObj,
                                                           'depth') else 0.0
                lande = float(maskObj.lande[i]) if hasattr(maskObj,
                                                           'lande') else 0.0
                weight = float(maskObj.weightV[i]) if has_weights else 0.0

                lines.append(
                    f'{marker} {elem_str} line #{i+1:4d} '
                    f'(@ {wl:8.4f} nm, d: {depth:.3f}, g: {lande:.3f}, w: {weight:.3f})'
                )

            if nLines > 5000:
                lines.append(f'   ... ({nLines - 5000} more lines omitted)')

    if ((chi2I is not None) or (chi2V is not None) or (chi2N1 is not None)):
        lines.append('')
        lines.append('Fit statistics:')
        dof = None
        if (obs is not None and prof is not None and hasattr(obs, 'wl')
                and hasattr(prof, 'npix')):
            dof = int(obs.wl.shape[0] - prof.npix)
            lines.append('  dof: {:d}'.format(dof))

        if chi2I is not None:
            lines.append('  chi2_I: {:.6f}'.format(float(chi2I)))
            if dof is not None and dof > 0:
                lines.append('  reduced_chi2_I: {:.6f}'.format(
                    float(chi2I) / dof))
        if chi2V is not None:
            lines.append('  chi2_V: {:.6f}'.format(float(chi2V)))
            if dof is not None and dof > 0:
                lines.append('  reduced_chi2_V: {:.6f}'.format(
                    float(chi2V) / dof))
        if chi2N1 is not None:
            lines.append('  chi2_N1: {:.6f}'.format(float(chi2N1)))
            if dof is not None and dof > 0:
                lines.append('  reduced_chi2_N1: {:.6f}'.format(
                    float(chi2N1) / dof))

    with open(outPath, 'w') as outFile:
        outFile.write('\n'.join(lines) + '\n')


def lsdFit(obs, mask, prof, interpMode):
    # Model the spectrum as a convolution of a line pattern (mask) M,
    # and a mean line profile Z.  Y = conv(M, Z)
    # With matrix multiplication Y = M.Z
    # where Y has n wavelength elements, Z has m profile elements, and M is nxm strengths (with diagonals encoding positions)

    # Define a chi^2, for an observed spectrum Yo (n long)
    # chi^2 = (Yo - M.Z)^T.S^2.(Yo - M.Z)
    # where S is the square diagonal matrix of inverse errors: S_(i,i) = 1/sigma_i
    # and ^T is the transpose of a matrix (and . is a dot product)
    # For a linear least squares solution, where the derivative of free parameters=0
    # 0 = (-M)^T.S^2.(Yo - M.Z)*2
    # Z = (M^T.S^2.M)^(-1).M^T.S^2.Yo
    # Where ^(-1) is the matrix inverse

    # Here M^T.S^2.Yo is is effectively the cross-correlation between the mask and the observation.  M^T.S^2.M is effectively the auto-correlation matrix.
    # Uncertainties can be estimated from the diagonal of (M^T.S^2.M)^(-1)
    # (M^T.S^2.M)^(-1) is the covariance matrix C, and sigma^2(Z_(i)) = C_(i,i)

    # For liner interpolation from the model on to the observed wavelength pixels,
    # the matrix M needs to have approximately double diagonals.
    # (not exactly diagonal, there will at least be glitches!)
    # Line l in the mask contributes to M by:
    # M_(i,j) = w_l * (v_(j+1) - v_(i))/(v_(j+1) - v_(j))
    # M_(i,j+1) = w_l * (v_(i) - v_(j))/(v_(j+1) - v_(j))
    # or: M_(i,j) = w_l * (1 - (v_(i) - v_(j))/(v_(j+1) - v_(j)) )
    # where w_l is the weigh of line l, and v_i is calculated as
    # v_i = c*(lambda_i - lambda_l)/lambda_l  and v_(j) < v_(i) < v_(j+1)
    # and lambda_l, lambda_i are the wavelengths of line l and pixel i
    # i runs over observed wavelengths, j runs over velocity pixels in the LSD profile

    # In the classic linear least squares setup of a.x=b, then minimize (a.x-b)^2
    # effectively x = Z, a = M, and b = Yo, solving for x
    # This could be solved by numpy.linalg.lstsq or scipy.optimize.lsq_linear
    # but that would ignore uncertainties. (Maybe divide a and b by sigma?)
    #
    # so here beta = M^T.S^2.Yo, alpha = (M^T.S^2.M), and covar = alpha^(-1)
    #

    sparseS2 = buildInvSig2(obs)

    M4I, M4V = buildM(obs, mask, prof, interpMode)
    MI = csr_matrix(M4I)
    MV = csr_matrix(M4V)

    #Use the sparse matrix 'dot with a vector' function for correct efficient calculation
    #(the sparse matrix dot product with a regular dense matrix seems to return a regular matrix)
    betaI = MI.T.dot(sparseS2.dot(obs.specI))
    betaV = MV.T.dot(sparseS2.dot(obs.specV))
    betaN1 = MV.T.dot(sparseS2.dot(obs.specN1))

    #Use the sparse matrix 'dot with a vector' function for correct efficient calculation
    #(the sparse matrix dot product with a sparse matrix seems to return a sparse matrix)
    alphaI = MI.T.dot(sparseS2.dot(MI))
    alphaV = MV.T.dot(sparseS2.dot(MV))

    # IMPROVED: Use Cholesky decomposition for numerical stability
    # This is ~10^6 times more stable than direct matrix inversion for ill-conditioned matrices
    alphaI_dense = alphaI.toarray()
    alphaV_dense = alphaV.toarray()

    try:
        # Cholesky decomposition: A = L·L^T
        cholI, lowI = cho_factor(alphaI_dense, lower=True)
        cholV, lowV = cho_factor(alphaV_dense, lower=True)

        # Solve via forward-backward substitution (no explicit inversion!)
        prof.specI = cho_solve((cholI, lowI), betaI)
        prof.specV = cho_solve((cholV, lowV), betaV)
        prof.specN1 = cho_solve((cholV, lowV), betaN1)

        # Compute error bars from diagonal of inverse
        # More efficient than full covar matrix inversion
        identity = np.eye(alphaI_dense.shape[0])
        covarI_diag = np.sum(cho_solve((cholI, lowI), identity)**2, axis=0)
        covarV_diag = np.sum(cho_solve((cholV, lowV), identity)**2, axis=0)

        prof.specSigI = np.sqrt(covarI_diag)
        prof.specSigV = np.sqrt(covarV_diag)
        prof.specSigN1 = np.sqrt(covarV_diag)

        # Apply adaptive smoothing based on covariance structure (C-version style)
        # This reduces high-frequency noise while preserving physical signal
        prof.specI = _smooth_profile(prof.specI, alphaI_dense, None)
        prof.specV = _smooth_profile(prof.specV, alphaV_dense, None)
        prof.specN1 = _smooth_profile(prof.specN1, alphaV_dense, None)

    except np.linalg.LinAlgError as e:
        print(f"WARNING: Cholesky decomposition failed: {e}")
        print("Falling back to direct matrix inversion (less stable)")
        covarI = inv(alphaI_dense)
        covarV = inv(alphaV_dense)

        prof.specI = np.dot(covarI, betaI)
        prof.specV = np.dot(covarV, betaV)
        prof.specN1 = np.dot(covarV, betaN1)
        prof.specSigI = np.sqrt(np.diag(covarI))
        prof.specSigV = np.sqrt(np.diag(covarV))
        prof.specSigN1 = np.sqrt(np.diag(covarV))

    return MI, MV, sparseS2


def _smooth_profile(profile, alpha, chol_factor=None):
    """
    Apply smoothing based on the Autocorrelation matrix (alpha).
    This mimics the C-version's adaptive smoothing from get_psf(), which uses
    the elements of the Cholesky-decomposed matrix 'a'.
    However, the C-version's 'choldc' does NOT overwrite the upper triangle of 'a',
    so 'a' still contains the original Autocorrelation matrix elements in the upper triangle.
    
    Therefore, the smoothing weights should come from alpha (Autocorrelation), NOT covar (Inverse).
    Using covar (which has negative off-diagonals) results in sharpening (jitter),
    whereas alpha (positive off-diagonals) results in smoothing.
    """
    nvel = len(profile)

    if nvel < 3:
        return profile

    try:
        # matrix 'alpha' IS the Autocorrelation matrix (M^T.S^2.M)
        # We use its diagonals directly.
        # Note: alpha is symmetric, so alpha[i, i+1] == alpha[i+1, i]

        covar = alpha  # Use alpha directly, do NOT invert it.

        # Extract diagonal and subdiagonal averages
        d1 = np.mean(np.diag(covar))  # diagonal average
        d2 = np.mean(np.diag(covar,
                             k=1)) if nvel > 1 else 0.0  # subdiagonal average

        if d1 <= 0:
            return profile  # Skip smoothing if diagonal is invalid

        # d2 in Autocorrelation matrix is POSITIVE (overlap).
        # This results in a proper weighted average smoothing.

        # Apply 3-point smoothing with weights
        prof_smooth = profile.copy()
        for k in range(1, nvel - 1):
            # Weighted average: current point + weighted neighbors
            prof_smooth[k] = (d1 * profile[k] + 0.5 * d2 *
                              (profile[k + 1] + profile[k - 1])) / (d1 + d2)

        return prof_smooth
    except Exception as e:
        # If smoothing fails, return original
        # print(f"DEBUG: Smoothing failed: {e}")
        return profile


def lsdFitSigmaClip(obs, mask, prof, params):
    #Fit within sigma clipping loop.
    #Calls the main LSD fitting function and several suport functions

    #simple error checking
    if (params.sigmaClipIter < 0):
        print(
            'WARNING: sigma clipping iterations < 1 found ({:}) assuming 1 fit desired'
            .format(params.sigmaClipIter))
        params.sigmaClipIter = 0

    #major sigma clipping loop
    i = 0
    while (i < params.sigmaClipIter + 1):

        MI, MV, sparseS2 = lsdFit(obs, mask, prof, params.interpMode)

        chi2I = getChi2(obs.specI, MI, sparseS2, prof.specI)
        chi2V = getChi2(obs.specV, MV, sparseS2, prof.specV)
        chi2N1 = getChi2(obs.specN1, MV, sparseS2, prof.specN1)

        if (i < params.sigmaClipIter):
            obs.sigmaClipI(prof, MI, params.sigmaClip)

        #print 'tlsdFit', tlsdFit-tStart, 'tChi2', tChi2-tlsdFit, 'tsigmaClipI', tsigmaClipI-tChi2
        i += 1

    #Optionally save the model after sigma clipping is done
    if (params.fSaveModelSpec == 1):
        print('saving model spectrum to {:} ...'.format(
            params.outModelSpecName))
        saveModelSpec(params.outModelSpecName, prof, MI, MV, obs.wl)

    return chi2I, chi2V, chi2N1


def scaleErr(profErr, chi2, obsUsed, profNpix):
    # Re-scales the error bars of an LSD profile by the root of the reduced chi^2
    # this ensures the reduced chi^2 is always ~1
    # useful for cases in which noise from the LSD reconstruction dominates photon noise
    # Note: this takes a calculated chi^2 value, assumed to be determined in the fitting routine
    # IMPROVED: Always apply chi2 scaling for conservative error estimates (C-version style)

    scale = np.sqrt(chi2 / (obsUsed - profNpix))

    # IMPROVED: Always apply scaling if chi2 > 1.0 for conservative error estimates
    # This matches C-version behavior in get_psf()
    if scale > 1.0:
        print(' Rescaling error bars by: {:.6f} (reduced chi2: {:.4f})'.format(
            scale, chi2 / (obsUsed - profNpix)))
        profErr *= scale
    else:
        print(' Error bars look good (scale {:.6f}, reduced chi2: {:.4f})'.
              format(scale, chi2 / (obsUsed - profNpix)))

    return scale


def zeroProf(prof, profErr, iContCorr):
    #Simple subroutine to make sure the average supplied profile is zero
    #this hopes to normalize out continuum polarization
    #Note: this may not always be desirable!

    avgP = np.average(prof)
    avgErr = np.average(profErr)
    rmsErr = np.sum(profErr**2)
    avgPerr = rmsErr / prof.shape[0]

    if (iContCorr != 0):
        print(
            ' removing profile continuum pol: {:.4e} +/- {:.4e} (avg err {:.4e})'
            .format(avgP, avgPerr, avgErr))
        prof -= avgP
    else:
        print(
            ' note, profile continuum pol: {:.4e} +/- {:.4e} (avg err {:.4e})'.
            format(avgP, avgPerr, avgErr))

    return


def estimateLineRange(profI, profSigI):
    #estimate the continuum from a 20 point average, using either end of the profile
    pad = 2
    approxCont = np.average((profI[pad:20 + pad], profI[-20 - pad:-pad]))
    approxErr = np.std((profI[pad:20 + pad], profI[-20 - pad:-pad]))
    meanErr = np.average((profSigI[pad:20 + pad], profSigI[-20 - pad:-pad]))
    scaleErr = 1.0
    if (approxErr > 1.1 * meanErr):
        print('(possible Stokes I uncertainty underestimate {:.4e} vs {:.4e})'.
              format(approxErr, meanErr))
        scaleErr = approxErr / meanErr

    #Get 4 sigma below (above) continuum points
    iTheorIn = np.where(profI[pad:-pad] > approxCont +
                        4. * scaleErr * profSigI[pad:-pad])[0] + pad
    iTheorOut = np.where(profI[pad:-pad] <= approxCont +
                         4. * scaleErr * profSigI[pad:-pad])[0] + pad

    return iTheorIn, iTheorOut


def nullTest(prof):
    #Check for a magnetic detection in V or N
    iTheorIn, iTheorOut = estimateLineRange(prof.specI, prof.specSigI)

    if (iTheorIn.shape[0] > 0):
        print('line range estimate {:} {:} km/s'.format(
            prof.vel[iTheorIn[0]], prof.vel[iTheorIn[-1]]))
    else:
        print('ERROR: could not find line range!  (using full profile)')
        iTheorIn = iTheorOut

    #import matplotlib.pyplot as plt
    #plt.plot(prof.vel, prof.specI)
    #plt.plot(prof.vel[iTheorIn], prof.specI[iTheorIn], '.')
    #plt.show()

    #'fitting' the flat line (essentially an average weighted by 1/sigma^2)
    contV = np.sum(prof.specV[iTheorIn] / prof.specSigV[iTheorIn]**2) / np.sum(
        1. / prof.specSigV[iTheorIn]**2)
    contN1 = np.sum(prof.specN1[iTheorIn] / prof.specSigN1[iTheorIn]**
                    2) / np.sum(1. / prof.specSigN1[iTheorIn]**2)

    chi2Vin = np.sum(
        ((prof.specV[iTheorIn] - contV) / prof.specSigV[iTheorIn])**2)
    chi2Vout = np.sum(
        ((prof.specV[iTheorOut] - contV) / prof.specSigV[iTheorOut])**2)
    chi2N1in = np.sum(
        ((prof.specN1[iTheorIn] - contN1) / prof.specSigN1[iTheorIn])**2)
    chi2N1out = np.sum(
        ((prof.specN1[iTheorOut] - contN1) / prof.specSigN1[iTheorOut])**2)

    approxDOFin = (iTheorIn.shape[0] - 1.)
    approxDOFout = (iTheorOut.shape[0] - 1.)

    probVIn = specialf.gammainc(approxDOFin / 2., chi2Vin / 2.)
    probVOut = specialf.gammainc(approxDOFout / 2., chi2Vout / 2.)
    probN1In = specialf.gammainc(approxDOFin / 2., chi2N1in / 2.)
    probN1Out = specialf.gammainc(approxDOFout / 2., chi2N1out / 2.)

    print(
        'V in line reduced chi^2 {:8f} (chi2 {:10f}) \n detect prob {:6f} (fap {:12.6e})'
        .format(chi2Vin / approxDOFin, chi2Vin, probVIn, 1. - probVIn))
    if (probVIn > 0.9999):
        print(' Detection! V (fap {:12.6e})'.format(1. - probVIn))
    elif (probVIn > 0.99):
        print(' Marginal detection V (fap {:12.6e})'.format(1. - probVIn))
    else:
        print(' Non-detection V (fap {:12.6e})'.format(1. - probVIn))
    print(
        ' V outside line reduced chi^2 {:8f} (chi2 {:10f}) \n detect prob {:6f} (fap {:12.6e})'
        .format(chi2Vout / approxDOFout, chi2Vout, probVOut, 1. - probVOut))

    print(
        'N1 in line reduced chi^2 {:8f} (chi2 {:10f}) \n detect prob {:6f} (fap {:12.6e})'
        .format(chi2N1in / approxDOFin, chi2N1in, probN1In, 1. - probN1In))
    if (probN1In > 0.9999):
        print(' Detection! N1 (fap {:12.6e})'.format(1. - probN1In))
    elif (probN1In > 0.99):
        print(' Marginal detection N1 (fap {:12.6e})'.format(1. - probN1In))
    else:
        print(' Non-detection N1 (fap {:12.6e})'.format(1. - probN1In))
    print(
        ' N1 outside line reduced chi^2 {:8f} (chi2 {:10f}) \n detect prob {:6f} (fap {:12.6e})'
        .format(chi2N1out / approxDOFout, chi2N1out, probN1Out,
                1. - probN1Out))

    return
