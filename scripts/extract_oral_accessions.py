#!/usr/bin/env python3 -u
"""
Extract and expand archive_accession values for oral samples with dental calculus or tooth material.
"""

import pandas as pd
import requests
import subprocess
import sys
import time
from typing import List

# Force unbuffered output
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

def get_run_accessions_from_sample(sample_accession: str, archive: str) -> List[str]:
    """
    Get run accessions (SRR/ERR) from sample accession (SRS/ERS) using NCBI EDirect tools or ENA API.
    
    For SRA samples: Uses NCBI EDirect tools (esearch + efetch)
    For ENA samples: Uses ENA Portal API
    """
    run_accessions = []
    
    if archive == 'SRA':
        # Use NCBI EDirect tools for SRA samples
        try:
            # Method 1: Try using esearch + efetch with runinfo format
            cmd = f'esearch -db sra -query "{sample_accession}[accn]" | efetch -format runinfo'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0 and result.stdout:
                lines = result.stdout.strip().split('\n')
                # Skip header line and extract Run IDs (first column)
                for line in lines[1:]:
                    if line.strip():
                        run_id = line.split(',')[0]
                        if run_id.startswith('SRR') or run_id.startswith('ERR'):
                            run_accessions.append(run_id)
            
            # Method 2: If Method 1 fails, try docsum format
            if not run_accessions:
                cmd = f'esearch -db sra -query "{sample_accession}[accn]" | efetch -format docsum | grep -oP \'Run acc="[^"]+\' | cut -d\'"\' -f2'
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
                
                if result.returncode == 0 and result.stdout:
                    runs = result.stdout.strip().split('\n')
                    run_accessions = [r.strip() for r in runs if r.strip()]
            
            time.sleep(0.35)  # Respect NCBI rate limit (3 requests per second)
            
        except subprocess.TimeoutExpired:
            print(f"  Warning: Timeout fetching runs for {sample_accession}")
        except Exception as e:
            print(f"  Warning: Error fetching runs for {sample_accession}: {e}")
    
    elif archive == 'ENA':
        # Use ENA Portal API for ENA samples
        try:
            url = "https://www.ebi.ac.uk/ena/portal/api/filereport"
            params = {
                'accession': sample_accession,
                'result': 'read_run',
                'fields': 'run_accession',
                'format': 'json'
            }
            response = requests.get(url, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                for record in data:
                    if 'run_accession' in record:
                        run_accessions.append(record['run_accession'])
            
            time.sleep(0.2)  # Be polite to ENA servers
            
        except requests.Timeout:
            print(f"  Warning: Timeout fetching runs for {sample_accession}")
        except Exception as e:
            print(f"  Warning: Error fetching runs for {sample_accession}: {e}")
    
    return run_accessions

# Get script directory and project root
import os
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)

# Read the TSV file
input_file = os.path.join(project_root, "data/ancientmetagenome-hostassociated_samples.tsv")
output_file = os.path.join(project_root, "data/oral_dental_accessions.tsv")

print(f"Reading {input_file}...", flush=True)
df = pd.read_csv(input_file, sep='\t')

print(f"Total rows: {len(df)}", flush=True)

# Filter for oral community_type, dental calculus or tooth material, and Homo sapiens
print("Filtering data...", flush=True)
filtered_df = df[
    (df['community_type'] == 'oral') & 
    (df['material'].isin(['dental calculus', 'tooth'])) &
    (df['sample_host'] == 'Homo sapiens')
]

print(f"Filtered rows (oral + dental calculus/tooth + Homo sapiens): {len(filtered_df)}", flush=True)

# Expand the archive_accession column
# Split by comma and create a new row for each accession
print("Expanding archive accessions...", flush=True)
expanded_rows = []
for _, row in filtered_df.iterrows():
    accessions = row['archive_accession'].split(',')
    for accession in accessions:
        new_row = row.copy()
        new_row['archive_accession'] = accession.strip()
        expanded_rows.append(new_row)

# Create new dataframe with expanded rows
print("Creating expanded dataframe...", flush=True)
expanded_df = pd.DataFrame(expanded_rows)

print(f"Expanded rows: {len(expanded_df)}", flush=True)

# Fetch run accessions for each sample
print("\nFetching run accessions from NCBI/ENA APIs...", flush=True)
print(f"This may take several minutes... ({len(expanded_df[['archive_accession', 'archive']].drop_duplicates())} unique samples)", flush=True)

run_accessions_map = {}
unique_samples = expanded_df[['archive_accession', 'archive']].drop_duplicates()

for idx, (sample_acc, archive) in enumerate(zip(unique_samples['archive_accession'], unique_samples['archive']), 1):
    if idx % 10 == 0:
        print(f"  Processed {idx}/{len(unique_samples)} samples...", flush=True)
    
    if sample_acc not in run_accessions_map:
        runs = get_run_accessions_from_sample(sample_acc, archive)
        # Store as comma-separated string if multiple runs
        run_accessions_map[sample_acc] = ','.join(runs) if runs else 'NA'

print(f"  Processed {len(unique_samples)}/{len(unique_samples)} samples.", flush=True)

# Add Run_accession column
expanded_df['Run_accession'] = expanded_df['archive_accession'].map(run_accessions_map)

print(f"\nRun accessions found: {expanded_df['Run_accession'].notna().sum()}")
print(f"Run accessions missing: {(expanded_df['Run_accession'] == 'NA').sum()}")

# Save to file
expanded_df.to_csv(output_file, sep='\t', index=False)
print(f"\nSaved to {output_file}")

# Also save just the archive_accession column
accessions_only_file = os.path.join(project_root, "data/oral_dental_accessions_only.txt")
expanded_df['archive_accession'].to_csv(accessions_only_file, index=False, header=False)
print(f"Saved accessions only to {accessions_only_file}")

# Print summary statistics
print("\n" + "="*60)
print("SUMMARY")
print("="*60)
print(f"  Unique projects: {expanded_df['project_name'].nunique()}")
print(f"  Unique samples: {expanded_df['sample_name'].nunique()}")
print(f"  Total archive accessions: {len(expanded_df)}")
print(f"\nMaterial breakdown:")
print(expanded_df['material'].value_counts())

# Compare with Collection_accessions.csv
print("\n" + "="*60)
print("COMPARISON WITH COLLECTION_ACCESSIONS.CSV")
print("="*60)

collection_file = os.path.join(project_root, "data/Collection_accessions.csv")
try:
    collection_df = pd.read_csv(collection_file, header=None, names=['accession'])
    collection_accessions = set(collection_df['accession'].str.strip())
    
    print(f"\nCollection_accessions.csv contains: {len(collection_accessions)} accessions")
    
    # Expand run accessions from our dataframe (handle comma-separated values)
    our_run_accessions = set()
    for run_acc in expanded_df['Run_accession'].dropna():
        if run_acc != 'NA':
            # Split by comma if multiple runs
            runs = [r.strip() for r in str(run_acc).split(',')]
            our_run_accessions.update(runs)
    
    print(f"Our dataset contains: {len(our_run_accessions)} unique run accessions")
    
    # Find overlaps
    overlap = collection_accessions.intersection(our_run_accessions)
    only_in_collection = collection_accessions - our_run_accessions
    only_in_our_data = our_run_accessions - collection_accessions
    
    print(f"\nOverlap: {len(overlap)} accessions present in both datasets")
    print(f"Only in Collection_accessions.csv: {len(only_in_collection)}")
    print(f"Only in our dataset: {len(only_in_our_data)}")
    
    if len(overlap) > 0:
        print(f"\nPercentage of Collection accessions found in our data: {len(overlap)/len(collection_accessions)*100:.1f}%")
        print(f"Percentage of our accessions found in Collection: {len(overlap)/len(our_run_accessions)*100:.1f}%")
    
    # Save overlap for reference
    if len(overlap) > 0:
        overlap_file = os.path.join(project_root, "data/overlapping_accessions.txt")
        pd.Series(sorted(overlap)).to_csv(overlap_file, index=False, header=False)
        print(f"\nSaved overlapping accessions to {overlap_file}")
    
except FileNotFoundError:
    print(f"\nWarning: {collection_file} not found. Skipping comparison.")
except Exception as e:
    print(f"\nError during comparison: {e}")

print("="*60)
