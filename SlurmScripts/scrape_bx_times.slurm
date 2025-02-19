#!/bin/bash

#Submit this script with: sbatch myjob.slurm

#SBATCH --time=2:00:00   # job time limit
#SBATCH --nodes=1   # number of nodes
#SBATCH --ntasks-per-node=1   # number of tasks per node
#SBATCH --cpus-per-task=1   # number of CPU cores per task
#SBATCH --partition=standard   # partition
#SBATCH -J "Scrape BronxTimes"   # job name
#SBATCH --mail-user=bhx5gh@virginia.edu   # email address
#SBATCH --mail-type=BEGIN
#SBATCH --mail-type=END
#SBATCH --mail-type=FAIL
#SBATCH --account=uvailp   # allocation name


# LOAD MODULES, INSERT CODE, AND RUN YOUR PROGRAMS HERE
source .venv/bin/activate
cd ScrapingNewsSources

