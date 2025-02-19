import json
import re
import time
from pathlib import Path
from datetime import datetime
import requests
from typing import Dict, Any, List, Optional
import traceback

# ================= CURRENTLY BROKEN =======================

class SiLive:
    def __init__(self, config: Dict[str, Any], output_dir: str):
        self.config = config
        self.output_dir = Path(output_dir)
        self.articles: List[Dict] = []
        self.errors: List[Dict] = []
        self.current_page_param = None
        self.total_results = None
        
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def get_nested_value(self, item: Dict, path: str) -> Any:
        keys = path.split('.')
        current = item
        for key in keys:
            if isinstance(current, dict):
                current = current.get(key)
            elif isinstance(current, list) and key.isdigit():
                current = current[int(key)] if int(key) < len(current) else None
            else:
                return None
            if current is None:
                break
        return current

    def build_params(self) -> Dict:
        params = self._process_parameters()
        params['query'] = self.config['query']
        
        if self.config['pagination']['type'] == 'offset':
            params[self.config['pagination']['parameter']] = self.current_page_param
        elif self.config['pagination']['type'] == 'cursor' and self.current_page_param:
            params[self.config['pagination']['parameter']] = self.current_page_param
        return params

    def _process_parameters(self) -> Dict:
        """Convert array parameters to WordPress-style indexed keys"""
        processed = {}
        for key, value in self.config['parameters'].items():
            if isinstance(value, list):
                for i, item in enumerate(value):
                    processed[f"{key}[{i}]"] = item
            else:
                processed[key] = value
        return processed

    def parse_response(self, response_text: str) -> Optional[Dict]:
        """Robust JSON parsing with advanced error correction"""
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            if self.config['name'] == 'silive':
                try:
                    # Extract JSON payload with improved regex
                    match = re.search(r"JSON\.parse\(['\"](.*?)['\"]\)", response_text, re.DOTALL)
                    if not match:
                        return None

                    json_str = match.group(1)
                    
                    json_str = json_str.replace("\\'","'").replace('\\\\"','\\"')
                    return json.loads(json_str, strict=False)

                except Exception as e:
                    self.log_error(f"Parse error: {str(e)}\n Stacktrace: \n{traceback.format_exc()}", self.current_page_param)
                    self.debug_failed_parse(response_text, json_str)
            return None

    def process_item(self, item: Dict) -> Dict:
        processed = {}
        for field, path in self.config['field_mappings'].items():
            value = self.get_nested_value(item, path)
            
            # Handle nested lists of content highlights
            if field == 'description' and isinstance(value, list):
                processed[field] = " ".join(
                    re.sub(r"<mark>|<\/mark>", "", text) 
                    for text in value
                )
            elif isinstance(value, list):
                processed[field] = ' '.join(str(v) for v in value)
            else:
                processed[field] = value
                
            # Fix URL formatting
            if field == 'link' and processed[field]:
                processed[field] = f"https://{processed[field].lstrip('www.')}"
        return processed

    def handle_pagination(self, response_data: Dict):
        pagination_config = self.config['pagination']
        
        if pagination_config['type'] == 'offset':
            self.total_results = self.get_nested_value(response_data, pagination_config['total_field'])
            self.current_page_param += pagination_config['batch_size']
            print(f'self.current_page_param after op: {self.current_page_param}')
            if self.current_page_param >= self.total_results:
                self.current_page_param = None
        elif pagination_config['type'] == 'cursor':
            self.current_page_param = self.get_nested_value(response_data, pagination_config['response_field'])

    def scrape(self):
        self.current_page_param = self.config['pagination'].get('initial_value', 0)
        retries = 0

        cur_page = 0
        while self.current_page_param is not None:
            print(f'On page {cur_page}')
            cur_page += 1
            try:
                response = requests.get(
                    self.config['base_url'],
                    params=self.build_params(),
                    headers=self.config['headers'],
                    timeout=10
                )

                if response.status_code != 200:
                    self.log_error(f"HTTP {response.status_code}", self.current_page_param)
                    if response.status_code == 429:
                        self.handle_rate_limit(response)
                        continue
                    print(f"HTTP {response.status_code}")
                    print(f'HTTP Response text: {response.text}')
                    break

                data = self.parse_response(response.text)
                if not data:
                    self.log_error("Invalid response format", self.current_page_param)
                    break

                items = self.get_nested_value(data, 'results') if 'results' in data else data.get('items', [])
                for item in items:
                    self.articles.append(self.process_item(item))

                self.handle_pagination(data)
                retries = 0
                time.sleep(self.config['request_settings']['delay'])

            except Exception as e:
                self.log_error(f'{str(e)}\n Stacktrace: \n{traceback.format_exc()}', self.current_page_param)
                retries += 1
                if retries > self.config['request_settings']['max_retries']:
                    break
                time.sleep(self.config['request_settings']['retry_delay'])

        self.save_results()

    def log_error(self, error: str, context: Any):
        self.errors.append({
            'timestamp': datetime.now().isoformat(),
            'error': error,
            'context': context,
            'config': self.config['name']
        })

    def handle_rate_limit(self, response: requests.Response):
        retry_after = int(response.headers.get('Retry-After', 60))
        print(f"Rate limited. Waiting {retry_after} seconds")
        time.sleep(retry_after)

    def save_results(self):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        if self.articles:
            with open(self.output_dir / f'articles_{timestamp}.json', 'w') as f:
                json.dump(self.articles, f, indent=2, )
        
        if self.errors:
            with open(self.output_dir / f'errors_{timestamp}.json', 'w') as f:
                json.dump(self.errors, f, indent=2)


    def debug_failed_parse(self, raw: str, processed: str):
        """Save debugging information for failed parses"""
        with open('parse_failure.log', 'a') as f:
            f.write(f"\n{'='*80}\n")
            f.write(f"Timestamp: {datetime.now().isoformat()}\n")
            f.write(f"Original Response:\n{raw}\n")
            f.write(f"Processed JSON:\n{processed}\n")
            f.write(f"{'='*80}\n")
            