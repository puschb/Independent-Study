#!/bin/bash
#SBATCH --time=48:00:00                 # Adjust total time based on number of files
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=32              # Use 32 CPUs as requested
#SBATCH --partition=standard
#SBATCH -J "Scrape_All_Article_Contents"
#SBATCH --mail-user=bhx5gh@virginia.edu
#SBATCH --mail-type=BEGIN
#SBATCH --mail-type=END
#SBATCH --mail-type=FAIL
#SBATCH --account=uvailp
#SBATCH -o ijobLogs/Scrape_All_Article_Contents.out
#SBATCH -e ijobLogs/Scrape_All_Article_Contents.err

# Activate virtual environment and move to script directory
source .venv/bin/activate
cd ScrapingNewsSources

# Set directories
INPUT_DIR="/scratch/bhx5gh/IndependentStudy/Newsbank/ScrapingResults"
OUTPUT_DIR="/scratch/bhx5gh/IndependentStudy/Newsbank/ScrapedArticles"
ERROR_DIR="/scratch/bhx5gh/IndependentStudy/Newsbank/ScrapedArticleErrors"

# Run the scraper sequentially for each JSON file
for json_file in "$INPUT_DIR"/*.json; do
    echo "Processing $json_file..."
    python scrape_article.py -i "$json_file" -s 2016-01-01 -o "$OUTPUT_DIR" -e "$ERROR_DIR" -c 32
done
