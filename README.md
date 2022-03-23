# decOM: Microbial source tracking for contamination assessment of ancient oral samples using k-mer-based methods

decOM is a high-accuracy microbial source tracking method that is suitable for contamination quantification in paleogenomics, namely the analysis of collections of possibly contaminated ancient oral metagenomic data sets.

+ [System requirements](#system-requirements)
+ [Installation](#installation)
+ [Usage](#usage)
+ [Output files](#output-files)
+ [Example](#example)
+ [Command-line options](#command-line-options)
+ [Reference](#reference)

## System requirements

`decOM`  has been developed and tested under a Linux environment.
It requires certain packages/tools in order to be installed/used: 
+ [miniconda3](https://conda.io/en/latest/miniconda.html)

## Installation

Install `decOM` through conda:
```
conda install -c camiladuitama decom
```
To make the ``decOM`` command available, it is advised to include the absolute path of `decOM`  in your PATH environment variable by adding the following line to your `~/.bashrc` file:

```
export PATH=/absolute/path/to/decOM:${PATH}
```

## Usage


## Output files


## Example


## Command line options

```
usage: decOM [-h] [-v] -s SINK -p_sources PATH_SOURCES -p_sink PATH_SINK -p_missing PATH_MISSING_KMERS -mem MEMORY -t THREADS [-plt PLOT]

Mandatory arguments:

-s SINK, --sink SINK  Write down the name of your sink

-p_sources PATH_SOURCES, --path_sources PATH_SOURCES

path to sources matrix. Ex: ./matrix_100.pa.txt

-p_sink PATH_SINK, --path_sink PATH_SINK

Path to sink vector, the output of kmtricks filter Ex: ./kmtricks_output/matrices/100.vec

-p_missing PATH_MISSING_KMERS, --path_missing_kmers PATH_MISSING_KMERS

Path to missing kmers, the output of kmtricks filter after using kmtricks aggregate Ex: ./kmtricks_output/count/{sink}_missing.txt

-mem MEMORY, --memory MEMORY

Write down how much memory you want to use. Ex: 500GiB

-t THREADS, --threads THREADS

Number of threads to use. Ex: 10

Optional arguments:

-plt PLOT, --plot PLOT
True if you want a plot with the source proportions of the sink, else False

Other arguments:
-h, --help  show this help message and exit
-v, --verbose increase output verbosity

```


