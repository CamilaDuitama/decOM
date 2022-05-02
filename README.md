
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

## Before running decOM

The users of OM can represent their own metagenomic sample as a presence/absence vector of k-mers using kmtricks, and compare this new sink against the collection of sources we have put together. This means that **before** running `decOM` you must first download the folder [ decOM_sources.tar.gz](https://zenodo.org/record/6511305/files/decOM_sources.tar.gz) and decompress it
```
wget https://zenodo.org/record/6511305/files/decOM_sources.tar.gz
tar -xf decOM_sources.tar.gz
```

## Test
You can test if `decOM`  is working by using one of the aOral samples present in the `test/sample/` folder, ex: SRR13355787. 
```
decOM -s SRR13355810 -p_sources decOM_sources/ -k sample/SRR13355810_key.fof -mem 10GB -t 5
```
*Note*: The final memory allocated for each run of `decOM` will be your input in -mem times the number of cores. In the previous run we used 10GB * 5 = 50 GB.


## Output files
`decOM` will output one .csv file with the k-mer counts and proportions and a barplot if indicated by the user

```
├──{sink}_OM_output.csv  
├──result_plot_{sink}.pdf
```
## Example

You can input your a fastq/fasta file from your own experiment, you can find an ancient sample of interest from the [AncientMetagenomeDir](https://github.com/SPAAM-community/AncientMetagenomeDir) or from the [SRA](https://sra-explorer.info/).

Once you have downloaded the folder with the matrix of sources  [ decOM_sources.tar.gz](https://zenodo.org/record/6511305/files/decOM_sources.tar.gz) , and your fastq file(s) of interest, you have to create a `key.fof` file per sample of interest, which from now one we will call sink (s). The `key.fof` has one line of text depending on your type of data:

**- Paired-end :**
	 `s : path/to/file/s_1.fastq.gz`

**-  Single-end:**
	`s : path/to/file/s_1.fastq.gz;  path/to/file/s_2.fastq.gz `

As you now have the name and fastq file of sink (s), the folder with the matrix of sources and the key file simply run decOM as follows:

```decOM -s s -p_sources decOM_sources/ -k s_key.fof -mem {mem} -t {t}```

## Command line options

```
usage: modules [-h] -s SINK -p_sources PATH_SOURCES -k KEY -mem MEMORY -t THREADS [-p PLOT] [-V]

Microbial source tracking for contamination assessment of ancient oral samples using k-mer-based methods

optional arguments:
  -h, --help            show this help message and exit
  -s SINK, --sink SINK  Write down the name of your sink
  -p_sources PATH_SOURCES, --path_sources PATH_SOURCES
                        path to folder downloaded from https://zenodo.org/record/6511305#.YnAq3i8RoUE
  -k KEY, --key KEY     filtering key (a kmtricks fof with only one sample).
  -mem MEMORY, --memory MEMORY
                        Write down how much memory you want to use. Ex: 50GiB
  -t THREADS, --threads THREADS
                        Number of threads to use. Ex: 10
  -p PLOT, --plot PLOT  True if you want a plot with the source proportions of the sink, else False
  -V, --version         Show version number and exit


```

