#!/usr/bin/python3

import argparse

from config_loader import LSDConfig
from pipeline.lsd_pipeline import LSDPipeline


def parse_args():
    parser = argparse.ArgumentParser(
        description=('Run Least Squares Deconvolution using a standard '
                     'LSDConfig.json configuration file.'))
    parser.add_argument(
        'observation',
        nargs='?',
        default='',
        help='Observed spectrum file. Overrides input.observation.')
    parser.add_argument(
        'output',
        nargs='?',
        default='',
        help='Output LSD profile path. Overrides output.profile.')
    parser.add_argument('-m',
                        '--mask',
                        dest='mask',
                        default='',
                        help='Mask file. Overrides input.mask.')
    parser.add_argument('--config',
                        '-c',
                        dest='config',
                        default='LSDConfig.json',
                        help='Path to LSD JSON configuration file.')
    return parser.parse_args()


class LSDRunner:

    def __init__(self, args):
        self.args = args

    def load_runtime_config(self):
        config = LSDConfig.load(self.args.config)
        config.apply_overrides(observation=self.args.observation,
                               mask=self.args.mask,
                               output=self.args.output)
        return [(task.params, task.output_profile)
                for task in config.run_tasks]

    def run(self):
        run_tasks = self.load_runtime_config()
        for index, (params, output_profile) in enumerate(run_tasks, start=1):
            if len(run_tasks) > 1:
                print('--- Running task {}/{} ---'.format(
                    index, len(run_tasks)))
                print('observation: {}'.format(params.inObs))
                print('mask: {}'.format(params.inMask))
                print('output: {}'.format(output_profile))
            pipeline = LSDPipeline(params, output_profile)
            pipeline.run()


def main():
    args = parse_args()
    runner = LSDRunner(args)
    runner.run()


if __name__ == '__main__':
    main()
