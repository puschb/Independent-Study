#!/bin/bash
#SBATCH --time=0:10:00             # job time limit (2 hours)
#SBATCH --nodes=1                  # number of nodes
#SBATCH --ntasks-per-node=1        # number of tasks per node
#SBATCH --cpus-per-task=1          # number of CPU cores per task
#SBATCH --partition=standard       # partition (adjust as needed)
#SBATCH -J "Clean_NER_Results"     # job name
#SBATCH --mail-user=bhx5gh@virginia.edu  # email address
#SBATCH --mail-type=FAIL
#SBATCH --account=uvailp           # allocation name
#SBATCH -o ijobLogs/Clean_NER_Results.out
#SBATCH -e ijobLogs/Clean_NER_Results.err

# Base directory containing the raw NER results
BASE_DIR="/scratch/bhx5gh/IndependentStudy/NERResults/Raw"

# Ensure logs directory exists
mkdir -p ijobLogs

# Activate virtual environment
source .venv/bin/activate

echo "Starting NER results cleaning process"
echo "Processing files from: $BASE_DIR"

# Get all method directories
METHOD_DIRS=$(find "$BASE_DIR" -mindepth 1 -maxdepth 1 -type d)

# Initialize counters
TOTAL_FILES=0
PROCESSED_FILES=0
FAILED_FILES=0

# Process each method directory
for METHOD_DIR in $METHOD_DIRS; do
    METHOD=$(basename "$METHOD_DIR")
    echo "Processing method: $METHOD"
    
    # Get all field directories within this method
    FIELD_DIRS=$(find "$METHOD_DIR" -mindepth 1 -maxdepth 1 -type d)
    
    # Process each field directory
    for FIELD_DIR in $FIELD_DIRS; do
        FIELD=$(basename "$FIELD_DIR")
        echo "  Processing field: $FIELD"
        
        # Get all JSON files in this field directory
        JSON_FILES=$(find "$FIELD_DIR" -maxdepth 1 -name "*.json")
        
        # Count files for this method/field
        FILE_COUNT=$(echo "$JSON_FILES" | wc -l)
        TOTAL_FILES=$((TOTAL_FILES + FILE_COUNT))
        echo "  Found $FILE_COUNT JSON files in $METHOD/$FIELD"
        
        # Process each file
        for JSON_FILE in $JSON_FILES; do
            # Extract just the filename without the extension
            FILENAME=$(basename "$JSON_FILE" .json)
            
            echo "    Processing file: $FILENAME (method: $METHOD, field: $FIELD)"
            
            # Run the cleaning script on this file with all required parameters
            python Analysis/NER/clean_ner_results.py -f "$FILENAME" -m "$METHOD" -fd "$FIELD"
            
            # Check if the script executed successfully
            if [ $? -eq 0 ]; then
                echo "    Successfully cleaned $FILENAME"
                PROCESSED_FILES=$((PROCESSED_FILES + 1))
            else
                echo "    Error cleaning $FILENAME"
                FAILED_FILES=$((FAILED_FILES + 1))
            fi
        done
    done
done

echo "NER results cleaning process completed"
echo "Total files: $TOTAL_FILES"
echo "Successfully processed: $PROCESSED_FILES"
echo "Failed: $FAILED_FILES"