"""
Utility functions for decOM package.

This module contains helper functions for logging, file operations, input validation,
and other utility operations used throughout the decOM package.
"""

import sys
import os
import subprocess
import logging
from pathlib import Path
from typing import Union, Tuple, Optional
from datetime import datetime

import numpy as np
import pandas as pd
import plotly.express as px
from colorama import Fore, Style, init

# Initialize colorama for cross-platform colored output
init(autoreset=True)


def setup_logging(log_file: str = "decOM.log", verbose: int = 0) -> logging.Logger:
    """Setup logging configuration for decOM.
    
    Args:
        log_file: Path to log file
        verbose: Verbosity level (0=INFO, 1=DEBUG, 2=TRACE)
        
    Returns:
        Configured logger instance
    """
    # Create logger
    logger = logging.getLogger('decOM')
    logger.setLevel(logging.DEBUG)
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Create formatters
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_formatter = logging.Formatter(
        '[%(asctime)s] [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # File handler
    file_handler = logging.FileHandler(log_file, mode='w')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stderr)
    if verbose >= 2:
        console_handler.setLevel(logging.DEBUG)
    elif verbose >= 1:
        console_handler.setLevel(logging.INFO)
    else:
        console_handler.setLevel(logging.WARNING)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    return logger


def eprint(*args, **kwargs):
    """Print to stderr with logging to file."""
    with open('decOM.log', 'a') as log:
        print(*args, file=log)
    print(*args, file=sys.stderr, **kwargs)


def datetime_now() -> str:
    """Get current datetime as formatted string."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]


def print_error(msg: str):
    """Print error message with colored formatting."""
    eprint(f'[{datetime_now()}] [{Fore.RED}error{Style.RESET_ALL}] {msg}')


def print_warning(msg: str):
    """Print warning message with colored formatting."""
    eprint(f'[{datetime_now()}] [{Fore.YELLOW}warning{Style.RESET_ALL}] {msg}')


def print_status(msg: str):
    """Print status message with colored formatting."""
    eprint(f'[{datetime_now()}] [{Fore.GREEN}status{Style.RESET_ALL}] {msg}')


def remove_files(path: Union[str, Path]):
    """Safely remove files or directories.
    
    Args:
        path: Path to file or directory to remove
    """
    try:
        if Path(path).exists():
            subprocess.run(["rm", "-rf", str(path)], capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as e:
        print_warning(f"Failed to remove {path}: {e}")
    except Exception as e:
        print_warning(f"Error removing {path}: {e}")


def check_nrows(path: Union[str, Path]) -> int:
    """Check the number of rows in an input file.

    Args:
        path: Path to input file

    Returns:
        Number of rows in input file
        
    Raises:
        FileNotFoundError: If file doesn't exist
        IOError: If file can't be read
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
        
    try:
        with open(path, 'r') as fp:
            nrows = sum(1 for _ in fp)
        return nrows
    except IOError as e:
        raise IOError(f"Cannot read file {path}: {e}")


def validate_memory_format(memory: str) -> bool:
    """Validate memory format string.
    
    Args:
        memory: Memory string (e.g., "8GB", "1024MB")
        
    Returns:
        True if valid format, False otherwise
    """
    import re
    pattern = r'^\d+(\.\d+)?(GB|MB|TB|KB)$'
    return bool(re.match(pattern, memory, re.IGNORECASE))


def check_input(
    sink: Optional[str], 
    p_sinks: Optional[str], 
    p_sources: str, 
    key: Optional[str], 
    p_keys: Optional[str], 
    t: int, 
    plot: str, 
    output: str, 
    mem: str, 
    default: bool = True
) -> Union[int, Tuple]:
    """Validate user input parameters.
    
    Args:
        sink: Name of the sink being analyzed (single sink mode)
        p_sinks: Path to text file with list of sink names (multiple sink mode)
        p_sources: Path to folder with source database
        key: Path to kmtricks fof file for single sink
        p_keys: Path to folder with kmtricks fof files for multiple sinks
        t: Number of threads to use
        plot: Whether to generate plots ("True"/"False")
        output: Output directory path
        mem: Memory allocation string (e.g., "8GB")
        default: Whether running normal decOM (True) or decOM-aOralOut (False)

    Returns:
        Tuple with validated parameters, or 1 if validation fails
    """
    
    # Validate output directory doesn't exist
    if Path(output).exists():
        print_error(f"Output directory already exists: {output}")
        return 1

    # Validate sources database
    p_sources_path = Path(p_sources)
    if not p_sources_path.is_dir():
        print_error(f"Sources database path does not exist or is not a directory: {p_sources}")
        return 1

    # Validate memory format
    if not validate_memory_format(mem):
        print_error(f"Invalid memory format: {mem}. Use format like '8GB', '1024MB', etc.")
        return 1

    # Validate single sink mode
    if sink is not None:
        if not key:
            print_error("For single sink mode, both --sink and --key are required")
            return 1
            
        key_path = Path(key)
        if not key_path.is_file():
            print_error(f"Key file does not exist: {key}")
            return 1
            
        # Validate sink name matches first element in fof file
        try:
            with open(key_path, 'r') as f:
                sink_in_fof = f.read().split()[0]
            if sink != sink_in_fof:
                print_error(f"Sink name '{sink}' doesn't match name in fof file '{sink_in_fof}'")
                return 1
        except (IOError, IndexError) as e:
            print_error(f"Error reading key file {key}: {e}")
            return 1

    # Validate multiple sink mode
    elif p_sinks is not None:
        if not p_keys:
            print_error("For multiple sink mode, both --path_sinks and --path_keys are required")
            return 1
            
        p_sinks_path = Path(p_sinks)
        if not p_sinks_path.is_file():
            print_error(f"Sinks file does not exist: {p_sinks}")
            return 1
            
        if not p_sinks.endswith('.txt'):
            print_error(f"Sinks file must have .txt extension: {p_sinks}")
            return 1

        # Read and validate sink names
        try:
            with open(p_sinks_path, 'r') as f:
                sinks = [line.strip() for line in f if line.strip()]
        except IOError as e:
            print_error(f"Error reading sinks file {p_sinks}: {e}")
            return 1

        if len(sinks) == 0:
            print_error(f"Sinks file is empty: {p_sinks}")
            return 1
            
        if len(sinks) != len(set(sinks)):
            print_error("Sinks file contains duplicate sink names")
            return 1

        # Validate keys directory and files
        p_keys_path = Path(p_keys)
        if not p_keys_path.is_dir():
            print_error(f"Keys directory does not exist: {p_keys}")
            return 1

        for sink_name in sinks:
            key_file = p_keys_path / f"{sink_name}.fof"
            if not key_file.is_file():
                print_error(f"Key file missing for sink '{sink_name}': {key_file}")
                return 1

    # Validate threads
    if t <= 0:
        print_warning(f"Invalid thread count {t}, setting to 5")
        t = 5

    # Validate plot parameter
    if plot not in ["True", "False"]:
        print_warning(f"Invalid plot parameter '{plot}', setting to 'True'")
        plot = "True"

    # Normalize paths (add trailing slash)
    if not output.endswith('/'):
        output = output + '/'
        
    if not p_sources.endswith('/'):
        p_sources = p_sources + '/'
        
    if p_keys and not p_keys.endswith('/'):
        p_keys = p_keys + '/'

    # Validate matrix of sources based on mode (add back the matrix validation)
    if default:
        matrix_file = p_sources_path / "matrices" / "matrix_100.pa.txt"
        if matrix_file.exists():
            try:
                expected_rows = 14261987
                actual_rows = check_nrows(matrix_file)
                if actual_rows != expected_rows:
                    print_error(f"Matrix validation failed. Expected {expected_rows} rows, got {actual_rows}. "
                              "Please download the correct sources matrix from: "
                              "https://zenodo.org/record/6513520/files/decOM_sources.tar.gz")
                    return 1
            except (FileNotFoundError, IOError) as e:
                print_error(f"Cannot validate sources matrix: {e}")
                return 1
        else:
            print_warning("Matrix validation file not found, skipping validation")
    else:
        # decOM-aOralOut mode
        matrix_file = p_sources_path / "matrices" / "matrix_100.pa.txt"
        if matrix_file.exists():
            try:
                expected_rows = 14647270
                actual_rows = check_nrows(matrix_file)
                if actual_rows != expected_rows:
                    print_error(f"Matrix validation failed. Expected {expected_rows} rows, got {actual_rows}. "
                              "Please download the correct sources matrix from: "
                              "https://zenodo.org/record/6772124/files/aOralOut_sources.tar.gz")
                    return 1
            except (FileNotFoundError, IOError) as e:
                print_error(f"Cannot validate sources matrix: {e}")
                return 1
        else:
            print_warning("Matrix validation file not found, skipping validation")

    return sink, p_sinks, p_sources, key, p_keys, t, plot, output, mem

def check_input_MST(sink: str, p_sinks: str, p_sources: str, m: str, key: str, p_keys: str, t: str, plot: str, output: str, mem: str) -> Tuple:
    """Function to verify user input for decOM-MST is correct


    Args:
        sink (str): Name of the sink being analysed.
        It must be the same as the first element of key.fof. When this argument is set, -k/--key must be defined too

        p_sinks (str): .txt file with a list of sinks limited by a newline (\n).
        When this argument is set, -p_keys/--path_keys must be defined too.

        p_sources (str): Path to matrix of sources built with kmtricks.

        m (str) : Path to .csv file with 2 columns : SampleID and Env. 
        Each source used to build the matrix of sources must be in this table and must have a corresponding environment label.

        key (str): filtering key (a kmtricks fof with only one sample). When this argument is set, -s/--sink must be defined too.

        p_keys (str): Path to folder with filtering keys (a kmtricks fof with only one sample).
        You should have as many .fof files as sinks.When this argument is set, -p_sinks/--path_sinks must be defined too.

        t (str): Number of threads to use.

        plot (str): True if you want a plot (in pdf and html format) with the source proportions of the sink, else False.

        output (str): Path to output folder, where you want decOM to write the results.

        mem (str): Memory user would like to allocate for this process.

    Returns:
        tuple: tuple with output or 1 if user input was incorrect
    """

    # Verify output directory does not exist already
    if os.path.isdir(output):
        print_error("Output directory already exists")
        return 1
    #Check if map.csv is correctly formatted:
    if os.path.isfile(m):

        if m[-4:] != ".csv":
            print_error("File extension of map is not .csv")
            return 1  
        try:
            m_file=pd.read_csv(m)          
        except Exception as e:
            print_error(e)
            print_error("your map.csv file is corrupted or not properly formatted")
            return 1
        
        nrows_m = open(m).read().splitlines()
        if len(nrows_m) == 0:
            print_error("Your map.csv file is empty.")
            return 1

        true_cols={"Env","SampleID"}
        user_cols=set(m_file.columns)  
        
        if true_cols!=user_cols:
            print_error("Your map.csv file is not properly formatted. Columns of map.csv file should be Env and SampleID only.")
            return 1

        elif m_file.duplicated(subset="SampleID").any():
            print_error("Your map.csv file contains duplicates in the column called SampleID. Please remove them.")
        
        if m_file.isnull().values.any():
            print_error("Your map.csv file contains NaNs. Please remove them.")
            return 1

    else:
        print_error("map.csv file does not exist or path is incorrect") 
        return 1
    
    # Add / to output directory if not added by the user
    if output[-1] != "/":
        output = output + "/"

    if p_sources[-1] != "/":
        p_sources = p_sources + "/"

    #Check folder with sources
    if not os.path.isdir(p_sources):
        print_error("Path to matrix of sources is incorrect or you have not created your matrix of sources.")
        return 1
    
    try:
        fof=pd.read_csv(p_sources+"kmtricks.fof",sep="\s:\s",engine="python", names=["SampleID","Path"])
        samples_m_file=set(m_file["SampleID"])
        samples_fof=set(fof["SampleID"])
        if samples_m_file!=samples_fof:
            print_error("The samples in the kmtricks.fof of your p_sources/ folder are different from the samples in your map.csv file.")
            return 1
        if not os.path.isfile(p_sources+"/matrices/matrix.pa"):
            print_error("File matrix.pa does not exist. Make sure a binary pa version of your matrix of sources is present in the folder p_sources/matrices/")
            return 1
        if not os.path.isfile(p_sources+"/matrices/matrix.pa.txt"):
            print_error("File matrix.pa.txt does not exist. Make sure a text pa version of your matrix of sources is present in the folder p_sources/matrices/")
            return 1
    except:
        print_error("p_sources folder is corrupted. Make sure you follow the instructions to create the matrix of sources as described in the README file and make sure you did not remove any file inside output the folder.")
    
    # If user only has one sink
    if sink != None:

        with open(key) as f:
            sink_in_fof = f.read().split(" ")[0]

        if sink != sink_in_fof:
            print_error("The name of your -s/--sink should coincide with the name of the sample in the key.fof ")
            return 1

        if not os.path.isfile(key):
            print_error("key.fof file does not exist")
            return 1

    elif sink == None:
        if os.path.isfile(p_sinks):
            sinks = open(p_sinks).read().splitlines()
            try:
                p_sinks[-4:] == ".txt"

                if len(sinks) == 1:
                    print_error("Make sure your p_sinks file is correctly formatted. It should be a .txt file delimited "
                                "by newline (\\n)")
                    return 1

                elif len(sinks) == 0:
                    print_error("Your p_sinks file is empty.")
                    return 1
            except:
                print_error("File extension of p_sinks is not .txt")
                return 1

            if len(sinks) > len(set(sinks)):
                print_error("The p_sinks file has duplicated sinks")
                return 1
        else:
            print_error(".txt file p_sinks does not exist")
            return 1
        # Add / to p_keys directory if not added by the user
        if p_keys[-1] != "/":
            p_keys = p_keys + "/"

        if not os.path.isdir(p_keys):
            print_error("p_keys directory does not exist")
            return 1

        for s in sinks:
            if os.path.isfile(p_keys + s + ".fof") == False:
                print_error("key.fof file for sink " + s + " does not exist in p_keys directory or extension is incorrect")
                return 1

    # Check number of processes
    if int(t) <= 0:
        t = 5
        print_warning("-t parameter has been set to 5")

    # Check if plot variable was set correctly
    if plot not in ["True", "False"]:
        plot = "True"
        print_warning("-plot parameter has been set to True")

    # Verify input for mem is an integer
    try:
        int(mem[0:-2])
    except:
        print_error("-mem parameter is incorrectly set. It should be a positive number followed by GB. Ex: 10GB")
        return 1

    # Verify the user assigned some GB to the process
    if mem[-2:] != "GB" or int(mem[0:-2]) <= 0:
        print_error("-mem parameter is incorrectly set. It should be a positive number followed by GB. Ex: 10GB")
        return 1

    return sink, p_sinks, p_sources, m, key, p_keys, t, plot, output, mem

def check_input_CV(p_sinks: str, p_sources: str, p_keys: str, t: str, plot: str, output: str, mem: str, default: bool) -> Tuple:
    """Function to verify user input is correct for decOM-CV

    Args:
        p_sinks (str): .txt file with a list of sinks limited by a newline (\n).
        When this argument is set, -p_keys/--path_keys must be defined too.
        p_sources (str): path to folder downloaded from zenodo with sources
        key (str): filtering key (a kmtricks fof with only one sample). When this argument is set, -s/--sink must be defined too.
        p_keys (str): Path to folder with filtering keys (a kmtricks fof with only one sample).
        You should have as many .fof files as sinks.When this argument is set, -p_sinks/--path_sinks must be defined too.
        t (str): Number of threads to use.
        plot (str): True if you want a plot (in pdf and html format) with the source proportions of the sink, else False
        output (str): Path to output folder, where you want decOM to write the results.
        mem (str): Memory user would like to allocate for this process.

    Returns:
        tuple: tuple with output or 1 if user input was incorrect
    """
    # Function to verify input is correct

    # Check if folder with sources was downloaded
    if not os.path.isdir(p_sources):
        print_error("Path to matrix of sources is incorrect or have not downloaded matrix of sources.")
        return 1
    if os.path.isfile(p_sinks):
        sinks = open(p_sinks).read().splitlines()
        try:
            p_sinks[-4:] == ".txt"

            if len(sinks) == 1:
                print_error("Make sure your p_sinks file is correctly formatted. It should be a .txt file delimited "
                            "by newline (\\n)")
                return 1

            elif len(sinks) == 0:
                print_error("Your p_sinks file is empty.")
                return 1
        except:
            print_error("File extension of p_sinks is not .txt")
            return 1

        if len(sinks) > len(set(sinks)):
            print_error("The p_sinks file has duplicated sinks")
            return 1
    else:
        print_error(".txt file p_sinks does not exist")
        return 1
    # Add / to p_keys directory if not added by the user
    if p_keys[-1] != "/":
        p_keys = p_keys + "/"

    if not os.path.isdir(p_keys):
        print_error("p_keys directory does not exist")
        return 1

    for s in sinks:
        if os.path.isfile(p_keys + s + ".fof") == False:
            print_error("key.fof file for sink " + s + " does not exist in p_keys directory or extension is incorrect")
            return 1

        # Check number of processes
        if int(t) <= 0:
            t = 5
            print_warning("-t parameter has been set to 5")

        # Check if plot variable was set correctly
        if plot not in ["True", "False"]:
            plot = "True"
            print_warning("-plot parameter has been set to True")

        # Add / to output directory if not added by the user
        if output[-1] != "/":
            output = output + "/"

        if p_sources[-1] != "/":
            p_sources = p_sources + "/"
        # Verify input for mem is an integer
        try:
            int(mem[0:-2])
        except:
            print_error("-mem parameter is incorrectly set. It should be a positive number followed by GB. Ex: 10GB")
            return 1

        # Verify the user assigned some GB to the process
        if mem[-2:] != "GB" or int(mem[0:-2]) <= 0:
            print_error("-mem parameter is incorrectly set. It should be a positive number followed by GB. Ex: 10GB")
            return 1

        return p_sinks, p_sources, p_keys, t, plot, output, mem

def find_proportions(row: pd.Series, classes: list) -> pd.Series:
    """find_proportions is a function that estimates the percentage of every element in classes with respect to the sum over all elements in classes.
    Classes are equivalent to source environments in the microbial source tracking framework.

    Args:
        row (pd.Series): Row of a pd.DataFrame (to be used with axis=1)
        classes (list): list of all the unique source environments 

    Returns:
        pd.DataFrame: Pandas object with the estimated percentages
    """
    total = sum(row[classes])
    try:
        result = row[classes] / total
        result = result * 100
        result = result.apply(np.round, decimals=4)
    except:
        data = dict()
        for c in classes:
            data[c] = np.nan
        result = pd.Series(data)
    return result

def check_input_LOO(p_sources: str, m: str, t: str, plot: str, output: str, mem: str) -> Tuple:
    """Function to verify user input for decOM-LOO is correct


    Args:
        p_sources (str): Path to matrix of sources built with kmtricks.

        m (str) : Path to .csv file with 2 columns : SampleID and Env. 
        Each source used to build the matrix of sources must be in this table and must have a corresponding environment label.

        t (str): Number of threads to use.

        plot (str): True if you want a plot (in pdf and html format) with the source proportions of the sink, else False.

        output (str): Path to output folder, where you want decOM to write the results.

        mem (str): Memory user would like to allocate for this process.

    Returns:
        tuple: tuple with output or 1 if user input was incorrect
    """

    # Verify output directory does not exist already
    if os.path.isdir(output):
        print_error("Output directory already exists")
        return 1
    #Check if map.csv is correctly formatted:
    if os.path.isfile(m):

        if m[-4:] != ".csv":
            print_error("File extension of map is not .csv")
            return 1  
        try:
            m_file=pd.read_csv(m)          
        except Exception as e:
            print_error(e)
            print_error("your map.csv file is corrupted or not properly formatted")
            return 1
        
        nrows_m = open(m).read().splitlines()
        if len(nrows_m) == 0:
            print_error("Your map.csv file is empty.")
            return 1

        true_cols={"Env","SampleID"}
        user_cols=set(m_file.columns)  
        
        if true_cols!=user_cols:
            print_error("Your map.csv file is not properly formatted. Columns of map.csv file should be Env and SampleID only.")
            return 1

        elif m_file.duplicated(subset="SampleID").any():
            print_error("Your map.csv file contains duplicates in the column called SampleID. Please remove them.")
        
        if m_file.isnull().values.any():
            print_error("Your map.csv file contains NaNs. Please remove them.")
            return 1
        
        classes=set(m_file.Env)
        for c in classes:
            if m_file[m_file["Env"]==c].shape[0]==1:
                print_error("You need at least two samples belonging to each source environment, and there is only one sample coming from environment "\
                            +c+".")
                return 1
    else:
        print_error("map.csv file does not exist or path is incorrect") 
        return 1
    
    # Add / to output directory if not added by the user
    if output[-1] != "/":
        output = output + "/"

    if p_sources[-1] != "/":
        p_sources = p_sources + "/"

    #Check folder with sources
    if not os.path.isdir(p_sources):
        print_error("Path to matrix of sources is incorrect or you have not created your matrix of sources.")
        return 1
    
    try:
        fof=pd.read_csv(p_sources+"kmtricks.fof",sep="\s:\s",engine="python", names=["SampleID","Path"])
        samples_m_file=set(m_file["SampleID"])
        samples_fof=set(fof["SampleID"])
        if samples_m_file!=samples_fof:
            print_error("The samples in the kmtricks.fof of your p_sources/ folder are different from the samples in your map.csv file.")
            return 1
        if not os.path.isfile(p_sources+"/matrices/matrix.pa"):
            print_error("File matrix.pa does not exist. Make sure a binary pa version of your matrix of sources is present in the folder p_sources/matrices/")
            return 1
        if not os.path.isfile(p_sources+"/matrices/matrix.pa.txt"):
            print_error("File matrix.pa.txt does not exist. Make sure a text pa version of your matrix of sources is present in the folder p_sources/matrices/")
            return 1
    except:
        print_error("p_sources folder is corrupted. Make sure you follow the instructions to create the matrix of sources as described in the README file and make sure you did not remove any file inside output the folder.")
    
    # Check number of processes
    if int(t) <= 0:
        t = 5
        print_warning("-t parameter has been set to 5")

    # Check if plot variable was set correctly
    if plot not in ["True", "False"]:
        plot = "True"
        print_warning("-plot parameter has been set to True")

    # Verify input for mem is an integer
    try:
        int(mem[0:-2])
    except:
        print_error("-mem parameter is incorrectly set. It should be a positive number followed by GB. Ex: 10GB")
        return 1

    # Verify the user assigned some GB to the process
    if mem[-2:] != "GB" or int(mem[0:-2]) <= 0:
        print_error("-mem parameter is incorrectly set. It should be a positive number followed by GB. Ex: 10GB")
        return 1

    return p_sources, m,t, plot, output, mem


def summarize_FEAST(x, Type, Envs) -> pd.Series:
    """Function that summarizes FEAST's output by estimating the sum of contributions of each source enviroment

    Args:
        x (pd.Series): row of a FEAST output formatted in a pandas dataframe
        Type (str): Source environment being analysed
        Envs (list): List of unique source environments present in FEAST's output 

    Returns (pd.Series):
        Sum of the contribution of each source belonging to the class Type (in percentage)  
    """
    i=0
    found=False
    while i<len(Envs) and found==False:
        if Type==Envs[i]:
            columns=[x for x in x.index if Type in x]
            val=sum(x[columns].dropna())*100
            found=True
        i=i+1
    if found == False:
        val=np.nan
    return val

def format_ST(ST_result: str) -> pd.DataFrame:
    """format_ST adapts SourceTracker output and changes its format to make it comparable to the result from FEAST and decOM

    Args:
        ST_result (str): Filename of mixing_proportions.txt file resulting from a SourceTracker run

    Returns:
        pd.DataFrame: Formatted SourceTracker output as a pandas dataframe object
    """
    ST=pd.read_csv(ST_result, sep="\t",index_col=0).transpose()
    ST.reset_index(inplace=True)
    ST.rename(columns={"index":"Sink"},inplace=True)
    return ST

def find_max(row: pd.Series) -> str:
    """find_max Return index of first occurrence of maximum over requested axis. In case of a tie outputs the string 'TIE'.
    If all values in axis are NA, output is NA. NA/null values are excluded.

    Args:
        row (pd.Series): row of a pd.DataFrame

    Returns:
        result (str): If there is a tie, the output is the string charachter 'TIE'. If all values are NAN, the output is np.nan. 
        Otherwise it returns the index of first occurrence of maximum over requested axis.
    """
    rowmax = row.max()
    if len(np.where(rowmax==row)[0])==1:
        result=row.idxmax()
    else:
        result="TIE"
    return result

def plot_results(sink: str, p_sinks: str, result: pd.DataFrame, classes: list, output: str):
    """plot_results generates a plot (in pdf and html format) with the source proportions of each source environment in each sink

    Args:
        sink (str): Name of sink when only one sample is being analysed.
        p_sinks (str): name of .txt file with a list of sinks limited by a newline (\n)
        result (pd.DataFrame): Output of decOM
        classes (list): list with the distinct source environments being analysed by decOM
        output (str): Path to output folder, where you want decOM to write the results.

    Returns:
        None
    """
    if sink is not None:
        fig = px.histogram(result, x="Sink", y=["p_" + c for c in classes],
                           color_discrete_sequence=px.colors.qualitative.G10 + px.colors.qualitative.T10, opacity=0.9,
                           title="Proportions for sinks estimated by decOM", barmode="stack")
        fig.update_layout(width=400, height=800, yaxis_title="Percentage (%)")
        fig.write_image(output + "result_plot_sinks.pdf", width=400, height=800, scale=5, engine="kaleido")
        fig.write_html(output + "result_plot_sinks.html")

    elif p_sinks is not None:
        fig = px.histogram(result, x="Sink", y=["p_" + c for c in classes],
                           color_discrete_sequence=px.colors.qualitative.G10 + px.colors.qualitative.T10, opacity=0.9,
                           title="Proportions for sinks estimated by decOM", barmode="stack")
        fig.update_layout(width=800, height=500,yaxis_title="Percentage (%)")
        fig.write_image(output + "result_plot_sinks.pdf", width=1000, height=500, scale=5, engine="kaleido")
        fig.write_html(output + "result_plot_sinks.html")
    return
