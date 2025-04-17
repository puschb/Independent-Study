#!/bin/bash
# Usage: ./submit_scraper.sh <file_name>
# Example: ./submit_scraper.sh bx_times

if [ -z "$1" ]; then
    echo "Usage: $0 <file_name>"
    exit 1
fi

FILE_NAME="$1"

# Create a temporary SLURM script with the dynamic values
TMP_SCRIPT=$(mktemp /tmp/slurm_script.XXXXXX.slurm)

cat <<EOF > "$TMP_SCRIPT"
#!/bin/bash
#SBATCH --time=1:00:00            # job time limit
#SBATCH --nodes=1                  # number of nodes
#SBATCH --ntasks-per-node=1        # number of tasks per node
#SBATCH --cpus-per-task=1          # number of CPU cores per task
#SBATCH --partition=standard       # partition (adjust as needed)
#SBATCH -J "Scrape_article_content_${FILE_NAME}"   # job name using the parameter
#SBATCH --mail-user=bhx5gh@virginia.edu  # email address
#SBATCH --mail-type=BEGIN
#SBATCH --mail-type=END
#SBATCH --mail-type=FAIL
#SBATCH --account=uvailp           # allocation name
#SBATCH -o ijobLogs/Scrape_article_content_${FILE_NAME}.out
#SBATCH -e ijobLogs/Scrape_article_content_${FILE_NAME}.err

# Activate virtual environment and run the scraper
source .venv/bin/activate
cd ScrapingNewsSources
python scrape_article.py --input=/scratch/bhx5gh/IndependentStudy/ScrapingResults/${FILE_NAME}.json -s 2016-01-01
EOF

# Submit the temporary script and then remove it
sbatch "$TMP_SCRIPT"
rm "$TMP_SCRIPT"
