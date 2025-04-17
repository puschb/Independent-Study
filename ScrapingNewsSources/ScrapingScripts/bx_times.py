import requests
import logging
import os
import json
import time
import re
from tqdm import tqdm
from bs4 import BeautifulSoup
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

def fetch_page(session, url, page, query):
    try:
        response = session.get(
            url.format(page=page, query=query),
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Referer': f'https://www.bxtimes.com/?s={query}'
            },
            timeout=20
        )
        response.raise_for_status()
        return response.text
    except Exception as e:
        logging.error(f"Error fetching page {page}: {str(e)}")
        return None

def parse_total_pages(html):
    try:
        soup = BeautifulSoup(html, 'html.parser')
        
        # Extract content from the Open Graph meta tag
        meta_tag = soup.find('meta', {'property': 'og:title'})
        if meta_tag and 'content' in meta_tag.attrs:
            title = meta_tag['content']
        else:
            return None  # Return None if the meta tag is missing
        
        # Use regex to extract the total number of pages
        match = re.search(r'Page \d+ of (\d+)', title)
        return int(match.group(1)) if match else None
    except Exception as e:
        logging.error(f"Error parsing total pages: {str(e)}")
        return None

def parse_articles(html):
    soup = BeautifulSoup(html, 'html.parser')
    articles = []
    
    for article in soup.find_all('article'):
        try:
            title_tag = article.find('h3')
            if not title_tag:
                continue
                
            link_tag = title_tag.find('a')
            title = link_tag.get_text(strip=True) if link_tag else None
            link = link_tag['href'] if link_tag else None
            
            date_tag = article.find('time', class_='entry-date published')
            date = date_tag['datetime'] if date_tag else None
            
            if title and link:
                articles.append({
                    'title': title,
                    'link': link,
                    'date': date,
                })
        except Exception as e:
            logging.error(f"Error parsing article: {str(e)}")
            continue
    
    return articles

def save_results(articles, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, 'bx_times.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(articles, f, indent=2, ensure_ascii=False)

@register_scraper('bx_times')
def main(query, output_dir):
    logging.basicConfig(
        filename='bxtimes_scraper.log',
        level=logging.ERROR,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    session = setup_session()
    base_url = "https://www.bxtimes.com/page/{page}/?s={query}"
    
    all_articles = []
    page = 1
    retry_count = 0
    max_retries = 3

    initial_html = fetch_page(session, base_url, 2, query)
    if not initial_html:
      logging.error("Failed to fetch initial page")
      return
    
    total_pages = parse_total_pages(initial_html)
    max_pages = total_pages if total_pages else 150 # default value
    if total_pages:
        max_pages = total_pages
       
    with tqdm(total=max_pages, desc=f"Scraping '{query}'", unit='page') as pbar:
      while page <= max_pages:
        html = fetch_page(session, base_url, page, query)
        
        if not html:
          if retry_count < max_retries:
            retry_count += 1
            time.sleep(2 ** retry_count)
            continue
          else:
            break

        articles = parse_articles(html)
        if not articles:
          break  # No more articles found

        all_articles.extend(articles)
        page += 1
        retry_count = 0
        pbar.update(1)
        time.sleep(1)  # Respectful delay

    save_results(all_articles, output_dir)
    print(f"✅ Saved {len(all_articles)} articles to {output_dir}/bronx_times.json")
