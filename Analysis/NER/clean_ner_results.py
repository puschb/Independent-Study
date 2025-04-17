#!/usr/bin/env python3
"""
NER Results Cleaner

This script cleans and deduplicates NER results from the previous extraction process.
It normalizes entity names and removes duplicates from each category.
"""

import json
import os
import sys
import argparse
import re
from collections import defaultdict


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Clean and deduplicate NER results.')
    parser.add_argument('-f', '--filename', type=str, help='Name of the JSON file to process')
    parser.add_argument('-m', '--method', type=str, help='NER Method used (ex. Spacy)')
    parser.add_argument('-fd', '--field', choices=['title', 'text'], default='title',
                        help='Field to analyze: title or text (default: title)')

    return parser.parse_args()

def normalize_entity(entity, entity_type):
    """
    Normalize entity names.
    For PERSON entities, remove possessives and standardize format.
    For other entity types, just return the original.
    
    Args:
        entity: String containing the entity name
        entity_type: The type of entity (PERSON, ORG, etc.)
        
    Returns:
        Normalized entity name
    """
    # Skip empty entities
    if not entity or not entity.strip():
        return entity
    
    # Only apply special normalization for PERSON entities
    if entity_type == "PERSON":
        # Remove possessives
        entity = re.sub(r"'s$", "", entity)
        
        # Fix capitalization - ensure first letter of each word is capitalized
        entity = ' '.join(word.capitalize() for word in entity.split())
    
    return entity

def extract_last_name(name):
    """
    Extract the last name from a person entity.
    
    Args:
        name: String containing a person's name
        
    Returns:
        Last name as a string
    """
    # Remove possessives first
    name = re.sub(r"'s$", "", name)
    
    # Split by spaces and take the last part as the last name
    parts = name.split()
    if len(parts) > 0:
        return parts[-1].lower()
    return ""

def consolidate_person_entities(entities):
    """
    Consolidate person entities by grouping those with the same last name.
    Keep the longest version of each name.
    
    Args:
        entities: List of person entities
        
    Returns:
        List of consolidated person entities
    """
    # Skip if empty
    if not entities:
        return []
    
    # Group by last name
    last_name_dict = {}
    
    for entity in entities:
        if not entity:
            continue
            
        last_name = extract_last_name(entity)
        if not last_name:
            continue
            
        # If we already have an entity with this last name
        if last_name in last_name_dict:
            # Keep the longer name version
            if len(entity) > len(last_name_dict[last_name]):
                last_name_dict[last_name] = entity
        else:
            last_name_dict[last_name] = entity
    
    # Return the consolidated list
    return list(last_name_dict.values())

def clean_entities(entities_dict):
    """
    Clean and deduplicate entities in each category.
    For PERSON entities, consolidate based on last name.
    For other entities, just remove duplicates.
    
    Args:
        entities_dict: Dictionary with entity types as keys and lists of entities as values
        
    Returns:
        Cleaned dictionary with deduplicated and normalized entities
    """
    cleaned_dict = {}
    
    for entity_type, entities in entities_dict.items():
        # Skip empty lists
        if not entities:
            cleaned_dict[entity_type] = []
            continue
        
        # Normalize entities
        normalized_entities = [normalize_entity(entity, entity_type) for entity in entities]
        
        # For PERSON entities, apply last name consolidation
        if entity_type == "PERSON":
            cleaned_entities = consolidate_person_entities(normalized_entities)
        else:
            # For other entity types, just remove duplicates
            seen = set()
            cleaned_entities = []
            for entity in normalized_entities:
                if entity and entity not in seen:
                    cleaned_entities.append(entity)
                    seen.add(entity)
        
        cleaned_dict[entity_type] = cleaned_entities
    
    return cleaned_dict

def main():
    # Parse command line arguments
    args = parse_arguments()
    
    # Define input and output paths
    input_dir = f"/scratch/bhx5gh/IndependentStudy/NERResults/Raw/{args.method}/{args.field}/"
    output_dir = f"/scratch/bhx5gh/IndependentStudy/NERResults/Cleaned/{args.method}/{args.field}/"
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    input_file = os.path.join(input_dir, args.filename)
    output_file = os.path.join(output_dir, args.filename)
    
    # Read input data
    print(f"Processing file: {input_file}")
    try:
        with open(f'{input_file}.json', 'r', encoding='utf-8') as f:
            articles = json.load(f)
    except FileNotFoundError:
        print(f"Error: Input file {input_file} not found.")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Error: Input file {input_file} is not valid JSON.")
        sys.exit(1)
    
    # Process each article
    cleaned_results = []
    total_articles = len(articles)
    
    print(f"Cleaning and deduplicating {total_articles} articles...")
    
    for i, article in enumerate(articles):
        if i % 1000 == 0 and i > 0:
            print(f"Processed {i}/{total_articles} articles...")
        
        # Extract data fields
        title = article.get("Title", "")
        date = article.get("Date", "")
        ner = article.get("NER", {})
        
        # Clean and deduplicate NER results
        cleaned_ner = clean_entities(ner)
        
        # Create cleaned result entry
        cleaned_entry = {
            "Title": title,
            "Date": date,
            "NER": cleaned_ner
        }
        
        cleaned_results.append(cleaned_entry)
    
    # Write output data
    print(f"Writing cleaned results to: {output_file}")
    with open(f'{output_file}.json', 'w', encoding='utf-8') as f:
        json.dump(cleaned_results, f, indent=2, ensure_ascii=False)
    
    print(f"Cleaning complete. Processed {len(cleaned_results)} articles.")

if __name__ == "__main__":
    main()