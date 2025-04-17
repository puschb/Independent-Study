#!/usr/bin/env python3
"""
NER processor for articles.
Extracts named entities from article titles or text using spaCy and saves the results.
"""

import json
import os
import sys
import argparse
from datetime import datetime
import spacy

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Process articles with NER.')
    parser.add_argument('filename', type=str, help='Name of the JSON file to process')
    parser.add_argument('--field', choices=['title', 'text'], default='title',
                        help='Field to analyze: title or text (default: title)')
    return parser.parse_args()

def process_title_with_ner(nlp, content, categories_of_interest):
    """
    Process content with spaCy NER and extract entities of interest.
    
    Args:
        nlp: spaCy language model
        content: The text content to process (title or full text)
        categories_of_interest: List of entity types to extract
        
    Returns:
        Dictionary with entity types as keys and lists of entities as values
    """
    doc = nlp(content)
    
    # Initialize result dictionary with empty lists for each category
    result = {category: [] for category in categories_of_interest}
    
    # Extract entities that match our categories of interest
    for ent in doc.ents:
        if ent.label_ in categories_of_interest:
            result[ent.label_].append(ent.text)
            
    return result

def main():
    # Parse command line arguments
    args = parse_arguments()
    
    # Define input and output paths
    input_dir = "/scratch/bhx5gh/IndependentStudy/ScrapedArticles/"
    output_dir = f"/scratch/bhx5gh/IndependentStudy/NERResults/Raw/Spacy/{args.field}"
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    input_file = os.path.join(input_dir, args.filename)
    output_file = os.path.join(output_dir, args.filename)
    
    #
    
    # Initialize spaCy model
    print(f"Loading spaCy model...")
    nlp = spacy.load("en_core_web_sm")
    
    # Define categories of interest
    categories_of_interest = ["EVENT", "FAC", "GPE", "LAW", "NORP", "ORG", "PERSON", "PRODUCT"]
    
    # Read input data
    print(f"Processing file: {input_file}")
    print(f"Analyzing {args.field} field")
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
    results = []
    total_articles = len(articles)
    
    for i, article in enumerate(articles):
        if i % 100 == 0:
            print(f"Processing article {i+1}/{total_articles}...")
        
        # Extract data fields
        title = article.get("title", "")
        date = article.get("date", "")
        
        # Determine which field to analyze
        if args.field == "title":
            content_to_analyze = title
            # Skip articles without titles
            if not content_to_analyze:
                continue
        else:  # args.field == "text"
            content_to_analyze = article.get("text", "")
            # Skip articles without text
            if not content_to_analyze:
                continue
        
        # Process content with NER
        ner_results = process_title_with_ner(nlp, content_to_analyze, categories_of_interest)
        
        # Create result entry
        result_entry = {
            "Title": title,
            "Date": date,
            "NER": ner_results
        }
        
        results.append(result_entry)
    
    # Write output data
    print(f"Writing results to: {output_file}")
    with open(f'{output_file}.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"Processing complete. Processed {len(results)} articles.")

if __name__ == "__main__":
    main()