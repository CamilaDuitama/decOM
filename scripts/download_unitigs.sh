#!/bin/bash
#SBATCH --job-name=download_unitigs
#SBATCH --partition=seqbio
#SBATCH --time=12:00:00
#SBATCH --mem=16G
#SBATCH --cpus-per-task=8
#SBATCH --output=logs/download_unitigs_%j.out
#SBATCH --error=logs/download_unitigs_%j.err

set -e  # Exit on error
set -u  # Exit on undefined variable

# Get script directory and project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "${SCRIPT_DIR}/.." && pwd )"

# Load required modules
module load parallel

# Use system zstd instead of homebrew version
export PATH=/usr/bin:$PATH

# Configuration
ACCESSION_FILE="${PROJECT_ROOT}/data/Collection_accessions.csv"
OUTPUT_DIR="${PROJECT_ROOT}/data/unitigs"
S3_BUCKET="s3://logan-pub/u"
PARALLEL_JOBS=8

# Create output directory if it doesn't exist
mkdir -p "${PROJECT_ROOT}/logs"

# Create output directory if it doesn't exist
mkdir -p "${OUTPUT_DIR}"
cd "${OUTPUT_DIR}"

echo "======================================"
echo "Starting unitigs download and decompression"
echo "Date: $(date)"
echo "======================================"
echo "Accession file: ${ACCESSION_FILE}"
echo "Output directory: ${OUTPUT_DIR}"
echo "Parallel jobs: ${PARALLEL_JOBS}"
echo ""

# Count total accessions
TOTAL=$(wc -l < "${ACCESSION_FILE}")
echo "Total accessions to process: ${TOTAL}"
echo ""

# Function to download a single accession
download_accession() {
    local accession=$1
    local s3_path="${S3_BUCKET}/${accession}/${accession}.unitigs.fa.zst"
    local output_file="${accession}.unitigs.fa.zst"
    local decompressed_file="${accession}.unitigs.fa"
    
    # Skip if already decompressed
    if [ -f "${decompressed_file}" ]; then
        echo "[SKIP] ${accession}: Already decompressed"
        return 0
    fi
    
    # Download if compressed file doesn't exist
    if [ ! -f "${output_file}" ]; then
        echo "[DOWNLOAD] ${accession}: Starting download..."
        if aws s3 cp "${s3_path}" "${output_file}" --no-sign-request 2>/dev/null; then
            echo "[DOWNLOAD] ${accession}: Download complete ($(du -h ${output_file} | cut -f1))"
        else
            echo "[ERROR] ${accession}: Download failed"
            return 1
        fi
    else
        echo "[SKIP] ${accession}: Already downloaded"
    fi
    
    # Decompress
    if [ -f "${output_file}" ]; then
        echo "[DECOMPRESS] ${accession}: Starting decompression..."
        if zstd -d "${output_file}" --rm 2>/dev/null; then
            echo "[DECOMPRESS] ${accession}: Decompression complete ($(du -h ${decompressed_file} | cut -f1))"
        else
            echo "[ERROR] ${accession}: Decompression failed"
            return 1
        fi
    fi
    
    return 0
}

# Export function for parallel execution
export -f download_accession
export S3_BUCKET
export OUTPUT_DIR

# Read accessions and process in parallel
echo "Starting parallel download and decompression..."
echo ""

cat "${ACCESSION_FILE}" | parallel -j ${PARALLEL_JOBS} --line-buffer download_accession {}

echo ""
echo "======================================"
echo "Processing complete!"
echo "Date: $(date)"
echo "======================================"
echo ""

# Summary statistics
echo "Summary:"
echo "--------"
DOWNLOADED=$(find . -name "*.unitigs.fa" | wc -l)
COMPRESSED=$(find . -name "*.unitigs.fa.zst" | wc -l)
TOTAL_SIZE=$(du -sh . | cut -f1)

echo "Decompressed files: ${DOWNLOADED}"
echo "Compressed files remaining: ${COMPRESSED}"
echo "Total disk usage: ${TOTAL_SIZE}"
echo ""

# List any failed downloads
EXPECTED=${TOTAL}
ACTUAL=${DOWNLOADED}
if [ ${ACTUAL} -lt ${EXPECTED} ]; then
    echo "WARNING: Expected ${EXPECTED} files but only found ${ACTUAL}"
    echo "Checking for missing accessions..."
    
    # Create list of successfully downloaded accessions
    find . -name "*.unitigs.fa" -exec basename {} .unitigs.fa \; | sort > downloaded_accessions.txt
    
    # Compare with original list
    sort "${ACCESSION_FILE}" > expected_accessions.txt
    comm -23 expected_accessions.txt downloaded_accessions.txt > missing_accessions.txt
    
    MISSING=$(wc -l < missing_accessions.txt)
    echo "Missing accessions: ${MISSING}"
    if [ ${MISSING} -gt 0 ]; then
        echo "List of missing accessions saved to: missing_accessions.txt"
        echo "First 10 missing:"
        head -10 missing_accessions.txt
    fi
    
    rm -f expected_accessions.txt
else
    echo "SUCCESS: All accessions downloaded successfully!"
fi

echo ""
echo "Done!"
