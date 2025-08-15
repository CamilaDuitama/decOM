#!/usr/bin/env python3
"""
decOM: Similarity-based microbial source tracking for contamination assessment
of ancient oral samples using k-mer-based methods.

This module provides the main command-line interface for decOM.
"""

from importlib_resources import files
import argparse
import os
import subprocess
import sys
import plotly.io as pio
from pathlib import Path

from decOM import data
from decOM.__version__ import __version__
from decOM.modules.utils import (
    eprint, print_error, print_status, remove_files, check_input
)
from decOM.modules.sink import one_sink, several_sinks


pio.renderers.default = 'iframe'

# Get the project root directory more robustly
def _get_project_root():
    """Get the project root directory."""
    current_dir = Path(__file__).parent.parent.parent
    if (current_dir / '.git').exists() or (current_dir / 'setup.py').exists():
        return str(current_dir)
    # Fallback to old method
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _version():
    """Get the version of decOM, including git info if available."""
    decOM_version = f'{__version__}'
    try:
        # Use the improved project root function
        project_root = _get_project_root()
        # Try to get git description
        git = subprocess.run([
            'git', '-C', project_root, 'describe', '--always', '--dirty', '--abbrev=7'
        ], capture_output=True, text=True, check=False)
        
        if git.returncode == 0:
            git_desc = git.stdout.strip()
            if git_desc and git_desc != __version__:
                decOM_version += f'-{git_desc}'
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        # Git not available or other error - just use the version
        pass
    return decOM_version

def create_argument_parser():
    """Create and configure the argument parser."""
    parser = argparse.ArgumentParser(
        prog="decOM",
        description="Microbial source tracking for contamination assessment of ancient "
                   "oral samples using k-mer-based methods",
        add_help=True,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Single sink analysis
  decOM -s sample1 -k sample1.fof -p_sources ./sources_db -t 4 -mem 8GB

  # Multiple sinks analysis  
  decOM -p_sinks sinks.txt -p_keys ./keys_folder -p_sources ./sources_db -t 4 -mem 8GB

For more information, visit: https://github.com/CamilaDuitama/decOM
        """
    )
    
    sinks_parser = parser.add_mutually_exclusive_group(required=True)
    keys_parser = parser.add_mutually_exclusive_group(required=True)

    # Input arguments
    sinks_parser.add_argument(
        "-s", "--sink", dest='SINK', 
        help="Name of your sink sample. Must match the first element of the corresponding .fof file. "
             "Use with -k/--key for single sink analysis."
    )
    sinks_parser.add_argument(
        "-p_sinks", "--path_sinks", dest='PATH_SINKS',
        help="Path to .txt file containing sink names (one per line). "
             "Use with -p_keys/--path_keys for multiple sink analysis."
    )
    
    keys_parser.add_argument(
        "-k", "--key", dest='KEY', 
        help="Path to kmtricks .fof file for the sink sample. "
             "Use with -s/--sink for single sink analysis."
    )
    keys_parser.add_argument(
        "-p_keys", "--path_keys", dest='PATH_KEYS',
        help="Path to folder containing kmtricks .fof files for sink samples. "
             "Use with -p_sinks/--path_sinks for multiple sink analysis."
    )
    
    parser.add_argument(
        "-p_sources", "--path_sources", dest='PATH_SOURCES', required=True,
        help="Path to sources database folder (download from: "
             "https://zenodo.org/record/6513520/files/decOM_sources.tar.gz)"
    )

    # Resource arguments
    parser.add_argument(
        "-mem", "--memory", dest='MEMORY', required=True, default="10GB",
        help="Memory allocation for the analysis (e.g., 10GB, 16GB)"
    )
    parser.add_argument(
        "-t", "--threads", dest='THREADS', required=True, default=5, type=int,
        help="Number of CPU threads to use (default: 5)"
    )

    # Output arguments
    parser.add_argument(
        "-o", "--output", dest='OUTPUT', required=False, default="decOM_output/",
        help="Output directory path. Directory must not exist (default: decOM_output/)"
    )
    parser.add_argument(
        "-p", "--plot", dest='PLOT', required=False, default=True, 
        choices=['True', 'False'], type=str,
        help="Generate plots in PDF and HTML format (default: True)"
    )

    # Other arguments
    parser.add_argument(
        '-V', '--version', action='version', version=f'decOM {_version()}',
        help='Show version number and exit'
    )
    parser.add_argument(
        '-v', '--verbose', dest='VERBOSE', action='count', default=0, 
        help='Increase verbosity (use -vv for more verbose output)'
    )

    return parser

def main():
    """Main entry point for decOM."""
    # Clean up any previous log file
    remove_files(str(Path.cwd()) + "/decOM.log")
    
    # Set path to resources
    resources = str(files(data))

    # Create and parse arguments
    parser = create_argument_parser()
    args = parser.parse_args()

    # Validate mutually exclusive arguments
    if (args.SINK and not args.KEY) or (args.KEY and not args.SINK):
        parser.error('For single sink analysis, both -s/--sink and -k/--key are required')
    if (args.PATH_SINKS and not args.PATH_KEYS) or (args.PATH_KEYS and not args.PATH_SINKS):
        parser.error('For multiple sink analysis, both -p_sinks/--path_sinks and -p_keys/--path_keys are required')

    # Extract arguments
    sink = args.SINK
    p_sinks = args.PATH_SINKS
    p_sources = args.PATH_SOURCES
    key = args.KEY
    p_keys = args.PATH_KEYS
    mem = args.MEMORY
    t = args.THREADS
    plot = args.PLOT
    output = args.OUTPUT

    # Validate input parameters
    checked_input = check_input(sink, p_sinks, p_sources, key, p_keys, t, plot, output, mem, default=True)
    if checked_input == 1:
        return 1
    else:
        sink, p_sinks, p_sources, key, p_keys, t, plot, output, mem = checked_input

    # Log startup information
    print_status(f"Starting decOM version: {_version()}")
    
    # Log parameters
    params = {
        'sink': sink,
        'p_sinks': p_sinks,  
        'p_sources': p_sources,
        'key': key,
        'p_keys': p_keys,
        'threads': t,
        'plot': plot,
        'memory': mem,
        'output': output
    }
    
    param_str = '\n'.join([f"  {k}: {v}" for k, v in params.items()])
    print_status(f"decOM parameters:\n{param_str}")

    # Execute analysis
    try:
        if sink is not None:
            # Single sink analysis
            return one_sink(sink, p_sinks, p_sources, key, t, plot, output, mem, resources, default=True)
        elif p_sinks is not None:
            # Multiple sinks analysis
            return several_sinks(sink, p_sinks, p_sources, p_keys, t, plot, output, mem, resources, default=True)
    except Exception as e:
        print_error(f"Analysis failed: {str(e)}")
        return 1
        
    return 0

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print_error("Analysis interrupted by user")
        sys.exit(130)  # Standard exit code for SIGINT
    except Exception as e:
        print_error(f"Unexpected error: {str(e)}")
        eprint(f"Traceback: {e}")
        sys.exit(1)

