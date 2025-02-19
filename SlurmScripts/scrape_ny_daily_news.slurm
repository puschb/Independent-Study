#!/bin/bash

#Submit this script with: sbatch myjob.slurm

#SBATCH --time=10:00:00   # job time limit
#SBATCH --nodes=1   # number of nodes
#SBATCH --ntasks-per-node=1   # number of tasks per node
#SBATCH --cpus-per-task=1   # number of CPU cores per task
#SBATCH --partition=standard   # partition
#SBATCH -J "Scrape NY Daily News"   # job name
#SBATCH --mail-user=bhx5gh@virginia.edu   # email address
#SBATCH --mail-type=BEGIN
#SBATCH --mail-type=END
#SBATCH --mail-type=FAIL
#SBATCH --account=uvailp   # allocation name
#SBATCH -o ijobLogs/scrape_ny_daily_news.out
#SBATCH -e ijobLogs/scrape_ny_daily_news.err


# LOAD MODULES, INSERT CODE, AND RUN YOUR PROGRAMS HERE
source .venv/bin/activate
cd ScrapingNewsSources
python scrape_newspaper.py ny_daily_news -q "" -o "/scratch/bhx5gh/IndependentStudy/ScrapingResults/"
