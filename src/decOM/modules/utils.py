import sys
from colorama import Fore, Style
import subprocess
import numpy as np
import pandas as pd
from datetime import datetime
import os


def eprint(*args, **kwargs):
    log = open('decOM.log', 'a')
    log.write(*args)
    log.write('\n')
    print(*args, file=sys.stderr, **kwargs)


def datetime_now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def print_error(msg):
    eprint(f'[{datetime_now()}] [' + f'{Fore.RED}error{Style.RESET_ALL}' + f'] {msg}')


def print_warning(msg):
    eprint(f'[{datetime_now()}] [' + f'{Fore.YELLOW}warning{Style.RESET_ALL}' + f'] {msg}')


def print_status(msg):
    eprint(f'[{datetime_now()}] [' + f'{Fore.GREEN}status{Style.RESET_ALL}' + f'] {msg}')


def remove_files(path):
    subprocess.call(["rm", "-rf", path])


def check_input(sink, p_sinks, p_sources, key, p_keys, t, plot, output, mem):
    # Function to verify input is correct

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

    # Verify output directory does not exist already
    if os.path.isdir(output):
        print_error("Output directory already exists")
        return 1

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
    return sink, p_sinks, p_sources, key, p_keys, t, plot, output, mem


def find_proportions(row, classes):
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
