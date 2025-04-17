import requests
import os
import json
import time
from tqdm import tqdm
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from ScrapingScripts import register_scraper

def setup_session():
    session = requests.Session()
    retries = Retry(
        total=5,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=['GET']
    )
    session.mount('https://', HTTPAdapter(max_retries=retries))
    return session

def fetch_data(session, query="", page_handle=None):
    base_url = "https://public-api.wordpress.com/rest/v1.3/sites/209453640/search?fields[]=date&fields[]=title.default&fields[]=permalink.url.raw&sort=date_desc&size=10"
    
    if query:
        base_url = f"{base_url}&query={query}"
    
    url = f"{base_url}&page_handle={page_handle}" if page_handle else base_url
    
    
    headers = {
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36'
    }
    
    try:
        response = session.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"[ERROR] Request failed: {str(e)}")
        return None

def process_data(data):
    articles = []
    if data and 'results' in data:
        for result in data['results']:
            try:
                # Extract fields from the response
                fields = result.get('fields', {})
                
                # Add https:// to the URL if it doesn't already have it
                url = fields.get('permalink.url.raw', '')
                if url and not url.startswith('http'):
                    url = f"https://{url}"
                
                article = {
                    'date': fields.get('date'),
                    'title': fields.get('title.default'),
                    'link': url
                }
                
                # Only add if we have all required fields
                if all(article.values()):
                    articles.append(article)
            except Exception as e:
                print(f"[ERROR] Error processing article: {str(e)}")
    return articles

def save_data(articles, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, 'cville_tomorrow.json')
    
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(articles, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[ERROR] Error saving file: {str(e)}")

@register_scraper('cville_tomorrow')
def main(query="", output_dir="results"):
    """
    Scrape articles from WordPress API
    
    Args:
        query: Search query (optional)
        output_dir: Directory to save the results
    """
    print(f"Starting Charlottesville Tomorrow scraper, saving results to: {output_dir}")
    
    session = setup_session()
    all_articles = []
    page_handle = None
    retry_count = 0
    max_retries = 3
    pbar = None
    
    while True:
        data = fetch_data(session, query, page_handle)
        if not data:
            if retry_count < max_retries:
                retry_count += 1
                print(f"Retrying... (attempt {retry_count}/{max_retries})")
                time.sleep(2 ** retry_count)
                continue
            else:
                print(f"[ERROR] Failed after {max_retries} retries. Stopping.")
                break
        
        # Initialize progress bar on first successful response
        if pbar is None:
            total_results = data.get('total', 0)
            print(f"Total results: {total_results}")
            pbar = tqdm(
                total=total_results,
                desc=f"Scraping Charlottesville Tomorrow",
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
            print("Reached the end of results")
            break
            
        page_handle = new_page_handle
        retry_count = 0
        time.sleep(.1)  # Be nice to the API

    if pbar:
        pbar.close()
        
    save_data(all_articles, output_dir)
    print(f"✅ Saved {len(all_articles)} articles to {output_dir}/cville_tomorrow.json")

if __name__ == "__main__":
    main()