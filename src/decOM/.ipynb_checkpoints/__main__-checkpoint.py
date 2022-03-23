#!/usr/bin/env python3

import os
import subprocess
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import time
import csv
import sys
import plotly.graph_objects as go
import plotly.io as pio
from dask.distributed import Client, LocalCluster, progress
import dask
import dask.dataframe as dd
import dask.array as da
from importlib_resources import files, as_file
from . import data
from .__version__ import __version__
import argparse
import plotly.graph_objects as go
import plotly.io as pio
pio.renderers.default = 'iframe' 

decOM_root = os.path.dirname(os.path.abspath(os.path.realpath(os.__file__)))

def _version():
    decOM_version = f'{__version__}'
    git = subprocess.run(['git', '-C', decOM_root, 'describe', '--always'], capture_output=True, stderr=None, text=True)
    if git.returncode == 0:
        git_hash = git.stdout.strip().rsplit('-',1)[-1]
        decOM_version += f'-{git_hash}'
    return decOM_version

def main(argv=None):
    
    print("Starting decOM version: "+str(_version()))
    
    #Set path to resources
    resources=str(files(data))

    #Parse args
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbose", help="increase output verbosity",
                        action="store_true")
    
    parser.add_argument("-s","--sink", help="Write down the name of your sink",required=True)
    parser.add_argument("-p_sources","--path_sources",help="path to sources matrix. Ex: ./matrix_100.pa.txt",required=True)
    parser.add_argument("-p_sink","--path_sink",help="Path to sink vector, the output of kmtricks filter Ex: ./kmtricks_output/matrices/100.vec",required=True)
    parser.add_argument("-p_missing", "--path_missing_kmers",help="Path to missing kmers, the output of kmtricks filter after using kmtricks aggregate Ex: ./kmtricks_output/count/{sink}_missing.txt",required=True)
    parser.add_argument("-mem","--memory",help="Write down how much memory you want to use. Ex: 500GiB",required=True)
    parser.add_argument("-t","--threads",help="Number of threads to use. Ex: 10",required=True)
    parser.add_argument("-plt","--plot",help="True if you want a plot with the source proportions of the sink, else False",required=False,default=True)
    args = parser.parse_args()
    
    start=time.time() 
    sink=args.sink
    p_sources=args.path_sources
    path_sink=args.path_sink
    path_missing_kmers=args.path_missing_kmers
    mem=args.memory
    t=args.threads
    plot=args.plot
    
    cluster = LocalCluster(memory_limit=mem,n_workers=int(t))
    client = Client(cluster)
    print("Client was set:")
    print(client)

    
    #Load metadata from sources
    metadata=pd.read_csv(resources+"/metadata.csv")

    #Load run accession codes for sources from k-mer matrix .fof files
    colnames=pd.read_csv(resources+"/kmtricks.fof", sep=" : ",\
                         header=None,names=["Run_accession","to_drop"],engine="python")
    colnames.drop(columns="to_drop",inplace=True)

    #Parse sources and classes
    sources=list(colnames["Run_accession"])
    classes=sorted(list(set(metadata["True_label"])))

    #Sort metadata according to column order in matrix DataFrame
    sorted_metadata=pd.DataFrame(columns=metadata.columns)
    for j in sources:
        sorted_metadata=pd.concat([sorted_metadata,metadata[metadata["Run_accession"]==j]])
    sorted_metadata.reset_index(drop=True,inplace=True)

    #Build result dataframe
    result=pd.DataFrame(columns=classes+["Unknown","Running time","Sink"])

    #Load k-mer matrix of sources as dataframe
    partition=dd.read_table(p_sources+"matrix_100.pa.txt",header=None,sep=" ",\
                            names=["Kmer"]+list(colnames["Run_accession"]))

    #Drop K-mer column
    partition_array=partition.drop(["Kmer"],axis=1)

    #Define M' matrix of sources
    M_prime=partition_array.values
    M_prime.compute_chunk_sizes()
    #M_prime=M_prime.persist()

    
    print("Chunk sizes for the M_prime matrix were computed") 

    #Create new vector for sink
    s_t=dd.read_table(path_sink,header=None,names=["pa"])
    s_t=s_t["pa"]
    s_t=s_t.values
    s_t.compute_chunk_sizes()

    #Define s_t (vector of sink)
    s_t=s_t.persist()

    #Labels for this LOO run
    labels=[sorted_metadata["True_label"][x] for x in range(len(sources))]

    #Define matrix H (one hot-encoding of labels)
    H = da.from_array(pd.get_dummies(labels, columns=classes).values)

    #Construct vector w (number of balls that go into each bin, see eq. 3 in paper)
    w=np.matmul(np.matmul(s_t,M_prime),H)
    w=w.compute()
    w=pd.DataFrame(w,index=classes).transpose()

    #Find balls that go into the Unknown bin
    missing_kmers=pd.read_csv(path_missing_kmers,names=["K-mer","Abundance"],header=None,sep=" ")
    w["Unknown"]=missing_kmers.shape[0]

    #Find proportions
    total=w[classes+["Unknown"]].sum(axis=1)[0]
    w["Sink"]=[sink]
    end=time.time()
    w["Running time"]=[end-start]
    result=pd.concat([result,w])
    result[["p_Sediment/Soil","p_Skin","p_aOral","p_mOral","p_Unknown"]]=(result[["Sediment/Soil","Skin","aOral","mOral","Unknown"]]/total).values[0]
    result.to_csv(sink+"_OM_output.csv",index=False)
    print("Sink " +sink+ " was analyzed in " + str(end-start))
    
    colors=['#636EFA', '#EF553B', '#00CC96', '#AB63FA']
    #Plot results
    if plot:
        fig = px.bar(result, y=["p_aOral", "p_mOral","p_Sediment/Soil","p_Skin","p_Unknown"], color_discrete_sequence=px.colors.qualitative.G10, opacity=0.8, title="Proportions sink "+ sink)
        fig.update_layout(width=400,height=800)
        fig.write_image("result_plot_"+sink+".pdf",width=400,height=800,scale=5)
    
    client.close()

if __name__ == "__main__":
    sys.exit(main())
