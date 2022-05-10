
# decOM: Microbial source tracking for contamination assessment of ancient oral samples using k-mer-based methods

`decOM`  is a high-accuracy microbial source tracking method that is suitable for contamination quantification in paleogenomics, namely the analysis of collections of possibly contaminated ancient oral metagenomic data sets. In simple words, if you want to know how contaminated your ancient oral metagenomic sample is, this tool will help :)

![pipeline_version2](https://raw.githubusercontent.com/CamilaDuitama/decOM/master/images/pipeline_version2.png?token=GHSAT0AAAAAABNF5TKQVZ7GWFJNDVX6VDVAYSGEMGA)

+ [System requirements](#system-requirements)
+ [Installation](#installation)
+ [Before running decOM](#before-running-decom)
+ [Test](#test)
+ [Output files](#output-files)
+ [Example](#example)
+ [Command-line options](#command-line-options)

## System requirements

`decOM`  has been developed and tested under a Linux environment.
It requires certain packages/tools in order to be installed/used: 
+ [miniconda3](https://conda.io/en/latest/miniconda.html)

## Installation

Install `decOM` through conda:
```
git clone https://github.com/CamilaDuitama/decOM.git
cd decOM
conda env create -n decOM --file environment.yml
conda activate decOM
```
To make the ``decOM`` command available, it is advised to include the absolute path of `decOM`  in your PATH environment variable by adding the following line to your `~/.bashrc` file:

```
export PATH=/absolute/path/to/decOM:${PATH}
```

## Before running decOM

**BEFORE** running `decOM` you must first download the folder [ decOM_sources.tar.gz](https://zenodo.org/record/6513520/files/decOM_sources.tar.gz) and decompress it. You can either follow the link or use wget (it has to be installed in your computer first):
```
wget https://zenodo.org/record/6513520/files/decOM_sources.tar.gz
tar -xf decOM_sources.tar.gz
``` 
If you did not use wget to download the matrix of sources and instead followed the link, make sure you know where the path to your file is and type it accordingly in the upcoming commands whenever `p_sources` is needed

## Test
You can test if `decOM`  is working by using one of the aOral samples present in the `test/sample/` folder, ex: SRR13355787. 
```
decOM -s SRR13355787 -p_sources decOM_sources/ -k tests/sample/SRR13355787.fof -mem 10GB -t 5 -o decOM_output/
```
*Note*: The final memory allocated for each run of `decOM` will be your input in -mem times the number of cores. In the previous run we used 10GB * 5 = 50 GB.


## Output files
`decOM` will output one .csv file with the k-mer counts and proportions, a folder with the vector representing the sample of interest, from now on called sink (s), and a barplot if indicated by the user.

```
decOM_output/
├──{s}_OM_output.csv  
├──result_plot_{s}.pdf
├──{s}_vector/
```
## Example

You can use as input your fastq/fasta file from your own experiment, you can download an ancient oral sample of interest from the [AncientMetagenomeDir](https://github.com/SPAAM-community/AncientMetagenomeDir) or from the [SRA](https://sra-explorer.info/).
The users of `decOM` can represent their own metagenomic sample as a presence/absence vector of k-mers using kmtricks. This sink can be compared against the collection of sources we have put together.

Once you have downloaded the folder with the [matrix of sources](#before-running-decom) and the fastq file(s) of your sink(s), you have to create a `key.fof` file per sink. 
The `key.fof` has one line of text depending on your type of data:

**-Paired-end :**
	 `s : path/to/file/s_1.fastq.gz`

**-Single-end:**
	`s : path/to/file/s_1.fastq.gz;  path/to/file/s_2.fastq.gz `

*Note*: As `decOM` relies on [`kmtricks`](https://github.com/tlemane/kmtricks), you might use a FASTA or FASTQ format, gzipped or not. 
Which means you have to change the `key.fof` file accordingly.

Since you now have the fasta/fastq file of your sink, the folder with the matrix of sources and the key file, simply run decOM as follows:

```decOM -s {SINK} -p_sources decOM_sources/ -k {KEY.FOF} -mem {MEMORY} -t {THREADS} -o {OUTPUT}```

## Command line options

```
usage: modules [-h] -s SINK -p_sources PATH_SOURCES -k KEY -mem MEMORY -t THREADS -o OUTPUT [-p PLOT] [-V]

Microbial source tracking for contamination assessment of ancient oral samples using k-mer-based methods

optional arguments:
  -h, --help            show this help message and exit
  -s SINK, --sink SINK  Write down the name of your sink
  -p_sources PATH_SOURCES, --path_sources PATH_SOURCES
                        path to folder downloaded from https://zenodo.org/record/6513520/files/decOM_sources.tar.gz
  -k KEY, --key KEY     filtering key (a kmtricks fof with only one sample).
  -mem MEMORY, --memory MEMORY
                        Write down how much memory you want to use for this process. Ex: 20GB
  -t THREADS, --threads THREADS
                        Number of threads to use. Ex: 5
  -o OUTPUT, --output OUTPUT
                        Path to output folder, where you want decOM to write the results
  -p PLOT, --plot PLOT  True if you want a plot with the source proportions of the sink, else False
  -V, --version         Show version number and exit

```
