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
    filename='thecity_scraper.log',
    level=logging.ERROR,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def fetch_data(query, page_handle=None):
    session = requests.Session()
    base_url = f'https://public-api.wordpress.com/rest/v1.3/sites/224811423/search?fields%5B0%5D=date&fields%5B1%5D=permalink.url.raw&fields%5B2%5D=tag.name.default&fields%5B3%5D=category.name.default&fields%5B4%5D=post_type&fields%5B5%5D=shortcode_types&fields%5B6%5D=forum.topic_resolved&fields%5B7%5D=has.image&fields%5B8%5D=image.url.raw&fields%5B9%5D=image.alt_text&highlight_fields%5B0%5D=title&highlight_fields%5B1%5D=content&highlight_fields%5B2%5D=comments&query={query}&sort=date_desc&size=20'
    
    url = f"{base_url}&page_handle={page_handle}" if page_handle else base_url

    headers = {
        'accept': '*/*',
        'accept-language': 'en-US,en;q=0.9,es;q=0.8',
        'origin': 'https://www.thecity.nyc',
        'priority': 'u=1, i',
        'referer': 'https://www.thecity.nyc/',
        'sec-ch-ua': '"Not A(Brand";v="8", "Chromium";v="132", "Google Chrome";v="132"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'cross-site',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36'
    }
    
    retries = Retry(
        total=5,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=['GET']
    )
    
    session.mount('https://', HTTPAdapter(max_retries=retries))
    
    try:
        response = session.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f'Request failed: {str(e)}')
        return None

def process_data(data):
    articles = []
    if data and 'results' in data:
        for result in data['results']:
            try:
                fields = result.get('fields', {})
                article = {
                    'date': fields.get('date'),
                    'title': fields.get('title.default'),
                    'link': fields.get('permalink.url.raw')
                }
                if all(article.values()):
                    articles.append(article)
            except Exception as e:
                logging.error(f'Error processing article: {str(e)}')
    return articles

def save_data(articles, output_dir):
    output_path = os.path.join(output_dir, 'the_city.json')
    try:
        os.makedirs(output_dir, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(articles, f, indent=2)
    except Exception as e:
        logging.error(f'Error saving file: {str(e)}')

@register_scraper('the_city')
def main(query, output_dir):
    all_articles = []
    page_handle = None
    retry_count = 0
    max_retries = 3
    pbar = None
    
    
    while True:
        data = fetch_data(query, page_handle)
        if not data:
            if retry_count < max_retries:
                retry_count += 1
                time.sleep(2 ** retry_count)
                continue
            else:
                break
        
        # Initialize progress bar on first successful response
        if pbar is None:
            total_results = data.get('total', 0)
            pbar = tqdm(
                total=total_results,
                desc=f"Scraping '{query}'",
                unit='article',
                dynamic_ncols=True
            )
        
        # Process current page
        articles = process_data(data)
        all_articles.extend(articles)
        
        # Update progress bar
        pbar.update(len(articles))
        
        # Get next page handle
        new_page_handle = data.get('page_handle')
        
        # Check for completion
        if not new_page_handle or new_page_handle == page_handle:
            break
            
        page_handle = new_page_handle
        retry_count = 0
        time.sleep(1)

    if pbar:
        pbar.close()
        
    save_data(all_articles, output_dir)
    print(f"\n✅ Saved {len(all_articles)} articles to {os.path.join(output_dir, 'the_city.json')}")