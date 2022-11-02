#!/usr/bin/env python3
import numpy as np
import pandas as pd
import plotly.io as pio
import argparse
from decOM.__version__ import __version__
from decOM.modules.utils import *
from pathlib import Path

pio.renderers.default = 'iframe'
decOM_root = os.path.dirname(os.path.abspath(os.path.realpath(os.__file__)))

def main():
    remove_files(str(Path.cwd())+"/decOM.log")
    # Parser
    parser = argparse.ArgumentParser(prog="decOM-format",
                                     description="Feature of decOM to compare and adapt the output format of FEAST and ST results",
                                     add_help=True)

    # Mandatory arguments
    parser.add_argument("-m", "--method", dest='METHOD', choices={"FEAST", "ST"},
    help="Write down the method used to produce the output table you want to reformat. Options are FEAST or ST. Ex: -m FEAST",
    required=True)
    parser.add_argument("-mst", "--MST_table", dest='MST_TABLE',
                              help="Path to output table you are interested in reformatting. It should be a tab (\t) separated file.",required=True)
    parser.add_argument("-map", "--map", dest='MAPFILE', help="Path to map.txt used by ST/FEAST. It should be a tab (\t) separated file.",required=True)
    parser.add_argument("-out", "--output_file", dest='OUTFILE', help="Name of output file",required=True)
    parser.add_argument('-v', '--verbose', dest='VERBOSE', action='count', default=0, help='Verbose output')

    # Parse arguments
    args = parser.parse_args()

    method=args.METHOD
    mst=args.MST_TABLE
    mapf=args.MAPFILE
    out=args.OUTFILE

    #Check user input is correct
    if  not os.path.isfile(mst):
        print_error("The file to the MST table from either FEAST or ST does not exist")
        return 1

    try :
        pd.read_csv(mst,sep="\t")
    except IOError as e:
        print_error(e)
        print_error("Error reading your MST table.")
        return 1

    if  not os.path.isfile(mapf):
        print_error("The file to the map.txt from either FEAST or ST does not exist")
        return 1

    try :
        pd.read_csv(mapf,sep="\t")
    except IOError as e:
        print_error(e)
        print_error("Error reading your map.txt file.")
        return 1

    if os.path.isfile(out):
        print_error("Your output file already exists, decOM won't over-write it.")
        return 1

    #Read map
    mapf=pd.read_csv(mapf,sep="\t",index_col=0)
    #Create list for environments present in map
    envs=list(set(mapf[(mapf["SourceSink"]=="source") | (mapf["SourceSink"]=="Source")]["Env"]))
    envs=envs+["Unknown"]
    
    #If user input is a FEAST table
    if method=="FEAST":
        FEAST=pd.read_csv(mst,sep="\t")
        result=pd.DataFrame()
        #Format MST table from FEAST
        for e in envs:
            result[e]=FEAST.apply(summarize_FEAST,args=(e,envs),axis=1)
        #Find environment with highest contribution (hard label)
        result["FEAST_max"]=result[envs].apply(find_max,axis=1)
        #Write file to csv
        result.to_csv(out,index=False)

    #If user input is a ST table
    else:
        #Format MST table from SourceTracker
        ST=format_ST(mst)
        #Find environment with highest contribution (hard label)
        ST["ST_max"]=ST[envs].apply(find_max,axis=1)
        #Write file to csv
        ST.to_csv(out,index=False)
    return


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        eprint(e)
        print_error(e)

