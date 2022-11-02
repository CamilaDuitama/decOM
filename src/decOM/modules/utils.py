from re import M
import sys
from xmlrpc.client import boolean
from colorama import Fore, Style
import subprocess
import numpy as np
import pandas as pd
from datetime import datetime
import plotly.express as px
import os


def eprint(*args, **kwargs):
    log = open('decOM.log', 'a')
    log.write(*args)
    log.write('\n')
    print(*args, file=sys.stderr, **kwargs)

def datetime_now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

def print_error(msg):
    eprint(f'[{datetime_now()}] [' + f'{Fore.RED}error{Style.RESET_ALL}' + f'] {msg}')

def print_warning(msg):
    eprint(f'[{datetime_now()}] [' + f'{Fore.YELLOW}warning{Style.RESET_ALL}' + f'] {msg}')

def print_status(msg):
    eprint(f'[{datetime_now()}] [' + f'{Fore.GREEN}status{Style.RESET_ALL}' + f'] {msg}')

def remove_files(path):
    subprocess.run(["rm", "-rf", path],capture_output=True,text=True)

def check_nrows(path:str)->int:
    """Function to check the number of rows of an input file

    Args:
        path (str): String to input file

    Returns:
        int: Number of rows in intput file
    """
    with open(path, 'r') as fp:
        nrows = len(fp.readlines())
    return nrows

def check_input(sink:str, p_sinks:str, p_sources:str, key:str, p_keys:str, t:str, plot:str, output:str, mem:str, default:boolean)->tuple:
    """Function to verify user input is correct

    Args:
        sink (str): Name of the sink being analysed.
        It must be the same as the first element of key.fof. When this argument is set, -k/--key must be defined too
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
        default (boolean): True if user wants to run normal decOM, False if user wants to run decOM-aOralOut

    Returns:
        tuple: tuple with output or 1 if user input was incorrect
    """
    # Function to verify input is correct

    # Verify output directory does not exist already
    if os.path.isdir(output):
        print_error("Output directory already exists")
        return 1

    # Check if folder with sources was downloaded
    if not os.path.isdir(p_sources):
        print_error("Path to matrix of sources is incorrect or have not downloaded matrix of sources.")
        return 1

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

    #Verify the number of rows of the matrix of sources, to see if user downloaded the right matrix
    if default == True:
        if check_nrows(p_sources+"/matrices/matrix_100.pa.txt") != 14261987:
            print_error("Your matrix of sources is corrupted or you selected the wrong p_sources folder. When running decOM, make sure you download and untar the following matrix of sources:"+\
                        "https://zenodo.org/record/6513520/files/decOM_sources.tar.gz")
            return 1
    else:
        if check_nrows(p_sources+"/matrices/matrix_100.pa.txt") != 14647270:
            print_error("Your matrix of sources is corrupted or you selected the wrong p_sources folder. When running decOM-aOralOut, make sure you download and untar the following matrix of sources:"+\
                        "https://zenodo.org/record/6772124/files/aOralOut_sources.tar.gz")
            return 1

    return sink, p_sinks, p_sources, key, p_keys, t, plot, output, mem

def check_input_MST(sink:str, p_sinks:str, p_sources:str, m:str,key:str, p_keys:str, t:str, plot:str, output:str, mem:str)->tuple:
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

def check_input_CV(p_sinks:str, p_sources:str, p_keys:str, t:str, plot:str, output:str, mem:str, default:boolean)->tuple:
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

def find_proportions(row:pd.Series, classes:list) -> pd.Series:
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

def summarize_FEAST(x,Type,Envs)->pd.Series:
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

def format_ST(ST_result:str)->pd.DataFrame:
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

def find_max(row:pd.Series)->str:
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

def plot_results(sink:str, p_sinks:str, result:pd.DataFrame, classes:list, output:str):
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
