#!/usr/bin/env python3

from importlib_resources import files
import argparse
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
    parser = argparse.ArgumentParser(prog="decOM",
                                     description="Microbial source tracking for contamination assessment of ancient "
                                                 "oral samples using k-mer-based methods",
                                     add_help=True)
    sinks_parser = parser.add_mutually_exclusive_group(required=True)
    keys_parser = parser.add_mutually_exclusive_group(required=True)

    # Mandatory arguments
    sinks_parser.add_argument("-s", "--sink", dest='SINK', help="Write down the name of your sink. "
                                                                "It must be the same as the first element of key.fof. "
                                                                "When this argument is set, -k/--key must be defined "
                                                                "too ")
    sinks_parser.add_argument("-p_sinks", "--path_sinks", dest='PATH_SINKS',
                              help=".txt file with a list of sinks limited by a newline (\\n).  "
                                   "When this argument is set, -p_keys/--path_keys must be defined too.")
    parser.add_argument("-p_sources", "--path_sources", dest='PATH_SOURCES',
                        help="path to folder downloaded from https://zenodo.org/record/6513520/files/decOM_sources"
                             ".tar.gz",
                        required=True)
    keys_parser.add_argument("-k", "--key", dest='KEY', help="filtering key (a kmtricks fof with only one sample). "
                                                             "When this argument is set, -s/--sink must be defined too.")
    keys_parser.add_argument("-p_keys", "--path_keys", dest='PATH_KEYS',
                             help=" Path to folder with filtering keys (a kmtricks fof with only one sample). "
                                  "You should have as many .fof files as sinks. "
                                  "When this argument is set, -p_sinks/--path_sinks must be defined too.")
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
    if (args.SINK and not args.KEY) or (args.KEY and not args.SINK):
        parser.error('If you only have one sink, both -s/--sink and -k/--key are mandatory arguments')
    if (args.PATH_SINKS and not args.PATH_KEYS) or (args.PATH_KEYS and not args.PATH_SINKS):
        parser.error('If you have several sinks, both -p_sinks/--path_sinks and -p_keys/--path_keys'
                     ' are mandatory arguments')
    sink = args.SINK
    p_sinks = args.PATH_SINKS
    p_sources = args.PATH_SOURCES
    key = args.KEY
    p_keys = args.PATH_KEYS
    mem = args.MEMORY
    t = args.THREADS
    plot = args.PLOT
    output = args.OUTPUT

    # Check user input is correct
    checked_input = check_input(sink, p_sinks, p_sources, key, p_keys, t, plot, output, mem, default = True)
    if checked_input == 1:
        return 1
    else:
        sink, p_sinks, p_sources, key, p_keys, t, plot, output, mem = checked_input



    print_status("Starting decOM version: " + str(_version()))

    print_status("Arguments decOM:"+"\n"+ 
    "sink: "+str(sink)+","+
    "p_sinks: "+str(p_sinks)+","+
    "p_sources: "+str(p_sources)+","+
    "key: "+str(key)+","+
    "p_keys: "+str(p_keys)+","+
    "t: "+str(t)+","+
    "plt: "+str(plot)+","+
    "mem: "+str(mem)+","+ 
    "o: "+str(output))

    #One sink to analyse only
    if sink is not None:
        return one_sink(sink, p_sinks, p_sources, key, t, plot, output, mem, resources, default=True)

    #If user has several sinks  
    elif p_sinks is not None:
        return several_sinks(sink, p_sinks, p_sources, p_keys, t, plot, output, mem, resources ,default=True)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        eprint(e)
        print_error(e)

