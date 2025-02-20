import requests
import logging
import os
import json
import time
from tqdm import tqdm
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from ScrapingScripts import register_scraper

# Configure logging
logging.basicConfig(
    filename='newsday_scraper.log',
    level=logging.ERROR,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def fetch_data(query, cursor=None):
    session = requests.Session()
    url = 'https://izxd45exh7-dsn.algolia.net/1/indexes/prod_ace/browse'
    
    headers = {
        'X-Algolia-Application-Id': 'IZXD45EXH7',
        'X-Algolia-API-Key': '1380221e0fdaf65262fc627c43ab1069',
        'Content-Type': 'application/json',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36',
    }
    
    data = {
        "query": query,
        "filters": "contentType:article",
        "hitsPerPage": 1000
    }
    if cursor:
        data["cursor"] = cursor
    
    retries = Retry(
        total=5,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=['POST']
    )
    
    session.mount('https://', HTTPAdapter(max_retries=retries))
    
    try:
        response = session.post(url, headers=headers, json=data, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f'Request failed: {str(e)}')
        return None

def process_data(data):
    articles = []
    if data and 'hits' in data:
        for hit in data['hits']:
            try:
                article = {
                    'date': hit.get('publishedDate'),
                    'title': hit.get('headline') or hit.get('title'),
                    'link': hit.get('url'),
                    'text': hit.get('body')  # Include the body of the article
                }
                if all(article.values()):  # Ensure all required fields are present
                    articles.append(article)
            except Exception as e:
                logging.error(f'Error processing article: {str(e)}')
    return articles

def save_data(articles, output_dir):
    output_path = os.path.join(output_dir, 'newsday.json')
    try:
        os.makedirs(output_dir, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(articles, f, indent=2)
    except Exception as e:
        logging.error(f'Error saving file: {str(e)}')

@register_scraper('news_day')
def main(query, output_dir):
    all_articles = []
    cursor = None
    retry_count = 0
    max_retries = 3
    
    # Initialize progress bar without a total
    pbar = tqdm(
        desc=f"Scraping '{query}'",
        unit='article',
        dynamic_ncols=True
    )
    
    while True:
        data = fetch_data(query, cursor)
        if not data:
            if retry_count < max_retries:
                retry_count += 1
                time.sleep(2 ** retry_count)
                continue
            else:
                break
        
        # Process current page
        articles = process_data(data)
        all_articles.extend(articles)
        
        # Update progress bar with the number of articles scraped so far
        pbar.update(len(articles))
        pbar.set_postfix({'articles': len(all_articles)})
        
        # Get next page cursor
        new_cursor = data.get('cursor')
        
        # Check for completion
        if not new_cursor or new_cursor == cursor:
            break
            
        cursor = new_cursor
        retry_count = 0
        time.sleep(1)

    pbar.close()
        
    save_data(all_articles, output_dir)
    print(f"\n✅ Saved {len(all_articles)} articles to {os.path.join(output_dir, 'newsday.json')}")