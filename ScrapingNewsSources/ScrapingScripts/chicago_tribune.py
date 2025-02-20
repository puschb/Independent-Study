import requests
import logging
import os
import json
import time
from tqdm import tqdm
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from ScrapingScripts import register_scraper
import re

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

def fetch_page(session, url, page):
    try:
        response = session.get(
            url.format(page=page),
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36',
                'Accept': '*/*',
                'Accept-Language': 'en-US,en;q=0.9,es;q=0.8'
            },
            timeout=15
        )
        response.raise_for_status()
        return response.text
    except Exception as e:
        logging.error(f"Error fetching page {page}: {str(e)}")
        return None

def parse_total_results(html):
    try:
        soup = BeautifulSoup(html, 'html.parser')
        results_text = soup.find('span', class_='results').get_text(strip=True)
        total = int(re.search(r'There are ([\d,]+) results', results_text).group(1).replace(',', ''))
        return max(1, total)
    except Exception as e:
        logging.error(f"Error parsing total results: {str(e)}")
        return None

def parse_articles(html):
    soup = BeautifulSoup(html, 'html.parser')
    articles = []
    
    for article in soup.find_all('article'):
        try:
            # Extract title and link from <a class="article-title">
            title_tag = article.find('a', class_='article-title')
            title = title_tag.get_text(strip=True) if title_tag else None
            link = title_tag['href'] if title_tag else None
            
            # Extract date from <time> tag
            date_tag = article.find('time')
            date = date_tag['datetime'] if date_tag else None
            
            if title and link and date:
                articles.append({'date': date, 'title': title, 'link': link})
        except Exception as e:
            logging.error(f"Error parsing article: {str(e)}")
    
    return articles

def save_results(articles, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, 'chicago_tribune.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(articles, f, indent=2, ensure_ascii=False)

@register_scraper('chicago_tribune')
def main(query, output_dir):
    logging.basicConfig(
        filename='chicago_tribune_scraper.log',
        level=logging.ERROR,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    session = setup_session()
    base_url = f"https://www.chicagotribune.com/page/{{page}}/?s={query}&post_type=post&category_name=local-news&orderby=date&order=desc&sp%5Bf%5D=2016-01-01&sp%5Bt%5D=2026-01-01&obit__spotlight&obit__site_name"
    
    # Get total results count
    initial_html = fetch_page(session, base_url, 1)
    if not initial_html:
        logging.error("Failed to fetch initial page")
        return

    total_results = parse_total_results(initial_html)
    print(total_results)
    if not total_results:
        logging.error("Couldn't determine total results, using default 1000 results")
        total_results = 1000  # Fallback value
    
    
    results_per_page = 10
    max_pages = (total_results + results_per_page - 1) // results_per_page  # Ceiling division


    all_articles = []
    page = 1
    retry_count = 0
    max_retries = 3

    with tqdm(total=max_pages, desc=f"Scraping '{query}'") as pbar:
        while page <= max_pages:
            html = fetch_page(session, base_url, page)
            if not html:
                if retry_count < max_retries:
                    retry_count += 1
                    time.sleep(2 ** retry_count)
                    continue
                else:
                    break

            articles = parse_articles(html)
            if not articles:
                break

            all_articles.extend(articles)
            pbar.update(1)
            page += 1
            retry_count = 0
            time.sleep(1)

    save_results(all_articles, output_dir)
    print(f"✅ Saved {len(all_articles)} articles to {output_dir}/chicago_tribune.json")

if __name__ == "__main__":
    main("local-news", "output")