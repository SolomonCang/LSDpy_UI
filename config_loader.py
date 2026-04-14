import json
from dataclasses import dataclass
from pathlib import Path
from typing import List

from core.lsd_config import paramsLSD


def _resolve_runtime_path(value, base_dir):
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = base_dir / path
    return str(path.resolve())


def _default_lsd_profile_for_observation(observation_path):
    obs_path = Path(observation_path)
    return str((obs_path.parent / (obs_path.stem + '.lsd')).resolve())


@dataclass
class LSDRunTask:
    params: paramsLSD
    output_profile: str


@dataclass
class LSDConfig:
    params: paramsLSD
    output_profile: str
    config_path: Path
    raw_config: dict
    run_tasks: List[LSDRunTask]

    @classmethod
    def load(cls, config_path):
        config_file = Path(config_path).expanduser().resolve()
        with config_file.open('r', encoding='utf-8') as infile:
            raw_config = json.load(infile)

        run_tasks = cls._build_run_tasks(raw_config, config_file.parent)
        params = run_tasks[0].params
        output_profile = run_tasks[0].output_profile

        instance = cls(params=params,
                       output_profile=output_profile,
                       config_path=config_file,
                       raw_config=raw_config,
                       run_tasks=run_tasks)
        instance.validate()
        return instance

    @staticmethod
    def _build_run_tasks(raw_config, base_dir):
        input_cfg = raw_config.get('input', {})
        output_cfg = raw_config.get('output', {})

        spectra = input_cfg.get('spectra', [])
        if not isinstance(spectra, list):
            raise ValueError('input.spectra must be a list when provided')

        tasks = []
        if len(spectra) > 0:
            for idx, item in enumerate(spectra):
                if isinstance(item, str):
                    obs = item
                    mask = input_cfg.get('mask', '')
                elif isinstance(item, dict):
                    obs = item.get('observation', '')
                    mask = item.get('mask', input_cfg.get('mask', ''))
                else:
                    raise ValueError(
                        f'input.spectra[{idx}] must be a string or object')

                if obs == '':
                    raise ValueError(
                        f'input.spectra[{idx}] is missing observation')
                if mask == '':
                    raise ValueError(
                        f'input.spectra[{idx}] is missing mask and input.mask is empty'
                    )

                task_config = dict(raw_config)
                task_input_cfg = dict(input_cfg)
                task_input_cfg['observation'] = obs
                task_input_cfg['mask'] = mask
                task_config['input'] = task_input_cfg

                params = paramsLSD(config=task_config, base_dir=base_dir)

                output_profile = _default_lsd_profile_for_observation(
                    params.inObs)

                tasks.append(
                    LSDRunTask(params=params, output_profile=output_profile))
        else:
            params = paramsLSD(config=raw_config, base_dir=base_dir)
            output_profile = _resolve_runtime_path(
                output_cfg.get('profile', 'prof.dat'), base_dir)
            tasks.append(
                LSDRunTask(params=params, output_profile=output_profile))

        return tasks

    def validate(self):
        if self.params.inObs == '':
            raise ValueError(
                'LSDConfig.json is missing input.observation or it is empty')
        if self.params.inMask == '':
            raise ValueError(
                'LSDConfig.json is missing input.mask or it is empty')
        if self.params.velEnd <= self.params.velStart:
            raise ValueError(
                'profile.vel_end_kms must be larger than vel_start_kms')
        if self.params.pixVel <= 0:
            raise ValueError('profile.pixel_velocity_kms must be positive')
        if self.params.normDepth == 0 or self.params.normLande == 0 or self.params.normWave == 0:
            raise ValueError(
                'normalization depth, lande and wavelength must be non-zero')

    def apply_overrides(self, observation='', mask='', output=''):
        if observation != '' or mask != '' or output != '':
            base_params = self.run_tasks[0].params
            params = paramsLSD(config=self.raw_config,
                               base_dir=self.config_path.parent)
            if params.inObs == '':
                params.inObs = base_params.inObs
            if params.inMask == '':
                params.inMask = base_params.inMask

            if observation != '':
                params.inObs = _resolve_runtime_path(observation, Path.cwd())
            if mask != '':
                params.inMask = _resolve_runtime_path(mask, Path.cwd())

            if output != '':
                output_profile = _resolve_runtime_path(output, Path.cwd())
            elif observation != '' and len(self.run_tasks) > 1:
                output_profile = _default_lsd_profile_for_observation(
                    params.inObs)
            else:
                output_profile = self.output_profile

            self.run_tasks = [
                LSDRunTask(params=params, output_profile=output_profile)
            ]
            self.params = params
            self.output_profile = output_profile
            return

        self.params = self.run_tasks[0].params
        self.output_profile = self.run_tasks[0].output_profile
