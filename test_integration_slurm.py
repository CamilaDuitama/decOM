#!/usr/bin/env python3
"""
Integration test for decOM - SLURM cluster aware
"""
import os
import sys
import subprocess
import time
from pathlib import Path

def run_command(cmd, cwd=None):
    """Run a command and return success status and output"""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, cwd=cwd, check=True
        )
        return True, result.stdout, result.stderr
    except subprocess.CalledProcessError as e:
        return False, e.stdout, e.stderr

def submit_slurm_job():
    """Submit decOM test as SLURM job and wait for completion"""
    print("🧪 Starting decOM Integration Test on SLURM...")
    
    # Check prerequisites
    if not Path("decOM_sources").exists():
        print("❌ decOM_sources not found. Please run 'make setup' first.")
        return False
        
    if not Path("tests/sample/SRR13355807.fof").exists():
        print("❌ Test sample not found.")
        return False
    
    # Create SLURM job script
    # NOTE: We direct both STDOUT and STDERR to decOM.log to avoid creating separate
    # decOM_test_<jobid>.out/err files. decOM itself also appends to decOM.log, so
    # its internal log lines will appear once (direct write) while script-level
    # echoes will also be captured. Avoid deleting decOM.log inside the package
    # so that the initial "Starting decOM analysis" line is preserved.
    slurm_script = """#!/bin/bash
#SBATCH --job-name=decOM_test
#SBATCH --partition=seqbio
#SBATCH --qos=seqbio
#SBATCH --mem=50G
#SBATCH --cpus-per-task=10
#SBATCH --time=02:00:00
#SBATCH --output=decOM.log
#SBATCH --error=decOM.log

# If you prefer to keep previous runs, comment out the next line. This truncates the file.
> decOM.log

echo "[SLURM] Job started at $(date)" >> decOM.log
echo "[SLURM] Working directory: $(pwd)" >> decOM.log

# Load conda and activate environment
source ~/miniconda3/etc/profile.d/conda.sh
conda activate decOM-dev

# Clean previous test outputs
rm -rf test_output_single/ test_output_several/

echo "🧪 Running decOM Integration Tests..." >> decOM.log

# TEST 1: Single sink
echo "🚀 Test 1: Single sink analysis (SRR13355807)..." >> decOM.log
PYTHONPATH=/pasteur/appa/scratch/cduitama/decOM/src python -m decOM \
    -s SRR13355807 \
    -p_sources decOM_sources/ \
    -k tests/sample/SRR13355807.fof \
    -mem 10GB \
    -t 5 \
    -o test_output_single/

echo "✅ Single sink test completed!" >> decOM.log
echo "📁 Single sink output files:" >> decOM.log
ls -la test_output_single/ >> decOM.log

# TEST 2: Several sinks
echo "🚀 Test 2: Several sinks analysis..." >> decOM.log
PYTHONPATH=/pasteur/appa/scratch/cduitama/decOM/src python -m decOM \
    -p_sources decOM_sources/ \
    -p_sinks tests/several_samples/sinks.txt \
    -p_keys tests/several_samples/ \
    -mem 10GB \
    -t 5 \
    -o test_output_several/

echo "✅ Several sinks test completed!" >> decOM.log
echo "📁 Several sinks output files:" >> decOM.log
ls -la test_output_several/ >> decOM.log

echo "🎉 All decOM integration tests completed!" >> decOM.log
"""
    
    # Write the SLURM script
    script_path = Path("test_decom_slurm.sh")
    with open(script_path, 'w') as f:
        f.write(slurm_script)
    
    # Make it executable
    script_path.chmod(0o755)
    
    # Submit the job
    print("📤 Submitting SLURM job...")
    success, stdout, stderr = run_command(f"sbatch {script_path}")
    
    if not success:
        print("❌ Failed to submit SLURM job!")
        print("STDERR:", stderr)
        return False
    
    # Extract job ID
    job_id = stdout.strip().split()[-1]
    print(f"✅ Job submitted with ID: {job_id}")
    print("⏳ Waiting for job to complete...")
    print("💡 You can monitor with: squeue -u $USER")
    print("💡 Or check logs with: tail -f decOM_test_*.out")
    
    return True

def check_test_results():
    """Check if both tests completed successfully"""
    success = True
    
    # Check single sink test
    output_dir_single = Path("test_output_single")
    if output_dir_single.exists():
        files = list(output_dir_single.glob("*"))
        print(f"✅ Single sink test completed! Found {len(files)} output files:")
        for f in files[:5]:  # Show first 5 files
            print(f"   - {f.name} ({f.stat().st_size} bytes)")
        if len(files) > 5:
            print(f"   ... and {len(files) - 5} more files")
    else:
        print("❌ Single sink test failed - no output directory found.")
        success = False
    
    # Check several sinks test  
    output_dir_several = Path("test_output_several")
    if output_dir_several.exists():
        files = list(output_dir_several.glob("*"))
        print(f"✅ Several sinks test completed! Found {len(files)} output files:")
        for f in files[:5]:  # Show first 5 files
            print(f"   - {f.name} ({f.stat().st_size} bytes)")
        if len(files) > 5:
            print(f"   ... and {len(files) - 5} more files")
    else:
        print("❌ Several sinks test failed - no output directory found.")
        success = False
        
    return success

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "check":
        # Check results mode
        success = check_test_results()
    else:
        # Submit job mode
        success = submit_slurm_job()
    
    sys.exit(0 if success else 1)
