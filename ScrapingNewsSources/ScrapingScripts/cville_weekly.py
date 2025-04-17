import requests
import os
import json
import time
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

def fetch_page(session, url, page):
    try:
        full_url = url.format(page=page)
        response = session.get(
            full_url,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
            },
            timeout=15
        )
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"[ERROR] Error fetching page {page}: {str(e)}")
        return None

def parse_total_pages(html):
    try:
        soup = BeautifulSoup(html, 'html.parser')
        # Look for the pagination div
        pagination = soup.find('div', class_='page-navigation')
        if pagination:
            # Find all page links (excluding next/prev navigation)
            max_page = 1
            for link in pagination.find_all('a'):
                # Skip next/prev navigation links
                if 'next' in link.get('class', []) or 'prev' in link.get('class', []):
                    continue
                    
                try:
                    page_num = int(link.text.strip())
                    max_page = max(max_page, page_num)
                except ValueError:
                    continue
            
            return max_page
        
        # If pagination not found or can't determine max pages, use a default value
        return 100  
    except Exception as e:
        print(f"[ERROR] Error parsing total pages: {str(e)}")
        return 100  # Default to a large number on error

def parse_articles(html):
    soup = BeautifulSoup(html, 'html.parser')
    articles = []
    
    # Try a more general approach - find all articles
    for article in soup.find_all('article'):
        try:
            # Look for the header within each article
            header = article.find('header', class_='card-post-text-header')
            if not header:
                # If not found, try just finding any header
                header = article.find('header')
            
            if header:
                # Find the title link - try several approaches
                title_link = header.find('a')
                
                if not title_link:
                    # Try finding h4 first, then a inside it
                    h4 = header.find('h4')
                    if h4:
                        title_link = h4.find('a')
                
                if title_link:
                    title = title_link.get_text(strip=True)
                    link = title_link['href']
                    
                    if title and link:
                        articles.append({'title': title, 'link': link})
        except Exception as e:
            print(f"[ERROR] Error parsing article: {str(e)}")
    
    return articles

def save_results(articles, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, 'cville_weekly.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(articles, f, indent=2, ensure_ascii=False)

@register_scraper('cville_weekly')
def main(query="", output_dir="results"):
    """
    Scrape articles from c-ville.com
    
    Args:
        query: Search query (not used in this implementation but kept for API consistency)
        output_dir: Directory to save the results
    """
    print(f"Starting C-Ville Weekly scraper, saving results to: {output_dir}")

    session = setup_session()
    base_url = "https://c-ville.com/page/{page}/?s&sort=date_desc"
    
    # Get first page
    initial_html = fetch_page(session, base_url, 1)
    if not initial_html:
        print("[ERROR] Failed to fetch initial page")
        return

    # Get estimated total pages and first batch of articles
    max_pages = parse_total_pages(initial_html)
    all_articles = parse_articles(initial_html)
    print(f"Found {len(all_articles)} articles on first page. Total pages to scrape: {max_pages}")
    
    # Scrape remaining pages
    page = 2  # Start from page 2 since we already processed page 1
    retry_count = 0
    max_retries = 3
    consecutive_empty_pages = 0
    max_empty_pages = 3  # Stop after this many consecutive pages with no articles

    with tqdm(total=max_pages, desc="Scraping C-Ville articles") as pbar:
        pbar.update(1)  # Update for the first page we already processed
        
        while page <= max_pages:
            html = fetch_page(session, base_url, page)
            if not html:
                if retry_count < max_retries:
                    retry_count += 1
                    time.sleep(2 ** retry_count)
                    continue
                else:
                    print(f"[ERROR] Failed to fetch page {page} after {max_retries} retries")
                    break

            articles = parse_articles(html)
            if not articles:
                consecutive_empty_pages += 1
                if consecutive_empty_pages >= max_empty_pages:
                    print(f"[INFO] Stopping after {max_empty_pages} consecutive empty pages")
                    break
            else:
                consecutive_empty_pages = 0
                all_articles.extend(articles)

            pbar.update(1)
            page += 1
            retry_count = 0
            time.sleep(.1)  # Rate limiting to be nice to the server

    save_results(all_articles, output_dir)
    print(f"✅ Saved {len(all_articles)} articles to {output_dir}/cville_weekly.json")

if __name__ == "__main__":
    main()