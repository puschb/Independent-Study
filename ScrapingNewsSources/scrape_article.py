import argparse
from pathlib import Path
from typing import Dict
import yaml
from ScrapingNewsSources.ScrapingScripts.silive import SiLive
import asyncio
from article_scraper import ArticleScraper

def load_config(config_path: str) -> Dict:
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def main():
    parser = argparse.ArgumentParser(description='Scrape article content from JSON file')
    parser.add_argument('-i', '--input', required=True, help='Input JSON file')
    parser.add_argument('-o', '--output', required=True, help='Output JSON file')
    parser.add_argument('-c', '--config', required=True, help='Config file')
    parser.add_argument('-n', '--concurrency', type=int, default=3, 
                       help='Maximum concurrent requests (default: 3)')
    args = parser.parse_args()

    config = load_config(args.config)
    scraper = ArticleScraper(args.input, args.output, config, args.concurrency)
    asyncio.run(scraper.run())

if __name__ == '__main__':
    main()