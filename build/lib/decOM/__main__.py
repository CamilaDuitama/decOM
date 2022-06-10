#!/usr/bin/env python3
import time
from dask.distributed import Client, LocalCluster
import dask.dataframe as dd
import dask.array as da
from importlib_resources import files
import argparse
import plotly.io as pio
from decOM import data
from decOM.__version__ import __version__
from decOM.modules.utils import *
from decOM.modules.sink import create_vector, plot_results

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
    start = time.time()
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
                        help="path to folder downloaded from https://zenodo.org/record/6620731/files/no_aOral_as_sources.tar.gz"
                             ".tar.gz",
                        required=True)
    keys_parser.add_argument("-k", "--key", dest='KEY', help="filtering key (a kmtricks fof with only one sample). "
                                                             "When this argument is set, -s/--sink must be defined too.")
    keys_parser.add_argument("-p_keys", "--path_keys", dest='PATH_KEYS',
                             help=" Path to folder with filtering keys (a kmtricks fof with only one sample)."
                                  "You should have as many .fof files as sinks."
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
                        required=False, default=True)

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
    checked_input = check_input(sink, p_sinks, p_sources, key, p_keys, t, plot, output, mem)
    if checked_input == 1:
        return 1
    else:
        sink, p_sinks, p_sources, key, p_keys, t, plot, output, mem = checked_input

    print_status("Starting decOM version: " + str(_version()))

    # If input is exactly one sink
    if sink is not None:
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

            # Load metadata from sources
            metadata = pd.read_csv(resources + "/metadata.csv")

            # Load run accession codes for sources from k-mer matrix .fof files
            colnames = pd.read_csv(resources + "/kmtricks.fof", sep=" : ",
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
            result.to_csv(output + "decOM_output.csv", index=False)
            print_status("Contamination assessment for sink " + sink + " was finished.")

            # Plot results
            if plot == "True":
                plot_results(sink, p_sinks, result, classes, output)

        except Exception as e:
            print_error(e)

        finally:
            client.close();
            client.shutdown();
            remove_files("./dask-worker-space/");
            return 1

    elif p_sinks is not None:

        # Create folder of results
        subprocess.call(["mkdir", output])

        # Initialize dask
        cluster = LocalCluster(memory_limit=mem, n_workers=int(t))
        client = Client(cluster)
        print_status("Client was set")
        print_status(client)

        # Load metadata from sources
        metadata = pd.read_csv(resources + "/metadata.csv")

        # Load run accession codes for sources from k-mer matrix .fof files
        colnames = pd.read_csv(resources + "/kmtricks.fof", sep=" : ",
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


if __name__ == "__main__":
    if os.path.isfile(os.path.relpath("decOM.log")):
        remove_files('decOM.log')
    open('decOM.log', 'w')
    sys.exit(main())
