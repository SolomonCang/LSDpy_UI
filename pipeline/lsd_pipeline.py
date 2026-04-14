import numpy as np
import scipy.constants
from pathlib import Path

from core import lsd_report, lsd_solver
from core.lsd_io import mask, observation, prof

c = scipy.constants.c * 1e-3


class LSDPipeline:

    def __init__(self, params, output_profile):
        self.params = params
        self.output_profile = output_profile

    def run(self):
        obs = observation(self.params.inObs)
        obs.specI = 1. - obs.specI

        line_mask = mask(self.params.inMask)
        line_mask.setWeights(self.params)

        profile = prof(self.params)

        line_mask.filterLines(obs, profile)
        obs.setInRange(line_mask, profile)

        wlStep = obs.wlOrig[1:] - obs.wlOrig[:-1]
        indWlSteps = np.where((wlStep > 0.) & (wlStep < 0.01))[0]
        obsAvgVel = np.average(wlStep[indWlSteps] / obs.wlOrig[indWlSteps] * c)
        print('Average observed spec velocity spacing: {:.6f} km/s'.format(
            obsAvgVel))

        print('using a {:n} point profile with {:.6f} km/s pixels'.format(
            profile.npix, self.params.pixVel))

        if (obsAvgVel * 0.9 > self.params.pixVel):
            print(
                'warning: profile velocity spacing small - profile may be poorly constrained'
            )
        if (obsAvgVel * 2.0 < self.params.pixVel):
            print(
                'warning: profile velocity spacing large - profile may be under sampling'
            )

        nLinesTooLow = np.where(line_mask.wl < obs.wl[0])[0].shape[0]
        nLinesTooHigh = np.where(line_mask.wl > obs.wl[-1])[0].shape[0]
        if (nLinesTooLow > 0):
            print('WARNING: {:n} lines in mask falls below observed range'.
                  format(nLinesTooLow))
        if (nLinesTooHigh > 0):
            print('WARNING: {:n} lines in mask falls above observed range'.
                  format(nLinesTooHigh))

        useMask = np.where(line_mask.iuse != 0)
        print(
            'mean mask depth {:.6f} wl {:.3f} Lande {:.6f} (from {:n} lines)'.
            format(np.average(line_mask.depth[useMask]),
                   np.average(line_mask.wl[useMask]),
                   np.average(line_mask.lande[useMask]),
                   line_mask.wl.shape[0]))
        print('mean mask norm weightI {:.6f} weightV {:.6f}'.format(
            np.average(line_mask.weightI[useMask]),
            np.average(line_mask.weightV[useMask])))

        chi2I, chi2V, chi2N1 = lsd_solver.lsdFitSigmaClip(
            obs, line_mask, profile, self.params)

        print('I reduced chi2 {:.4f} (chi2 {:.2f} constraints {:n} dof {:n})'.
              format(chi2I / (obs.wl.shape[0] - profile.npix), chi2I,
                     obs.wl.shape[0], profile.npix))
        lsd_solver.scaleErr(profile.specSigI, chi2I, obs.wl.shape[0],
                            profile.npix)

        print('V reduced chi2 {:.4f} (chi2 {:.2f} constraints {:n} dof {:n})'.
              format(chi2V / (obs.wl.shape[0] - profile.npix), chi2V,
                     obs.wl.shape[0], profile.npix))
        lsd_solver.scaleErr(profile.specSigV, chi2V, obs.wl.shape[0],
                            profile.npix)
        lsd_solver.zeroProf(profile.specV, profile.specSigV,
                            self.params.removeContPol)

        print('N1 reduced chi2 {:.4f} (chi2 {:.2f} constraints {:n} dof {:n})'.
              format(chi2N1 / (obs.wl.shape[0] - profile.npix), chi2N1,
                     obs.wl.shape[0], profile.npix))
        lsd_solver.scaleErr(profile.specSigN1, chi2N1, obs.wl.shape[0],
                            profile.npix)
        lsd_solver.zeroProf(profile.specN1, profile.specSigN1,
                            self.params.removeContPol)

        lsd_report.nullTest(profile)

        profile.save(self.output_profile)
        if (self.params.fLSDPlotImg != 0):
            profile.lsdplot(self.params.outPlotImgName)

        if (self.params.fSaveLSDOut != 0):
            if (self.params.outLSDOutName == 'auto'
                    or self.params.outLSDOutName == ''):
                output_path = Path(self.output_profile)
                lsdoutName = str(
                    output_path.with_name(output_path.stem + '_lsdout.txt'))
            else:
                lsdoutName = self.params.outLSDOutName

            lsd_report.saveLSDOut(lsdoutName,
                                  spectrumFile=self.params.inObs,
                                  maskFile=self.params.inMask,
                                  profileFile=self.output_profile,
                                  params=self.params,
                                  obs=obs,
                                  maskObj=line_mask,
                                  prof=profile,
                                  chi2I=chi2I,
                                  chi2V=chi2V,
                                  chi2N1=chi2N1,
                                  modelOptions={
                                      'saturationCorrection':
                                      self.params.saturationCorrection,
                                      'telluricFiltering':
                                      self.params.telluricFiltering,
                                      'lineFiltering':
                                      self.params.lineFiltering,
                                  })
        else:
            print('LSD output summary (lsdout) disabled in configuration')
