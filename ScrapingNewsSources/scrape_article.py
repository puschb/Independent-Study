import argparse
import asyncio
import json
import random
import re
import time
from datetime import datetime
from newspaper import Article
from typing import List, Dict
import aiohttp
from aiohttp import ClientSession
from tqdm.asyncio import tqdm_asyncio
import os
from dateutil.parser import parse
from tqdm.asyncio import tqdm as async_tqdm
#from llama_immigration_classifier import LlamaImmigrationClassifier

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Safari/605.1.15',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36'
]

IMMIGRATION_PATTERN = re.compile(
    r'\b(immigration|immigrant?s|immigrat(e|ed|ing|es)|migration|migrant?s|migrat(e|ed|ing|es)|green\s?card|'
    r'citizenship|naturalization|naturaliz(e|ed|ing|es)|asylum|refugee?s|border|deportation|deport(s|ed|ing)?|'
    r'undocumented|DACA|Dreamers|ICE|USCIS|Title\s?42|Title\s?8|sanctuary\s?cities|sanctuary\s?city|'
    r'Temporary\s?Protected\s?Status|TPS|path\s?to\s?citizenship|DAPA|travel\s?ban|family\s?separation)\b',
    flags=re.IGNORECASE
)

async def fetch_article(session: ClientSession, article: Dict, semaphore: asyncio.Semaphore) -> Dict:
    async with semaphore:
        try:
            url = article['url']
            if not url.startswith(('http://', 'https://')):
                url = f'https://{url}'

            headers = {'User-Agent': random.choice(USER_AGENTS)}

            #await asyncio.sleep(random.uniform(0.5, 2.0))

            async with session.get(url, headers=headers, timeout=30) as response:
                html = await response.text()

                loop = asyncio.get_event_loop()
                article_obj = await loop.run_in_executor(
                    None, 
                    lambda: Article(url, language='en', fetch_images=False)
                )

                article_obj.download(input_html=html)
                article_obj.parse()

                return {
                    **article,
                    'text': article_obj.text,
                    'date': article_obj.publish_date.isoformat() if article_obj.publish_date else article['date']
                }

        except Exception as e:
            return {**article, 'text': '', 'error': str(e)}

async def process_articles(articles: List[Dict], concurrency: int) -> List[Dict]:
    connector = aiohttp.TCPConnector(limit_per_host=5)
    semaphore = asyncio.Semaphore(concurrency)

    async with ClientSession(connector=connector) as session:
        tasks = [fetch_article(session, article, semaphore) for article in articles]
        results = []

        for i in async_tqdm(range(0, len(tasks), concurrency), desc="Fetching article batches"):
            batch = tasks[i:i+concurrency]
            results.append(await asyncio.gather(*batch))
            await asyncio.sleep(1)


        return results

def parse_article_date(article):
    date_str = article.get('date')
    if not date_str:
        return None
    try:
        dt = parse(date_str).replace(tzinfo=None)
        return dt if isinstance(dt, datetime) else None
    except:
        return None

def main():
    parser = argparse.ArgumentParser(description='Scrape news articles from JSON file')
    parser.add_argument('-i', '--input', type=str, required=True, help='Path to input JSON file')
    parser.add_argument('-s', '--start-date', type=lambda d: datetime.strptime(d, '%Y-%m-%d'), 
                        required=True, help='Start date in YYYY-MM-DD format')
    parser.add_argument('-o', '--output', type=str, default='/scratch/bhx5gh/IndependentStudy/ScrapedArticles/', help='Path to output folder')
    parser.add_argument('-e', '--errors', type=str, default='/scratch/bhx5gh/IndependentStudy/ScrapedArticles/', help='Path to error folder')
    parser.add_argument('-c', '--concurrency', type=int, default=10, help='Number of concurrent requests')

    args = parser.parse_args()
    start_date = args.start_date.replace(tzinfo=None)  # Make offset-naive

    name = args.input.split('/')[-1]

    with open(args.input, 'r') as f:
        articles = json.load(f)

    # Filter articles by pattern and check date if it exists
    filtered_articles = [
        article for article in articles 
        if 'title' in article 
        and IMMIGRATION_PATTERN.search(article['title'])
        and (
            # Include if date is null OR date meets the start_date condition
            (article_date := parse_article_date(article)) is None 
            or article_date >= start_date
        )
    ]

    print(f"Found {len(filtered_articles)} articles matching immigration pattern and date criteria")

    start_time = time.time()
    results = asyncio.run(process_articles(filtered_articles, args.concurrency))

    # Process results and apply date filtering for previously null dates
    successful = []
    errors = []

    for result in results:   
        if 'error' in result:
            errors.append(result)
        else:
            '''# Get the original date before scraping
            original_date = parse_article_date({'date': result.get('original_date')})
            
            # If article previously had no date but now has one, check the new date
            if original_date is None:
                article_date = parse_article_date(result)
                if article_date is None or article_date >= start_date:
                    successful.append(result)
                # Skip articles with newly found dates before the start date
            else:
                # Article had a valid date initially, so we keep it'''
            successful.append(result)

    os.makedirs(args.output, exist_ok=True)
    os.makedirs(args.errors, exist_ok=True)

    output_path = os.path.join(args.output, name)
    error_path = os.path.join(args.errors, f'errors_{name}')

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(successful, f, indent=2, ensure_ascii=False)

    with open(error_path, 'w', encoding='utf-8') as f:
        json.dump(errors, f, indent=2, ensure_ascii=False)

    print(f"\nCompleted in {time.time() - start_time:.2f}s")
    print(f"Successfully scraped: {len(successful)} articles")
    print(f"Scraping errors: {len(errors)} articles")

if __name__ == "__main__":
    main()