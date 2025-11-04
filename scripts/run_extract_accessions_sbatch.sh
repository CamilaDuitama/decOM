#!/bin/bash
#SBATCH --job-name=extract_oral_accessions
#SBATCH --partition=seqbio
#SBATCH --time=04:00:00
#SBATCH --mem=8G
#SBATCH --cpus-per-task=1
#SBATCH --output=extract_oral_accessions_%j.out
#SBATCH --error=extract_oral_accessions_%j.err

# Load necessary modules or activate conda environment
source ~/.bashrc
conda activate base

# Add EDirect tools to PATH if not already there
export PATH=$HOME/edirect:$PATH

# Navigate to working directory
cd /pasteur/appa/scratch/cduitama/decOM

# Run the Python script
echo "Starting extraction at $(date)"
python3 extract_oral_accessions.py
echo "Finished extraction at $(date)"
