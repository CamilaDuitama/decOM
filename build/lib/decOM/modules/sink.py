#!/usr/bin/env python3

from email.policy import strict
from .utils import *
from os import path
import pandas as pd
from dask.distributed import Client, LocalCluster
import dask.dataframe as dd
import dask.array as da
import time

def create_vector(output_path:str, path_to_sources:str, key:str, accession:str, t:int):
    """create_vector prepares the input fastq files by using kmtricks. 
    It produces the input vector to be compared against the matrix of sources and estimates the number of k-mers to be allocated in the Unknown bin.

    Args:
        output_path (str): Path to output folder, where you want decOM to write the results.
        path_to_sources (str): Path to matrix of downloaded from zenodo
        key (str): filtering key (a kmtricks fof with only one sample).
        accession (str): Identifier of sink being processed
        t (int): Number of threads allocated by the user to run decOM
    Returns:
        None
    """
    output = output_path + accession + "_vector/"
    if path.exists(output):
        subprocess.call(["rm", "-rf", output])
    subprocess.call(
        ["kmtricks", "filter", "--in-matrix", path_to_sources, "--key", key, "--output", output, "--out-types", "k,v"])
    subprocess.call(
        ["kmtricks", "aggregate", "-t", str(t), "--run-dir", output, "--count", accession + ":kmer", "--output",
         output + "counts/partition_100/" + accession + "_missing.txt"])
    return

def one_sink(sink, p_sinks, p_sources, key, t, plot, output, mem, resources, default):
    start = time.time()
    #Which matrix of sources does the user want to use
    if default == True:
        # Load metadata from sources
        metadata = pd.read_csv(resources + "/metadata.csv")

        # Load run accession codes for sources from k-mer matrix .fof files
        colnames = pd.read_csv(resources + "/kmtricks.fof", sep=" : ",
                                header=None, names=["Run_accession", "to_drop"], engine="python")
        colnames.drop(columns="to_drop", inplace=True)
    else:
        # Load metadata from sources
        metadata = pd.read_csv(resources + "/aOralOut_metadata.csv")

        # Load run accession codes for sources from k-mer matrix .fof files
        colnames = pd.read_csv(resources + "/aOralOut_kmtricks.fof", sep=" : ",
                                header=None, names=["Run_accession", "to_drop"], engine="python")
        colnames.drop(columns="to_drop", inplace=True)


    # Create folder of results
    subprocess.call(["mkdir", output])

    # Create vector of sources
    create_vector(output_path=output, path_to_sources=p_sources, key=key, accession=sink, t=t)

    # Define paths from output of kmtricks filter and kmtricks aggregate
    path_sink = output + sink + "_vector/matrices/100.vec"
    path_missing_kmers = output + sink + "_vector/counts/partition_100/" + sink + "_missing.txt"

    if not os.path.isfile(path_sink) or not os.path.isfile(path_missing_kmers):
        print_error("Sink vector for " + sink + " could not be created, verify your input files are correct")
        return 1
    else:
        print_status("Sink vector for " + sink + " was created")

    try:
        # Initialize dask
        cluster = LocalCluster(memory_limit=mem, n_workers=int(t))
        client = Client(cluster)
        print_status("Client was set")
        print_status(client)

        # Parse sources and classes
        sources = list(colnames["Run_accession"])
        classes = sorted(list(set(metadata["True_label"])))

        # Sort metadata according to column order in matrix DataFrame
        sorted_metadata = pd.DataFrame(columns=metadata.columns)
        for j in sources:
            sorted_metadata = pd.concat([sorted_metadata, metadata[metadata["Run_accession"] == j]])
        sorted_metadata.reset_index(drop=True, inplace=True)

        # Build result dataframe
        result = pd.DataFrame(columns=classes + ["Unknown", "Running time (s)", "Sink"])

        # Start using dask:
        # Load k-mer matrix of sources as dataframe
        partition = dd.read_table(p_sources + "matrices/matrix_100.pa.txt", header=None, sep=" ",
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
        w["Sink"] = [sink]
        c_classes = classes + ["Unknown"]
        end = time.time()
        w["Running time (s)"] = [np.round(end - start, decimals=4)]
        result = pd.concat([result, w])
        result[["p_" + c for c in c_classes]] = result.apply(find_proportions, classes=c_classes, axis=1)
        result["decOM_max"] = result[c_classes].astype(np.int64).apply(find_max,axis=1)
        result.to_csv(output + "decOM_output.csv", index=False)
        print_status("Contamination assessment for sink " + sink + " was finished.")

        # Plot results
        if plot == "True":
            plot_results(sink, p_sinks, result, c_classes, output)

    except Exception as e:
        print_error(e)

    finally:
        client.close();
        client.shutdown();
        remove_files("./dask-worker-space/");
        return 1

def several_sinks(sink, p_sinks, p_sources, p_keys, t, plot, output, mem, resources ,default):
    start = time.time()
    #Which matrix of sources does the user want to use
    if default == True:
        # Load metadata from sources
        metadata = pd.read_csv(resources + "/metadata.csv")

        # Load run accession codes for sources from k-mer matrix .fof files
        colnames = pd.read_csv(resources + "/kmtricks.fof", sep=" : ",
                                header=None, names=["Run_accession", "to_drop"], engine="python")
        colnames.drop(columns="to_drop", inplace=True)
    else:
        # Load metadata from sources
        metadata = pd.read_csv(resources + "/aOralOut_metadata.csv")

        # Load run accession codes for sources from k-mer matrix .fof files
        colnames = pd.read_csv(resources + "/aOralOut_kmtricks.fof", sep=" : ",
                                header=None, names=["Run_accession", "to_drop"], engine="python")
        colnames.drop(columns="to_drop", inplace=True)
    # Create folder of results
    subprocess.call(["mkdir", output])

    # Initialize dask
    cluster = LocalCluster(memory_limit=mem, n_workers=int(t))
    client = Client(cluster)
    print_status("Client was set")
    print_status(client)

    # Parse sources and classes
    sources = list(colnames["Run_accession"])
    classes = sorted(list(set(metadata["True_label"])))

    # Sort metadata according to column order in matrix DataFrame
    sorted_metadata = pd.DataFrame(columns=metadata.columns)
    for j in sources:
        sorted_metadata = pd.concat([sorted_metadata, metadata[metadata["Run_accession"] == j]])
    sorted_metadata.reset_index(drop=True, inplace=True)

    # Build result dataframe
    result = pd.DataFrame(columns=classes + ["Unknown", "Running time (s)", "Sink"])

    # Start using dask

    try:
        # Load k-mer matrix of sources as dataframe
        partition = dd.read_table(p_sources + "matrices/matrix_100.pa.txt", header=None, sep=" ",
                                    names=["Kmer"] + list(colnames["Run_accession"]))

        # Drop K-mer column
        partition_array = partition.drop(["Kmer"], axis=1)

        # Define M_s matrix of sources
        M_s = partition_array.values
        M_s.compute_chunk_sizes()

        print_status("Chunk sizes for the M_s matrix were computed")

        # Create vector of sources
        sinks = open(p_sinks).read().splitlines()
        for s in sinks:
            start_sink = time.time()

            # Create vector of sources
            create_vector(output_path=output, path_to_sources=p_sources, key=p_keys + s + ".fof", accession=s,
                                t=t)

            # Define paths from output of kmtricks filter and kmtricks aggregate
            path_sink = output + s + "_vector/matrices/100.vec"
            path_missing_kmers = output + s + "_vector/counts/partition_100/" + s + "_missing.txt"

            if not os.path.isfile(path_sink) or not os.path.isfile(path_missing_kmers):
                print_error("Sink vector for " + s + " could not be created, verify your input files are correct")
                return 1
            else:
                print_status("Sink vector for " + s + " was created")

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
            w["Sink"] = [s]
            end_sink = time.time()
            time_sink = end_sink - start_sink
            w["Running time (s)"] = np.round(time_sink, decimals=4)
            result = pd.concat([result, w])
            print_status("Contamination assessment for sink " + s + " was finished.")
        c_classes = classes + ["Unknown"]
        result[["p_" + c for c in c_classes]] = result.apply(find_proportions, classes=c_classes, axis=1)
        result["decOM_max"] = result[c_classes].astype(np.int64).apply(find_max,axis=1)
        result.to_csv(output + "decOM_output.csv", index=False)
        end = time.time()
        print_status("Sinks were analyzed in " + str(np.round(end - start, decimals=4)) + " seconds")

        # Plot results
        if plot == "True":
            plot_results(sink, p_sinks, result, c_classes, output)

    except Exception as e:
        print_error(e)

    finally:
        client.close();
        client.shutdown();
        remove_files("./dask-worker-space/");
        return 1