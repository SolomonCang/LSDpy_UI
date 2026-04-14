from pathlib import Path

WEIGHTING_MODE_DESCRIPTIONS = {
    0: 'g',
    1: 'prof*g',
    2: 'lam*prof*g',
    3: 'prof',
    4: 'lam*prof',
    5: '1',
    6: 'prof*(lam*g)^2',
    7: 'fixed_threshold',
}


def get_weighting_mode_description(mode):
    return WEIGHTING_MODE_DESCRIPTIONS.get(int(mode), 'unknown')


class paramsLSD:

    def __init__(self, config, base_dir=None):
        #Read in most information controlling how the program runs
        self._set_defaults()
        self._load_from_mapping(config, base_dir=base_dir)

    def _set_defaults(self):
        self.weightingMode = 2
        self.fSaveLSDOut = 1
        self.outLSDOutName = 'auto'
        self.saturationCorrection = 1
        self.telluricFiltering = 1
        self.lineFiltering = 1
        # Fixed threshold weighting parameters (for high-noise-robust mode 7)
        self.weightingThreshold = 0.5  # Normalized depth threshold (0-1)
        self.weightingLowValue = 0.1  # Weight below threshold
        self.weightingHighValue = 10.0  # Weight above threshold

    @staticmethod
    def _resolve_path(value, base_dir=None):
        if value in ('', 'auto', None):
            return value

        path = Path(value).expanduser()
        if not path.is_absolute() and base_dir is not None:
            path = Path(base_dir).expanduser() / path
        return str(path.resolve())

    def _load_from_mapping(self, config, base_dir=None):
        input_cfg = config.get('input', {})
        profile_cfg = config.get('profile', {})
        normalization_cfg = config.get('normalization', {})
        processing_cfg = config.get('processing', {})
        sigma_cfg = processing_cfg.get('sigma_clip', {})
        output_cfg = config.get('output', {})
        model_cfg = config.get('model_options', {})

        self.inObs = self._resolve_path(input_cfg.get('observation', ''),
                                        base_dir=base_dir)
        self.inMask = self._resolve_path(input_cfg.get('mask', ''),
                                         base_dir=base_dir)

        self.velStart = float(profile_cfg.get('vel_start_kms', -200.0))
        self.velEnd = float(profile_cfg.get('vel_end_kms', 200.0))
        self.pixVel = float(profile_cfg.get('pixel_velocity_kms', 1.8))

        self.normDepth = float(normalization_cfg.get('depth', 1.0))
        self.normLande = float(normalization_cfg.get('lande', 1.0))
        self.normWave = float(normalization_cfg.get('wavelength_nm', 500.0))
        self.weightingMode = int(normalization_cfg.get('weighting_mode', 2))
        self.weightingThreshold = float(
            normalization_cfg.get('weighting_threshold', 0.5))
        self.weightingLowValue = float(
            normalization_cfg.get('weighting_low_value', 0.1))
        self.weightingHighValue = float(
            normalization_cfg.get('weighting_high_value', 10.0))

        self.removeContPol = int(
            processing_cfg.get('remove_continuum_polarization', 1))
        self.sigmaClip = float(sigma_cfg.get('limit', 500.0))
        self.sigmaClipIter = int(sigma_cfg.get('iterations', 0))
        self.interpMode = int(processing_cfg.get('interp_mode', 1))

        self.fSaveModelSpec = int(output_cfg.get('save_model_spectrum', 0))
        self.outModelSpecName = ''
        if self.fSaveModelSpec == 1:
            self.outModelSpecName = self._resolve_path(output_cfg.get(
                'model_spectrum', 'outModelSpec.dat'),
                                                       base_dir=base_dir)

        self.fLSDPlotImg = int(output_cfg.get('plot_profile', 0))
        self.fSavePlotImg = int(output_cfg.get('save_plot', 0))
        self.outPlotImgName = ''
        if self.fSavePlotImg == 1:
            self.outPlotImgName = self._resolve_path(output_cfg.get(
                'plot_image', 'prof.png'),
                                                     base_dir=base_dir)

        self.fSaveLSDOut = int(output_cfg.get('save_lsdout', 1))
        self.outLSDOutName = ''
        if self.fSaveLSDOut == 1:
            self.outLSDOutName = self._resolve_path(output_cfg.get(
                'lsdout', 'auto'),
                                                    base_dir=base_dir)

        self.saturationCorrection = int(
            model_cfg.get('saturation_correction', 1))
        self.telluricFiltering = int(model_cfg.get('telluric_filtering', 1))
        self.lineFiltering = int(model_cfg.get('line_filtering', 1))
