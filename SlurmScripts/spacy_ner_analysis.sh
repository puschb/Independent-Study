#!/bin/bash
# Usage: ./run_ner_analysis.sh [title|text]
# Example: ./run_ner_analysis.sh text
# If no argument is provided, "title" is used by default

# Set default field to "title" if not specified
FIELD="${1:-title}"

# Validate the field parameter
if [ "$FIELD" != "title" ] && [ "$FIELD" != "text" ]; then
    echo "Error: Field parameter must be either 'title' or 'text'"
    echo "Usage: $0 [title|text]"
    exit 1
fi

echo "Running NER analysis on all JSON files with field: $FIELD"

# Directory containing the JSON files
INPUT_DIR="/scratch/bhx5gh/IndependentStudy/ScrapedArticles"

# Create logs directory if it doesn't exist
mkdir -p ijobLogs

# Get all JSON files directly in the input directory (no subdirectories)
JSON_FILES=$(find "$INPUT_DIR" -maxdepth 1 -name "*.json")

# Count the number of files
NUM_FILES=$(echo "$JSON_FILES" | wc -l)
echo "Found $NUM_FILES JSON files to process"

# Process each file
for JSON_FILE in $JSON_FILES; do
    # Extract just the filename without the path or extension
    FILENAME=$(basename "$JSON_FILE" .json)
    
    echo "Submitting job for $FILENAME..."
    
    # Create a temporary SLURM script for this file
    TMP_SCRIPT=$(mktemp /tmp/ner_job_${FILENAME}.XXXXXX.slurm)
    
    cat <<EOF > "$TMP_SCRIPT"
#!/bin/bash
#SBATCH --time=0:30:00             # job time limit (30 minutes)
#SBATCH --nodes=1                  # number of nodes
#SBATCH --ntasks-per-node=1        # number of tasks per node
#SBATCH --cpus-per-task=1          # number of CPU cores per task
#SBATCH --partition=standard       # partition (adjust as needed)
#SBATCH -J "NER_${FIELD}_${FILENAME}"   # job name
#SBATCH --mail-user=bhx5gh@virginia.edu  # email address
#SBATCH --mail-type=FAIL
#SBATCH --account=uvailp           # allocation name
#SBATCH -o ijobLogs/NER_${FIELD}_${FILENAME}.out
#SBATCH -e ijobLogs/NER_${FIELD}_${FILENAME}.err

# Activate virtual environment
source .venv/bin/activate

# Run the NER analysis script
python Analysis/NER/Spacy/spacy_ner_analysis.py ${FILENAME} --field ${FIELD} 

echo "NER analysis for ${FILENAME} (field: ${FIELD}) completed"
EOF
    
    # Submit the job
    sbatch "$TMP_SCRIPT"
    
    # Remove the temporary script
    rm "$TMP_SCRIPT"
    
    # Optional: add a small delay to avoid overwhelming the scheduler
    sleep 0.5
done

echo "All jobs submitted. Use 'squeue -u \$USER' to check job status."