import numpy as np
import scipy
from numpy.linalg import inv
from scipy.linalg import cho_factor, cho_solve
from scipy.sparse import csr_matrix

from core.lsd_report import saveModelSpec

c = scipy.constants.c * 1e-3


def buildInvSig2(obs):
    # Diagonal sparse matrix S²: weights = I/σ² (photon-noise model, see docs/algorithm.md §4)
    if np.mean(obs.specI) < 0.5:
        intensity = 1.0 - obs.specI  # specI stored as depth (1-I)
    else:
        intensity = obs.specI
    intensity = np.maximum(intensity, 0.0001)
    tmp = intensity * (obs.specSig**(-2))
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

    return maskMI, maskMV


def getChi2(Yo, sparseM, sparseS2, Z):
    # chi^2 = (Yo - M.Z)^T S^2 (Yo - M.Z)  — see docs/algorithm.md §8
    tmpChi = (Yo - sparseM.dot(Z))
    chi2 = tmpChi.T.dot(sparseS2.dot(tmpChi))
    return chi2


def lsdFit(obs, mask, prof, interpMode):
    # Solve LSD normal equations Z = (M^T S^2 M)^{-1} M^T S^2 Yo via Cholesky.
    # See docs/algorithm.md §5-6 for derivation.

    sparseS2 = buildInvSig2(obs)

    M4I, M4V = buildM(obs, mask, prof, interpMode)
    MI = csr_matrix(M4I)
    MV = csr_matrix(M4V)

    #Use the sparse matrix 'dot with a vector' function for correct efficient calculation
    #(the sparse matrix dot product with a regular dense matrix seems to return a regular matrix)
    betaI = MI.T.dot(sparseS2.dot(obs.specI))
    betaV = MV.T.dot(sparseS2.dot(obs.specV))
    betaN1 = MV.T.dot(sparseS2.dot(obs.specN1))

    alphaI = MI.T.dot(sparseS2.dot(MI))  # autocorrelation matrix
    alphaV = MV.T.dot(sparseS2.dot(MV))

    alphaI_dense = alphaI.toarray()
    alphaV_dense = alphaV.toarray()

    try:
        cholI, lowI = cho_factor(alphaI_dense, lower=True)
        cholV, lowV = cho_factor(alphaV_dense, lower=True)

        prof.specI = cho_solve((cholI, lowI), betaI)
        prof.specV = cho_solve((cholV, lowV), betaV)
        prof.specN1 = cho_solve((cholV, lowV), betaN1)

        identity = np.eye(alphaI_dense.shape[0])
        covarI_diag = np.sum(cho_solve((cholI, lowI), identity)**2, axis=0)
        covarV_diag = np.sum(cho_solve((cholV, lowV), identity)**2, axis=0)

        prof.specSigI = np.sqrt(covarI_diag)
        prof.specSigV = np.sqrt(covarV_diag)
        prof.specSigN1 = np.sqrt(covarV_diag)

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
    # 3-point weighted smoothing using autocorrelation matrix diagonals.
    # Weights come from alpha (= M^T S^2 M), not the inverse, so off-diagonals
    # are positive and produce averaging rather than sharpening.
    # See docs/algorithm.md §7.
    nvel = len(profile)
    if nvel < 3:
        return profile
    try:
        d1 = np.mean(np.diag(alpha))
        d2 = np.mean(np.diag(alpha, k=1)) if nvel > 1 else 0.0
        if d1 <= 0:
            return profile
        prof_smooth = profile.copy()
        for k in range(1, nvel - 1):
            prof_smooth[k] = (d1 * profile[k] + 0.5 * d2 *
                              (profile[k + 1] + profile[k - 1])) / (d1 + d2)
        return prof_smooth
    except Exception:
        return profile


def lsdFitSigmaClip(obs, mask, prof, params):
    # LSD fit with optional sigma clipping; see docs/algorithm.md §9.
    if (params.sigmaClipIter < 0):
        print(
            'WARNING: sigma clipping iterations < 1 found ({:}) assuming 1 fit desired'
            .format(params.sigmaClipIter))
        params.sigmaClipIter = 0

    i = 0
    while (i < params.sigmaClipIter + 1):

        MI, MV, sparseS2 = lsdFit(obs, mask, prof, params.interpMode)

        chi2I = getChi2(obs.specI, MI, sparseS2, prof.specI)
        chi2V = getChi2(obs.specV, MV, sparseS2, prof.specV)
        chi2N1 = getChi2(obs.specN1, MV, sparseS2, prof.specN1)

        if (i < params.sigmaClipIter):
            obs.sigmaClipI(prof, MI, params.sigmaClip)

        i += 1

    if (params.fSaveModelSpec == 1):
        print('saving model spectrum to {:} ...'.format(
            params.outModelSpecName))
        saveModelSpec(params.outModelSpecName, prof, MI, MV, obs.wl)

    return chi2I, chi2V, chi2N1


def scaleErr(profErr, chi2, obsUsed, profNpix):
    # Scale error bars by sqrt(reduced chi2) when chi2_red > 1. See docs/algorithm.md §10.
    scale = np.sqrt(chi2 / (obsUsed - profNpix))
    if scale > 1.0:
        print(' Rescaling error bars by: {:.6f} (reduced chi2: {:.4f})'.format(
            scale, chi2 / (obsUsed - profNpix)))
        profErr *= scale
    else:
        print(' Error bars look good (scale {:.6f}, reduced chi2: {:.4f})'.
              format(scale, chi2 / (obsUsed - profNpix)))
    return scale


def zeroProf(prof, profErr, iContCorr):
    # Subtract profile mean to remove continuum polarisation offset. See docs/algorithm.md §11.
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
