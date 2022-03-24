# decOM: Microbial source tracking for contamination assessment of ancient oral samples using k-mer-based methods

`decOM`  is a high-accuracy microbial source tracking method that is suitable for contamination quantification in paleogenomics, namely the analysis of collections of possibly contaminated ancient oral metagenomic data sets.

![pipeline_version2](https://raw.githubusercontent.com/CamilaDuitama/decOM/master/images/pipeline_version2.png?token=GHSAT0AAAAAABNF5TKQVZ7GWFJNDVX6VDVAYSGEMGA)

+ [System requirements](#system-requirements)
+ [Installation](#installation)
+ [Test](#usage)
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

## Test
You can test if `decOM`  is working by using one of the aOral samples present in the test folder, ex: SRR13355810. 
```
decOM -s SRR13355810 -p_sources tests/matrix_100.pa.txt -p_sink tests/SRR13355810_output/matrices/100.vec -p_missing tests/SRR13355810_output/counts/partition_100/SRR13355810_missing.txt -mem 50GB -t 10
```
*Note*: The final memory allocated for each run of `decOM` will be your input in -mem times the number of cores. In the previous run we used 50GB * 10 = 500 GB.


## Output files
`decOM` will output one .csv file with the k-mer counts and proportions and a barplot if indicated by the user

```
├──{sink}_OM_output.csv  
├──result_plot_{sink}.pdf
```
## Example

You can input your a fastq/fasta file from your own experiment, you can find an ancient sample of interest from the [AncientMetagenomeDir](https://github.com/SPAAM-community/AncientMetagenomeDir) or from the [SRA](https://sra-explorer.info/).

#TODO

## Command line options

```
usage: decOM [-h] [-v] -s SINK -p_sources PATH_SOURCES -p_sink PATH_SINK -p_missing PATH_MISSING_KMERS -mem MEMORY -t THREADS [-plt PLOT]

Mandatory arguments:

-s, --sink  Write down the name of your sink

-p_sources, --path_sources

path to sources matrix. Ex: ./matrix_100.pa.txt

-p_sink, --path_sink

Path to sink vector, the output of kmtricks filter Ex: ./kmtricks_output/matrices/100.vec

-p_missing , --path_missing_kmers

Path to missing kmers, the output of kmtricks filter after using kmtricks aggregate Ex: ./kmtricks_output/count/{sink}_missing.txt

-mem, --memory

Write down how much memory you want to use. Ex: 50GiB

-t, --threads

Number of threads to use. Ex: 10

Optional arguments:

-plt, --plot
True if you want a plot with the source proportions of the sink, else False

Other arguments:
-h, --help  show this help message and exit

```

## Reference


