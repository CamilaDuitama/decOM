#!/usr/bin/env python3
from asyncio.subprocess import PIPE
from xmlrpc.client import Boolean, boolean
from .utils import print_error,print_status, print_warning, plot_results, find_proportions,find_max,remove_files
import os
from os import access, path
import pandas as pd
import numpy as np
from dask.distributed import Client, LocalCluster
import dask.dataframe as dd
import dask.array as da
import time
import glob
import subprocess

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
        subprocess.run(["rm", "-rf", output])
    try:    
        filter = subprocess.run(
            ["kmtricks", "filter", "--in-matrix", path_to_sources, "--key", key, "--output", output, "--out-types", "k,v"],capture_output=True,text=True)
        print_status("Status for kmtricks filter for sample "+accession+"\n"+filter.stderr[:-1])
    except Exception as e:
        print_error(e)
        return 1
    try:
        aggregate = subprocess.run(
            ["kmtricks", "aggregate", "-t", str(t), "--run-dir", output, "--count", accession + ":kmer", "--output",
            output + "counts/" + accession + "_missing.txt"],capture_output=True,text=True)
        print_status("Status for kmtricks aggregate for sample "+accession+"\n"+aggregate.stderr[:-1])

    except Exception as e:
        print_error(e)
        return 1
    return

def concat_vectors(output:str,accession:str):
    """concat_vectors is a function to concatenate all the .vec files generated after using kmtricks filter on matrix of sources.
    Useful only for when the user inputs their own matrix.

    Args:
        output (str): Path to output folder, where you want decOM to write the results.
        accession (str): Identifier of sink being processed

    Returns:
        None
    """
    try:
        output_to_vectors = output + accession + "_vector/matrices/"
        files=glob.glob(output_to_vectors+"*.vec")
        if len(files)!=0:
            try:
                with open(output_to_vectors+"sink.vec", "w") as outfile:
                    subprocess.run(["cat"]+files,stdout=outfile,check=True)
            except Exception as e:
                print_error(e)
                return 1
        else:
            print_warning(".vec files in "+ output_to_vectors + " folder could not be concatenated as there are no .vec files in the folder.")
            return 1
    except Exception as e:
        print_error(e)
        return 1
    return

def one_sink(sink:str, p_sinks:str, p_sources:str, key:str, t:int, plot:bool, output:str, mem:str, resources:str, default:bool):
    """one_sink is the function of decOM in charge of processing one sink only.

    Args:
        sink (str): Name of the sink being analysed.
        It must be the same as the first element of key.fof. When this argument is set, -k/--key must be defined too
        p_sinks (str): .txt file with a list of sinks limited by a newline (\n).
        When this argument is set, -p_keys/--path_keys must be defined too.
        p_sources (str): path to folder downloaded from zenodo with sources
        key (str): filtering key (a kmtricks fof with only one sample). When this argument is set, -s/--sink must be defined too.
        p_keys (str): Path to folder with filtering keys (a kmtricks fof with only one sample).
        You should have as many .fof files as sinks.When this argument is set, -p_sinks/--path_sinks must be defined too.
        t (int): Number of threads to use.
        plot (str): True if you want a plot (in pdf and html format) with the source proportions of the sink, else False
        output (str): Path to output folder, where you want decOM to write the results.
        mem (str): Memory user would like to allocate for this process.
        resources (str): Path to data folder of resources within decOM package.
        default (boolean): True if user wants to run standard decOM, False if user wants to run decOM-aOralOut

    """
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
    concat_vectors(output=output,accession=sink)


    # Define paths from output of kmtricks filter and kmtricks aggregate
    path_sink = output + sink + "_vector/matrices/sink.vec"
    path_missing_kmers = output + sink + "_vector/counts/" + sink + "_missing.txt"

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

def several_sinks(sink:str, p_sinks:str, p_sources:str, p_keys:str, t:int, plot:bool, output:str, mem:str, resources:str ,default:bool):
    """several_sinks is the function of decOM in charge of processing a list of sinks.

    Args:
        sink (str): Name of the sink being analysed.
        It must be the same as the first element of key.fof. When this argument is set, -k/--key must be defined too
        p_sinks (str): .txt file with a list of sinks limited by a newline (\n).
        When this argument is set, -p_keys/--path_keys must be defined too.
        p_sources (str): path to folder downloaded from zenodo with sources
        key (str): filtering key (a kmtricks fof with only one sample). When this argument is set, -s/--sink must be defined too.
        p_keys (str): Path to folder with filtering keys (a kmtricks fof with only one sample).
        You should have as many .fof files as sinks.When this argument is set, -p_sinks/--path_sinks must be defined too.
        t (int): Number of threads to use.
        plot (str): True if you want a plot (in pdf and html format) with the source proportions of the sink, else False
        output (str): Path to output folder, where you want decOM to write the results.
        mem (str): Memory user would like to allocate for this process.
        resources (str): Path to data folder of resources within decOM package.
        default (boolean): True if user wants to run standard decOM, False if user wants to run decOM-aOralOut

    """
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

        # Define list of labels for sources
        labels = [sorted_metadata["True_label"][x] for x in range(len(sources))]

        # Define matrix H (one hot-encoding of labels)
        H = da.from_array(pd.get_dummies(labels, columns=classes).values)

        #Create matrix M_s * H
        Ms_dot_H=np.matmul(M_s,H)
        Ms_dot_H=Ms_dot_H.persist()

        print_status("Persist of Ms_dot_H was finished ")

        # Create vector of sources
        sinks = open(p_sinks).read().splitlines()
        for s in sinks:
            start_sink = time.time()

            # Create vector of sources
            create_vector(output_path=output, path_to_sources=p_sources, key=p_keys + s + ".fof", accession=s,
                                t=t)
            concat_vectors(output=output,accession=s)


            # Define paths from output of kmtricks filter and kmtricks aggregate
            path_sink = output + s + "_vector/matrices/sink.vec"
            path_missing_kmers = output + s + "_vector/counts/" + s + "_missing.txt"

            if not os.path.isfile(path_sink) or not os.path.isfile(path_missing_kmers):
                print_warning("Sink vector for " + s + " could not be created, verify your input files for that sample are correct")
                continue
            else:
                print_status("Sink vector for " + s + " was created")

            # Create new vector for sink
            s_t = dd.read_table(path_sink, header=None, names=["pa"])
            s_t = s_t["pa"]
            s_t = s_t.values
            s_t.compute_chunk_sizes()

            # Define s_t (vector of sink)
            s_t = s_t.persist()

            # Construct vector w (number of balls that go into each bin, see eq. 2 in paper)
            w = np.matmul(s_t, Ms_dot_H)
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

def LOO(p_sinks, p_sources, p_keys, t, plot, output, mem, resources):
    
    start = time.time()

    # Create folder of results
    subprocess.call(["mkdir", output])

    # Initialize dask
    cluster = LocalCluster(memory_limit=mem, n_workers=int(t))
    client = Client(cluster)
    print_status("Client was set")
    print_status(client)

    # Build result dataframe from unchanged metadata dataframe
    metadata = pd.read_csv(resources + "/metadata.csv")
    classes = sorted(list(set(metadata["True_label"])))
    result = pd.DataFrame(columns=classes + ["Unknown", "Running time (s)", "Sink"])

    try:
        # Create vector of sources
        sinks = open(p_sinks).read().splitlines()

        for s in sinks:

            # Define paths from output of kmtricks filter and kmtricks aggregate
            path_sink = output + s + "_vector/matrices/sink.vec"
            path_missing_kmers = output + s + "_vector/counts/" + s + "_missing.txt"  

            if not os.path.isfile(path_sink) or not os.path.isfile(path_missing_kmers):
                # Create vector of sources
                create_vector(output_path=output, path_to_sources=p_sources, key=p_keys + s + ".fof", accession=s,
                                    t=t)
                concat_vectors(output=output,accession=s)


            if not os.path.isfile(path_sink) or not os.path.isfile(path_missing_kmers):
                print_error("Sink vector for " + s + " could not be created, verify your input files are correct")
                return 1
            else:
                print_status("Sink vector for " + s + " exists.")

        for s in sinks:
            
            start_sink = time.time()

            # Define paths from output of kmtricks filter and kmtricks aggregate
            path_sink = output + s + "_vector/matrices/sink.vec"
            path_missing_kmers = output + s + "_vector/counts/" + s + "_missing.txt"  


            # Load metadata from sources
            metadata = pd.read_csv(resources + "/metadata.csv")
            metadata = metadata[metadata["Run_accession"] != s]

            # Load run accession codes for sources from k-mer matrix .fof files
            colnames = pd.read_csv(resources + "/kmtricks.fof", sep=" : ",
                            header=None, names=["Run_accession", "to_drop"], engine="python")
            colnames.drop(columns="to_drop", inplace=True)

            # Parse sources and classes
            sources = [x for x in colnames["Run_accession"] if x != s]
            classes = sorted(list(set(metadata["True_label"])))

            # Sort metadata according to column order in matrix DataFrame
            sorted_metadata = pd.DataFrame(columns=metadata.columns)
            for j in sources:
                sorted_metadata = pd.concat([sorted_metadata, metadata[metadata["Run_accession"] == j]])
            sorted_metadata.reset_index(drop=True, inplace=True)

            # Load k-mer matrix of sources as dataframe
            partition = dd.read_table(p_sources + "matrices/matrix_100.pa.txt", header=None, sep=" ",
                                        names=["Kmer"] + list(colnames["Run_accession"]))

            # Drop K-mer column
            partition_array = partition.drop(["Kmer",s], axis=1)

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
            w["Sink"] = [s]
            end_sink = time.time()
            time_sink = end_sink - start_sink
            w["Running time (s)"] = np.round(time_sink, decimals=4)
            result = pd.concat([result, w])
            print_status("Contamination assessment for sink " + s + " was finished.")
            result.to_csv(output + "decOM_output.csv", index=False)
        c_classes = classes + ["Unknown"]
        result[["p_" + c for c in c_classes]] = result.apply(find_proportions, classes=c_classes, axis=1)
        result["decOM_max"] = result[c_classes].astype(np.int64).apply(find_max,axis=1)
        result.to_csv(output + "decOM_output.csv", index=False)
        end = time.time()
        print_status("Sinks were analyzed in " + str(np.round(end - start, decimals=4)) + " seconds")

        # Plot results
        if plot == "True":
            sink=None
            plot_results(sink, p_sinks, result, c_classes, output)

    except Exception as e:
        print_error(e)

    finally:
        client.close();
        client.shutdown();
        remove_files("./dask-worker-space/");
        return 1

def CV(p_sinks, p_sources, p_keys, t, plot, output, mem, resources, fold): 
    
    start = time.time()

    # Create folder of results
    subprocess.call(["mkdir", output])

    # Initialize dask
    cluster = LocalCluster(memory_limit=mem, n_workers=int(t))
    client = Client(cluster)
    print_status("Client was set")
    print_status(client)

    # Build result dataframe from unchanged metadata dataframe
    metadata = pd.read_csv(resources + "/metadata_sources_"+fold+"_fold.csv")
    classes = sorted(list(set(metadata["True_label"])))
    result = pd.DataFrame(columns=classes + ["Unknown", "Running time (s)", "Sink"])

    # Parse sinks
    sinks = open(p_sinks).read().splitlines()

    # Load run accession codes for sources from k-mer matrix .fof files
    colnames = pd.read_csv(p_sources + "/kmtricks.fof", sep=" : ",
                    header=None, names=["Run_accession", "to_drop"], engine="python")
    colnames.drop(columns="to_drop", inplace=True)

    # Parse sources and classes
    sources = [x for x in colnames["Run_accession"] if x not in sinks]
    classes = sorted(list(set(metadata["True_label"])))

    # Sort metadata according to column order in matrix DataFrame
    sorted_metadata = pd.DataFrame(columns=metadata.columns)
    for j in sources:
        sorted_metadata = pd.concat([sorted_metadata, metadata[metadata["Run_accession"] == j]])
    sorted_metadata.reset_index(drop=True, inplace=True)

    # Load k-mer matrix of sources as dataframe
    partition = dd.read_table(p_sources + "matrices/matrix_100.pa.txt", header=None, sep=" ",
                                names=["Kmer"] + list(colnames["Run_accession"]))

    # Drop K-mer column
    partition_array = partition.drop(["Kmer"], axis=1)

    # Define M_s matrix of sources
    M_s = partition_array.values
    M_s.compute_chunk_sizes()

    print_status("Chunk sizes for the M_s matrix were computed")

    try:
        # Create vector of sources
        for s in sinks:
            start_sink = time.time()

            # Create vector of sources
            create_vector(output_path=output, path_to_sources=p_sources, key=p_keys + s + ".fof", accession=s,
                                t=t)
            concat_vectors(output=output,accession=s)


            # Define paths from output of kmtricks filter and kmtricks aggregate
            path_sink = output + s + "_vector/matrices/sink.vec"
            path_missing_kmers = output + s + "_vector/counts/" + s + "_missing.txt"

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
            result.to_csv(output + "decOM_output_fold_"+fold+".csv", index=False)
        c_classes = classes + ["Unknown"]
        result[["p_" + c for c in c_classes]] = result.apply(find_proportions, classes=c_classes, axis=1)
        result["decOM_max"] = result[c_classes].astype(np.int64).apply(find_max,axis=1)
        result.to_csv(output + "decOM_output_fold_"+fold+".csv", index=False)
        end = time.time()
        print_status("Sinks were analyzed in " + str(np.round(end - start, decimals=4)) + " seconds")

        # Plot results
        if plot == "True":
            sink=None
            plot_results(sink, p_sinks, result, c_classes, output)

    except Exception as e:
        print_error(e)

    finally:
        client.close();
        client.shutdown();
        remove_files("./dask-worker-space/");
        return 1
        
def one_sink_MST(sink:str, p_sinks:None, p_sources:str, m:str, key:str, t:int, plot:bool, output:str, mem:str):
    """one_sink_MST is the function in charge of processing one sink using decOM-MST feature.

    Args:
        sink (str): Name of the sink being analysed.
        It must be the same as the first element of key.fof. When this argument is set, -k/--key must be defined too

        p_sinks (None): Must be None as we are analysing one sample only.

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
    """

    start = time.time()
    #Upload map.csv file
    metadata = pd.read_csv(m)

    # Load run accession codes for sources from k-mer matrix .fof files
    colnames = pd.read_csv(p_sources + "/kmtricks.fof", sep=" : ",
                            header=None, names=["SampleID", "to_drop"], engine="python")
    colnames.drop(columns="to_drop", inplace=True)

    # Create folder of results
    subprocess.call(["mkdir", output])

    # Create vector of sources
    create_vector(output_path=output, path_to_sources=p_sources, key=key, accession=sink, t=t)
    concat_vectors(output=output,accession=sink)

    # Define paths from output of kmtricks filter and kmtricks aggregate
    path_sink = output + sink + "_vector/matrices/sink.vec"
    path_missing_kmers = output + sink + "_vector/counts/" + sink + "_missing.txt"

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
        sources = list(colnames["SampleID"])
        classes = sorted(list(set(metadata["Env"])))

        # Sort metadata according to column order in matrix DataFrame
        sorted_metadata = pd.DataFrame(columns=metadata.columns)
        for j in sources:
            sorted_metadata = pd.concat([sorted_metadata, metadata[metadata["SampleID"] == j]])
        sorted_metadata.reset_index(drop=True, inplace=True)

        # Build result dataframe
        result = pd.DataFrame(columns=classes + ["Unknown", "Running time (s)", "Sink"])

        # Start using dask:
        # Load k-mer matrix of sources as dataframe
        partition = dd.read_table(p_sources + "matrices/matrix.pa.txt", header=None, sep=" ",
                                    names=["Kmer"] + list(colnames["SampleID"]))

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
        labels = [sorted_metadata["Env"][x] for x in range(len(sources))]

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

def several_sinks_MST(sink:None, p_sinks:str, p_sources:str, m:str, p_keys:str, t:int, plot:bool, output:str, mem:str):
    """several_sinks_MST is the function in charge of processing a list of sinks using decOM-MST feature.

    Args:
        sink (str): Must be None as we are analysing a list of samples

        p_sinks (str): .txt file with a list of sinks limited by a newline (\n).
        When this argument is set, -p_keys/--path_keys must be defined too.

        p_sources (str): Path to matrix of sources built with kmtricks.

        m (str) : Path to map.csv file with 2 columns : SampleID and Env. 
        Each source used to build the matrix of sources must be in this table and must have a corresponding environment label.

        key (str): filtering key (a kmtricks fof with only one sample). When this argument is set, -s/--sink must be defined too.

        p_keys (str): Path to folder with filtering keys (a kmtricks fof with only one sample).
        You should have as many .fof files as sinks.When this argument is set, -p_sinks/--path_sinks must be defined too.

        t (str): Number of threads to use.

        plot (str): True if you want a plot (in pdf and html format) with the source proportions of the sink, else False.

        output (str): Path to output folder, where you want decOM to write the results.

        mem (str): Memory user would like to allocate for this process.
    """

    start = time.time()

    #Upload map.csv file
    metadata = pd.read_csv(m)
    
    # Load run accession codes for sources from k-mer matrix .fof files
    colnames = pd.read_csv(p_sources + "kmtricks.fof", sep=" : ",
                                header=None, names=["SampleID", "to_drop"], engine="python")
    colnames.drop(columns="to_drop", inplace=True)

    # Create folder of results
    subprocess.call(["mkdir", output])

    # Initialize dask
    cluster = LocalCluster(memory_limit=mem, n_workers=int(t))
    client = Client(cluster)
    print_status("Client was set")
    print_status(client)

    # Parse sources and classes
    sources = list(colnames["SampleID"])
    classes = sorted(list(set(metadata["Env"])))

    # Sort metadata according to column order in matrix DataFrame
    sorted_metadata = pd.DataFrame(columns=metadata.columns)
    for j in sources:
        sorted_metadata = pd.concat([sorted_metadata, metadata[metadata["SampleID"] == j]])
    sorted_metadata.reset_index(drop=True, inplace=True)

    # Build result dataframe
    result = pd.DataFrame(columns=classes + ["Unknown", "Running time (s)", "Sink"])

    # Start using dask

    try:
        # Load k-mer matrix of sources as dataframe
        partition = dd.read_table(p_sources + "matrices/matrix.pa.txt", header=None, sep=" ",
                                    names=["Kmer"] + list(colnames["SampleID"]))

        # Drop K-mer column
        partition_array = partition.drop(["Kmer"], axis=1)

        # Define M_s matrix of sources
        M_s = partition_array.values
        M_s.compute_chunk_sizes()

        print_status("Chunk sizes for the M_s matrix were computed")

        # Define list of labels for sources
        labels = [sorted_metadata["Env"][x] for x in range(len(sources))]

        # Define matrix H (one hot-encoding of labels)
        H = da.from_array(pd.get_dummies(labels, columns=classes).values)

        #Create matrix M_s * H
        Ms_dot_H=np.matmul(M_s,H)
        Ms_dot_H=Ms_dot_H.persist()

        print_status("Persist of Ms_dot_H was finished ")

        # Create vector of sources
        sinks = open(p_sinks).read().splitlines()
        for s in sinks:
            start_sink = time.time()

            # Create vector of sources
            create_vector(output_path=output, path_to_sources=p_sources, key=p_keys + s + ".fof", accession=s,
                                t=t)
            concat_vectors(output=output,accession=s)
            
            # Define paths from output of kmtricks filter and kmtricks aggregate
            path_sink = output + s + "_vector/matrices/sink.vec"
            path_missing_kmers = output + s + "_vector/counts/" + s + "_missing.txt"

            if not os.path.isfile(path_sink) or not os.path.isfile(path_missing_kmers):
                print_warning("Sink vector for " + s + " could not be created, verify your input files for that sample are correct")
                continue
            else:
                print_status("Sink vector for " + s + " was created")

            # Create new vector for sink
            s_t = dd.read_table(path_sink, header=None, names=["pa"])
            s_t = s_t["pa"]
            s_t = s_t.values
            s_t.compute_chunk_sizes()

            # Define s_t (vector of sink)
            s_t = s_t.persist()

            # Construct vector w (number of balls that go into each bin, see eq. 2 in paper)
            w = np.matmul(s_t, Ms_dot_H)
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
