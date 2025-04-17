#!/usr/bin/env python3
import argparse
import logging
from ScrapingScripts import SCRAPER_REGISTRY

def run_scraper(scraper_name, query, output_dir):
    print('in run_scraper')
    if scraper_name not in SCRAPER_REGISTRY:
        available = ", ".join(SCRAPER_REGISTRY.keys())
        logging.error(f"Scraper '{scraper_name}' not found. Available: {available}")
        return
    
    try:
        SCRAPER_REGISTRY[scraper_name](query, output_dir)
    except Exception as e:
        print(e)
        logging.error(f"Error running {scraper_name}: {str(e)}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run website scrapers')
    parser.add_argument('scraper', 
                       help=f'Name of the scraper to run. Available: {", ".join(SCRAPER_REGISTRY.keys())}')
    
    parser.add_argument('-q', '--query',
                       default='',
                       help='Query for the search')
    
    parser.add_argument('-o', '--output-dir',
                       default='output',
                       help='Output directory for JSON files (default: output)')
    
    args = parser.parse_args()
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('scraper_errors.log'),
            logging.StreamHandler()
        ]
    )
    print("here")
    run_scraper(args.scraper, args.query, args.output_dir)