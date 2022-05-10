#!/usr/bin/env python3

import os
import numpy as np
import plotly.express as px
import pandas as pd
import time
import subprocess
import csv
import sys
import plotly.graph_objects as go
import plotly.io as pio
from dask.distributed import Client, LocalCluster, progress
import dask.dataframe as dd
import dask.array as da
from importlib_resources import files, as_file
import argparse
import plotly.io as pio

from decOM import data
from decOM.__version__ import __version__
from decOM.modules.utils import *
from decOM.modules.sink import create_vector

pio.renderers.default = 'iframe'

decOM_root = os.path.dirname(os.path.abspath(os.path.realpath(os.__file__)))


def _version():
    decOM_version = f'{__version__}'
    git = subprocess.run(['git', '-C', decOM_root, 'describe', '--always'], capture_output=True, stderr=None, text=True)
    if git.returncode == 0:
        git_hash = git.stdout.strip().rsplit('-', 1)[-1]
        decOM_version += f'-{git_hash}'
    return decOM_version


def main(argv=None):
    start = time.time()
    # Set path to resources
    resources = str(files(data))

    # Parser
    parser = argparse.ArgumentParser(prog="decOM",
                                     description="Microbial source tracking for contamination assessment of ancient oral samples using k-mer-based methods",
                                     add_help=True)

    ## Mandatory arguments
    parser.add_argument("-s", "--sink", dest='SINK', help="Write down the name of your sink", required=True)
    parser.add_argument("-p_sources", "--path_sources", dest='PATH_SOURCES',
                        help="path to folder downloaded from https://zenodo.org/record/6513520/files/decOM_sources.tar.gz",
                        required=True)
    parser.add_argument("-k", "--key", dest='KEY', help="filtering key (a kmtricks fof with only one sample).",
                        required=True)
    parser.add_argument("-mem", "--memory", dest='MEMORY',
                        help="Write down how much memory you want to use for this process. Ex: 20GiB", required=True,
                        default="5GiB")
    parser.add_argument("-t", "--threads", dest='THREADS', help="Number of threads to use. Ex: 5", required=True,
                        default=5, type=int)
    parser.add_argument("-o", "--output", dest='OUTPUT',
                        help="Path to output folder, where you want decOM to write the results", required=True,
                        default="decOM_output/")

    ## Optional arguments
    parser.add_argument("-p", "--plot", dest='PLOT',
                        help="True if you want a plot with the source proportions of the sink, else False",
                        required=False, default=True)

    ## Other arguments
    parser.add_argument('-V', '--version', action='version', version=f'decOM {_version()}',
                        help='Show version number and exit')

    # Parse arguments
    args = parser.parse_args()

    print_status("Starting decOM version: " + str(_version()))

    sink = args.SINK
    p_sources = args.PATH_SOURCES
    key = args.KEY
    mem = args.MEMORY
    t = args.THREADS
    plot = args.PLOT
    output = args.OUTPUT

    # Verify input is correct
    if not os.path.isdir(p_sources):
        print_error("Path to matrix of sources is incorrect or you have not downloaded matrix of sources")
        return 1

    if not os.path.isfile(key):
        print_error("key.fof file does not exist")
        return 1

    with open(key) as f:
        sink_in_fof = f.read().split(" ")[0]

    if sink != sink_in_fof:
        print_error("The name of your -sink should coincide with the name of the sample in the key.fof ")
        return 1

    if int(t) <= 0:
        t = 5
        print_warning("-t parameter has been set to 5")

    if plot not in ["True", "False"]:
        plot = "True"
        print_warning("-plot parameter has been set to True")

    if output[-1] != "/":
        output = output + "/"

    if p_sources[-1] != "/":
        p_sources = p_sources + "/"

    if os.path.isdir(output):
        print_error("Output directory already exists")
        return 1

    error = False
    try:
        int(mem[0:-2])
    except:
        error = True

    if error:
        print_error("-mem parameter is incorrectly set. It should be a positive number followed by GB. Ex: 10GB")
        return 1

    if mem[-2:] != "GB" or int(mem[0:-2]) <= 0:
        print_error("-mem parameter is incorrectly set. It should be a positive number followed by GB. Ex: 10GB")
        return 1

    # Create folder of results
    subprocess.call(["mkdir", output])

    # Create vector of sources
    create_vector(output_path=output, path_to_sources=p_sources, key=key, accession=sink, t=t)

    # Define paths from output of kmtricks filter and kmtricks aggregate
    path_sink = output + sink + "_vector/matrices/100.vec"
    path_missing_kmers = output + sink + "_vector/counts/partition_100/" + sink + "_missing.txt"

    # Initialize dask
    cluster = LocalCluster(memory_limit=mem, n_workers=int(t))
    client = Client(cluster)
    print_status("Client was set:")
    print_status(client)

    # Load metadata from sources
    metadata = pd.read_csv(resources + "/metadata.csv")

    # Load run accession codes for sources from k-mer matrix .fof files
    colnames = pd.read_csv(resources + "/kmtricks.fof", sep=" : ", \
                           header=None, names=["Run_accession", "to_drop"], engine="python")
    colnames.drop(columns="to_drop", inplace=True)

    # Parse sources and classes
    sources = list(colnames["Run_accession"])
    classes = sorted(list(set(metadata["True_label"])))

    # Sort metadata according to column order in matrix DataFrame
    sorted_metadata = pd.DataFrame(columns=metadata.columns)
    for j in sources:
        sorted_metadata = pd.concat([sorted_metadata, metadata[metadata["Run_accession"] == j]])
    sorted_metadata.reset_index(drop=True, inplace=True)

    # Build result dataframe
    result = pd.DataFrame(columns=classes + ["Unknown", "Running time", "Sink"])

    # Load k-mer matrix of sources as dataframe
    partition = dd.read_table(p_sources + "matrices/matrix_100.pa.txt", header=None, sep=" ", \
                              names=["Kmer"] + list(colnames["Run_accession"]))

    # Drop K-mer column
    partition_array = partition.drop(["Kmer"], axis=1)

    # Define M_s matrix of sources
    M_s = partition_array.values
    M_s.compute_chunk_sizes()

    print_status("Chunk sizes for the M_s matrix were computed")

    # Create new vector for sink
    s_t = dd.read_table(path_sink, header=None, names=["pa"])
    s_t = s_t["pa"]
    s_t = s_t.values
    s_t.compute_chunk_sizes()

    # Define s_t (vector of sink)
    s_t = s_t.persist()

    # Define list of labels for sources
    labels = [sorted_metadata["True_label"][x] for x in range(len(sources))]

    # Define matrix H (one hot-encoding of labels)
    H = da.from_array(pd.get_dummies(labels, columns=classes).values)

    # Construct vector w (number of balls that go into each bin, see eq. 2 in paper)
    w = np.matmul(np.matmul(s_t, M_s), H)
    w = w.compute()
    w = pd.DataFrame(w, index=classes).transpose()

    # Find balls that go into the Unknown bin
    missing_kmers = pd.read_csv(path_missing_kmers, names=["K-mer", "Abundance"], header=None, sep=" ")
    w["Unknown"] = missing_kmers.shape[0]

    # Find proportions
    total = w[classes + ["Unknown"]].sum(axis=1)[0]
    w["Sink"] = [sink]
    end = time.time()
    w["Running time"] = [end - start]
    result = pd.concat([result, w])
    result[["p_Sediment/Soil", "p_Skin", "p_aOral", "p_mOral", "p_Unknown"]] = \
        (result[["Sediment/Soil", "Skin", "aOral", "mOral", "Unknown"]] / total).values[0]
    result.to_csv(output + sink + "_OM_output.csv", index=False)
    print_status("Sink " + sink + " was analyzed in " + str(np.round(end - start, 4)) + " seconds")

    # Plot results
    if plot == "True":
        fig = px.histogram(result, x="Sink", y=["p_aOral", "p_mOral", "p_Sediment/Soil", "p_Skin", "p_Unknown"],
                           color_discrete_sequence=px.colors.qualitative.G10, opacity=0.9,
                           title="Proportions sink " + sink, barmode="stack")
        fig.update_layout(width=400, height=800)
        fig.write_image(output + "result_plot_" + sink + ".pdf", width=400, height=800, scale=5, engine="kaleido")

    client.close();
    client.shutdown();
    remove_files("./dask-worker-space/");


if __name__ == "__main__":
    sys.exit(main())
