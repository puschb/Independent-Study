import json
import asyncio
import random
import time
from datetime import datetime
from typing import List, Dict, Any
import argparse
from tqdm import tqdm
import aiohttp
from newspaper import Article
from newspaper.configuration import Configuration

# Configuration to prevent downloading images/videos
config = Configuration()
config.fetch_images = False
config.keep_article_html = False
config.memoize_articles = False

class ArticleScraper:
    def __init__(self, input_file: str, output_file: str, referer: str, max_concurrent: int = 3):
        self.input_file = input_file
        self.output_file = output_file
        self.max_concurrent = max_concurrent
        self.results: List[Dict] = []
        self.failed_urls: List[str] = []
        self.request_count = 0
        self.start_time = time.time()
        self.referer = referer

        # Extract user agents from config
        self.user_agents = ["Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
                            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
                            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
                            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15"]

    async def fetch_article(self, session: aiohttp.ClientSession, article_data: Dict) -> Dict:
        """Fetch and parse an individual article with error handling and rate limiting"""
        url = article_data['link']
        result = {
            'link': url,
            'date': article_data.get('date'),
            'title': article_data.get('title'),
            'text': ''
        }

        try:
            # Rate limiting
            elapsed = time.time() - self.start_time
            if self.request_count / elapsed > 2:  # Max 2 requests/sec
                await asyncio.sleep(random.uniform(0.5, 1.5))

            headers = {
                'User-Agent': random.choice(self.user_agents),
                'Accept-Encoding': 'gzip, deflate',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Referer': self.referer
            }

            async with session.get(url, headers=headers, timeout=10) as response:
                if response.status == 200:
                    html = await response.text()
                    article = Article(url)
                    article.download(input_html=html)
                    article.parse()
                    result['text'] = article.text
                else:
                    self.failed_urls.append(url)
        except Exception as e:
            self.failed_urls.append(url)
            if 'newspaper' in str(e).lower():
                result['text'] = "Article content could not be extracted"
        
        self.request_count += 1
        return result

    async def process_batch(self, session: aiohttp.ClientSession, batch: List[Dict]):
        tasks = [self.fetch_article(session, article) for article in batch]
        for future in tqdm(asyncio.as_completed(tasks), total=len(tasks), desc="Processing batch"):
            result = await future
            if result['text']:
                self.results.append(result)

    async def run(self):
        # Load input data
        with open(self.input_file) as f:
            articles = json.load(f)

        # Set up HTTP session with connection pool
        connector = aiohttp.TCPConnector(limit_per_host=2, ssl=False)
        async with aiohttp.ClientSession(connector=connector) as session:
            # Process in batches to manage memory and connections
            batch_size = self.max_concurrent * 2
            for i in tqdm(range(0, len(articles), batch_size), desc="Processing articles"):
                batch = articles[i:i+batch_size]
                await self.process_batch(session, batch)
                await asyncio.sleep(random.uniform(1, 3))  # Random delay between batches

        # Save results
        with open(self.output_file, 'w') as f:
            json.dump(self.results, f, indent=2)

        # Save error log
        if self.failed_urls:
            with open('failed_urls.log', 'w') as f:
                f.write('\n'.join(self.failed_urls))

        print(f"Completed. Success: {len(self.results)}/{len(articles)}. Failed URLs logged to failed_urls.log")