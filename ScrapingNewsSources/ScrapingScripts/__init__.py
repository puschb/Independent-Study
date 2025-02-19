import importlib
from pathlib import Path
from typing import Dict, Callable

# Registry dictionary {scraper_name: main_function}
SCRAPER_REGISTRY: Dict[str, Callable] = {}

def register_scraper(name: str):
    """Decorator to register scrapers"""
    def decorator(func: Callable):
        SCRAPER_REGISTRY[name] = func
        return func
    return decorator

def discover_scrapers():
    """Auto-discover scrapers by scanning the directory"""
    package_dir = Path(__file__).parent
    for file in package_dir.glob('*.py'):
        module_name = file.stem
        if module_name == '__init__':
            continue
        try:
            importlib.import_module(f'ScrapingScripts.{module_name}')
        except ImportError as e:
            print(f"Failed to import {module_name}: {str(e)}")

# Auto-discover scrapers when package is imported
discover_scrapers()