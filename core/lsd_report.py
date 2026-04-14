from datetime import datetime
from pathlib import Path

import numpy as np
import scipy.special as specialf

from core.lsd_config import get_weighting_mode_description


def saveModelSpec(outModelSpecName, prof, MI, MV, obsWl):
    # Save model spectrum (M·Z for I and V) at observed wavelength pixels.
    if (outModelSpecName != ''):
        specI = MI.dot(prof.specI)
        specV = MV.dot(prof.specV)
        specN1 = MV.dot(prof.specN1)

        out_path = Path(outModelSpecName)
        out_path.parent.mkdir(parents=True, exist_ok=True)
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


def estimateLineRange(profI, profSigI):
    # Estimate continuum level from the 20 outer pixels on each side (skip 2-pixel pad).
    # Returns pixel index arrays for inside and outside the line region.
    # See docs/algorithm.md §13.
    pad = 2
    approxCont = np.average((profI[pad:20 + pad], profI[-20 - pad:-pad]))
    approxErr = np.std((profI[pad:20 + pad], profI[-20 - pad:-pad]))
    meanErr = np.average((profSigI[pad:20 + pad], profSigI[-20 - pad:-pad]))
    scaleErr = 1.0
    if (approxErr > 1.1 * meanErr):
        print('(possible Stokes I uncertainty underestimate {:.4e} vs {:.4e})'.
              format(approxErr, meanErr))
        scaleErr = approxErr / meanErr

    iTheorIn = np.where(profI[pad:-pad] > approxCont +
                        4. * scaleErr * profSigI[pad:-pad])[0] + pad
    iTheorOut = np.where(profI[pad:-pad] <= approxCont +
                         4. * scaleErr * profSigI[pad:-pad])[0] + pad

    return iTheorIn, iTheorOut


def nullTest(prof):
    # Compute detection statistics for V and N1 in/out of line region.
    # See docs/algorithm.md §14 and docs/physics.md §7.
    iTheorIn, iTheorOut = estimateLineRange(prof.specI, prof.specSigI)

    if (iTheorIn.shape[0] > 0):
        print('line range estimate {:} {:} km/s'.format(
            prof.vel[iTheorIn[0]], prof.vel[iTheorIn[-1]]))
    else:
        print('ERROR: could not find line range!  (using full profile)')
        iTheorIn = iTheorOut

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
