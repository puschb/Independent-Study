#!/usr/bin/env python3
"""
NER Frequency Analysis

This script analyzes the frequency of named entities by category and year
from NER results files. It generates frequency data at three levels:
1. Individual files
2. City-level aggregation (Chicago vs New York)
3. All files aggregated together

Results are stored as JSON files in their respective output directories.
"""

import json
import os
import sys
import argparse
from collections import defaultdict
from datetime import datetime
import re

# Define city groupings
CHICAGO_FILES = ["chicago_reporter", "chicago_tribune", "daily_herald"]
NEW_YORK_FILES = ["ny_daily_news", "the_city"]
CHARLOTTESVILLE_FILES = ["cville_tomorrow", "cville_weekly"]


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Analyze NER frequency by year and category.')
    parser.add_argument('-i', '--input_dir', required=True, 
                        help='Root directory containing the cleaned NER result files')
    parser.add_argument('-o', '--output_dir', required=True,
                        help='Root directory where frequency analysis results will be stored')
    parser.add_argument('-t', '--threshold', type=int, default=3,
                        help='Minimum frequency threshold (entities with lower frequencies will be excluded, default: 3)')
    return parser.parse_args()

def get_file_base_name(filename):
    """Extract the base name from a filename (without extension)."""
    # Simply remove extension
    return os.path.splitext(filename)[0]

def get_year_from_date(date_str):
    """Extract the year from a date string."""
    try:
        # Try ISO format first (2018-10-01T17:35:10+00:00)
        date_obj = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        return date_obj.year
    except (ValueError, AttributeError):
        # Try to extract year with regex
        year_match = re.search(r'20\d\d', date_str)
        if year_match:
            return int(year_match.group(0))
        
        # Default to unknown if parsing fails
        return "unknown"

def process_file(file_path):
    """
    Process a single NER results file and return frequency data by year and category.
    
    Returns:
        dict: A dictionary with years as keys, each containing categories and their word frequencies
    """
    freq_data = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            ner_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error reading file {file_path}: {e}")
        return freq_data
    
    # Process each article
    for article in ner_data:
        # Extract date and NER results
        date = article.get("Date", "")
        ner_results = article.get("NER", {})
        
        # Get year from date
        year = get_year_from_date(date)
        if year == "unknown":
            continue
        
        # Process each entity category
        for category, entities in ner_results.items():
            for entity in entities:
                # Skip empty entities
                if not entity or not entity.strip():
                    continue
                
                # Count frequency
                freq_data[str(year)][category][entity] += 1
    
    return freq_data

def merge_frequency_data(data_list):
    """
    Merge multiple frequency data dictionaries into one.
    
    Args:
        data_list: List of frequency data dictionaries to merge
        
    Returns:
        dict: Merged frequency data
    """
    merged_data = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    
    for data in data_list:
        for year, categories in data.items():
            for category, entities in categories.items():
                for entity, freq in entities.items():
                    merged_data[year][category][entity] += freq
    
    return merged_data

def sort_frequency_data(freq_data, threshold=3):
    """
    Sort frequency data by frequency (descending) for each category.
    Convert defaultdicts to regular dicts for JSON serialization.
    Filter out entities with frequency below the threshold.
    
    Args:
        freq_data: Frequency data dictionary
        threshold: Minimum frequency to include an entity (default: 3)
        
    Returns:
        dict: Sorted frequency data as regular dictionaries
    """
    sorted_data = {}
    
    for year, categories in freq_data.items():
        sorted_data[year] = {}
        
        for category, entities in categories.items():
            # Filter entities by threshold and sort by frequency (descending)
            filtered_entities = {entity: freq for entity, freq in entities.items() if freq >= threshold}
            sorted_entities = dict(sorted(
                filtered_entities.items(), 
                key=lambda item: item[1], 
                reverse=True
            ))
            
            sorted_data[year][category] = sorted_entities
    
    return sorted_data

def process_individual_files(input_dir, output_dir, threshold):
    """
    Process each NER results file individually and save frequency data.
    
    Args:
        input_dir: Directory containing input files
        output_dir: Directory where output will be stored
        threshold: Minimum frequency threshold for entities
    """
    individual_dir = os.path.join(output_dir, "Individual")
    os.makedirs(individual_dir, exist_ok=True)
    
    print(f"Processing individual files...")
    
    # Walk through the input directory structure
    for root, _, files in os.walk(input_dir):
        for file in files:
            if not file.endswith('.json'):
                continue
                
            file_path = os.path.join(root, file)
            base_name = get_file_base_name(file)
            
            print(f"  Processing {file}...")
            
            # Process the file
            freq_data = process_file(file_path)
            
            # Sort the frequency data and apply threshold
            sorted_data = sort_frequency_data(freq_data, threshold)
            
            # Save the results
            output_file = os.path.join(individual_dir, f"{base_name}_freqs.json")
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(sorted_data, f, indent=2, ensure_ascii=False)
                
            print(f"  Saved frequencies to {output_file}")

def process_city_files(input_dir, output_dir, threshold):
    """
    Process files grouped by city and save aggregated frequency data.
    
    Args:
        input_dir: Directory containing input files
        output_dir: Directory where output will be stored
        threshold: Minimum frequency threshold for entities
    """
    city_dir = os.path.join(output_dir, "City")
    os.makedirs(city_dir, exist_ok=True)
    
    print(f"Processing city groups...")
    
    # Initialize data containers
    chicago_data = []
    new_york_data = []
    cville_data = []
    
    # Walk through the input directory structure
    for root, _, files in os.walk(input_dir):
        for file in files:
            if not file.endswith('.json'):
                continue
                
            file_path = os.path.join(root, file)
            base_name = get_file_base_name(file)
            
            # Process the file
            freq_data = process_file(file_path)
            
            # Add to appropriate city group
            if any(city_file in base_name for city_file in CHICAGO_FILES):
                print(f"  Adding {file} to Chicago group")
                chicago_data.append(freq_data)
            elif any(city_file in base_name for city_file in NEW_YORK_FILES):
                print(f"  Adding {file} to New York group")
                new_york_data.append(freq_data)
            elif any(city_file in base_name for city_file in CHARLOTTESVILLE_FILES):
                print(f"  Adding {file} to Charlottesville group")
                cville_data.append(freq_data)
    
    # Merge and save Chicago data
    if chicago_data:
        merged_chicago = merge_frequency_data(chicago_data)
        sorted_chicago = sort_frequency_data(merged_chicago, threshold)
        
        chicago_file = os.path.join(city_dir, "chicago_freqs.json")
        with open(chicago_file, 'w', encoding='utf-8') as f:
            json.dump(sorted_chicago, f, indent=2, ensure_ascii=False)
            
        print(f"  Saved Chicago frequencies to {chicago_file}")
    
    # Merge and save New York data
    if new_york_data:
        merged_new_york = merge_frequency_data(new_york_data)
        sorted_new_york = sort_frequency_data(merged_new_york, threshold)
        
        new_york_file = os.path.join(city_dir, "new_york_freqs.json")
        with open(new_york_file, 'w', encoding='utf-8') as f:
            json.dump(sorted_new_york, f, indent=2, ensure_ascii=False)
            
        print(f"  Saved New York frequencies to {new_york_file}")

    if cville_data:
        merged_cville = merge_frequency_data(cville_data)
        sorted_cville = sort_frequency_data(merged_cville, threshold)
        
        cville_file = os.path.join(city_dir, "cville_freqs.json")
        with open(cville_file, 'w', encoding='utf-8') as f:
            json.dump(sorted_cville, f, indent=2, ensure_ascii=False)
            
        print(f"  Saved Charlottesville frequencies to {new_york_file}")



def process_all_files(input_dir, output_dir, threshold):
    """
    Process all files together and save aggregated frequency data.
    
    Args:
        input_dir: Directory containing input files
        output_dir: Directory where output will be stored
        threshold: Minimum frequency threshold for entities
    """
    all_dir = os.path.join(output_dir, "All")
    os.makedirs(all_dir, exist_ok=True)
    
    print(f"Processing all files together...")
    
    # Initialize data container
    all_data = []
    
    # Walk through the input directory structure
    for root, _, files in os.walk(input_dir):
        for file in files:
            if not file.endswith('.json'):
                continue
                
            file_path = os.path.join(root, file)
            print(f"  Adding {file} to aggregate")
            
            # Process the file
            freq_data = process_file(file_path)
            all_data.append(freq_data)
    
    # Merge and save all data
    if all_data:
        merged_all = merge_frequency_data(all_data)
        sorted_all = sort_frequency_data(merged_all, threshold)
        
        all_file = os.path.join(all_dir, "all_freqs.json")
        with open(all_file, 'w', encoding='utf-8') as f:
            json.dump(sorted_all, f, indent=2, ensure_ascii=False)
            
        print(f"  Saved aggregate frequencies to {all_file}")

def main():
    """Main function to run the analysis."""
    # Parse command line arguments
    args = parse_arguments()
    
    # Check if input directory exists
    if not os.path.isdir(args.input_dir):
        print(f"Error: Input directory {args.input_dir} not found.")
        sys.exit(1)
    
    # Create output directory if it doesn't exist
    os.makedirs(args.output_dir, exist_ok=True)
    
    print(f"Starting NER frequency analysis")
    print(f"Input directory: {args.input_dir}")
    print(f"Output directory: {args.output_dir}")
    print(f"Frequency threshold: {args.threshold}")
    
    # Process at individual level
    process_individual_files(args.input_dir, args.output_dir, args.threshold)
    
    # Process at city level
    process_city_files(args.input_dir, args.output_dir, args.threshold)
    
    # Process all files together
    process_all_files(args.input_dir, args.output_dir, args.threshold)
    
    print(f"NER frequency analysis completed")

if __name__ == "__main__":
    main()