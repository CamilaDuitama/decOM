#!/usr/bin/env python3
import time
from dask.distributed import Client, LocalCluster
import dask.dataframe as dd
import dask.array as da
from importlib_resources import files
import argparse
import plotly.io as pio
from decOM import data
from decOM.__version__ import __version__
from decOM.modules.utils import *
from decOM.modules.sink import create_vector, plot_results

pio.renderers.default = 'iframe'
decOM_root = os.path.dirname(os.path.abspath(os.path.realpath(os.__file__)))


def _version():
    decOM_version = f'{__version__}'
    git = subprocess.run(['git', '-C', decOM_root, 'describe', '--always'], capture_output=True, stderr=None, text=True)
    if git.returncode == 0:
        git_hash = git.stdout.strip().rsplit('-', 1)[-1]
        decOM_version += f'-{git_hash}'
    return decOM_version

def main():
    return