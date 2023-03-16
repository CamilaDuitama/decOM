#!/usr/bin/env python3

import resource
from importlib_resources import files
import argparse
from pkg_resources import resource_isdir
import plotly.io as pio
from decOM import data
from decOM.__version__ import __version__
from decOM.modules.utils import *
from decOM.modules.sink import * 
from pathlib import Path


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
    remove_files(str(Path.cwd())+"/decOM.log")

    # Set path to resources
    resources = str(files(data))

    # Parser
    parser = argparse.ArgumentParser(prog="decOM-LOO",
                                     description="Microbial source tracking for contamination assessment of ancient "
                                                 "oral samples using k-mer-based methods",
                                     add_help=True)
    # Mandatory arguments
    parser.add_argument("-p_sources", "--path_sources", dest='PATH_SOURCES',
                        help="path to matrix of sources created using kmtricks",
                        required=True)
    parser.add_argument("-m", "--map", dest='MAP_FILE',
                        help=".csv file with two columns: SampleID and Env. All the samples used to build the input matrix of sources p_sources should be present in this table.",
                        required=True)
    parser.add_argument("-mem", "--memory", dest='MEMORY',
                        help="Write down how much memory you want to use for this process. Ex: 10GB", required=True,
                        default="10GB")
    parser.add_argument("-t", "--threads", dest='THREADS', help="Number of threads to use. Ex: 5", required=True,
                        default=5, type=int)
    parser.add_argument("-o", "--output", dest='OUTPUT',
                        help="Path to output folder, where you want decOM to write the results."
                             " Folder must not exist, it won't be overwritten.", required=False,
                        default="decOM_output/")

    # Optional arguments
    parser.add_argument("-p", "--plot", dest='PLOT',
                        help="True if you want a plot (in pdf and html format)"
                             " with the source proportions of the sink, else False",
                        required=False, default=True,choices={'True', 'False'})

    # Other arguments
    parser.add_argument('-V', '--version', action='version', version=f'decOM {_version()}',
                        help='Show version number and exit')
    parser.add_argument('-v', '--verbose', dest='VERBOSE', action='count', default=0, help='Verbose output')

    # Parse arguments
    args = parser.parse_args()

    # Error mutually inclusive arguments
    p_sources = args.PATH_SOURCES
    m= args.MAP_FILE
    mem = args.MEMORY
    t = args.THREADS
    plot = args.PLOT
    output = args.OUTPUT

    # Check user input is correct
    checked_input = check_input_LOO(p_sources, m, t, plot, output, mem)
    if checked_input == 1:
        return 1
    else:
        p_sources, m, t, plot, output, mem = checked_input

    print_status("Starting decOM-LOO version: " + str(_version()))
    print_status("MST feature of decOM has started")

    print_status("Arguments decOM-LOO:"+"\n"+ 
    "p_sources: "+str(p_sources)+","+
    "m: "+str(p_sources)+","+
    "t: "+str(t)+","+
    "plt: "+str(plot)+","+
    "mem: "+str(mem)+","+ 
    "o: "+str(output))

    #Run decOM-LOO
    LOO(p_sources, m ,t, plot, output, mem)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        eprint(e)
        print_error(e)
