"""
immigration_classifier.py - Helper module to classify if articles are immigration-related
using an open source language model running on GPU.
"""

import torch
from transformers import pipeline, AutoModelForSequenceClassification, AutoTokenizer
import numpy as np
from typing import List, Union, Dict, Any
from tqdm import tqdm

class ImmigrationClassifier:
    """Classifier to determine if text is related to immigration using an LLM."""
    
    def __init__(
        self, 
        model_name: str = "facebook/bart-large-mnli",  # Good zero-shot classification model
        batch_size: int = 8,
        threshold: float = 0.7,  # Confidence threshold
        device: str = None
    ):
        """
        Initialize the immigration classifier.
        
        Args:
            model_name: HuggingFace model to use for classification
            batch_size: Number of articles to process at once
            threshold: Confidence threshold for positive classification
            device: Device to run inference on ('cuda', 'cpu', etc.)
                    If None, will auto-detect GPU availability
        """
        # Auto-detect GPU if available
        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"
        
        # Log device being used
        print(f"Using device: {device}")
        if device == "cuda":
            print(f"GPU: {torch.cuda.get_device_name(0)}")
        
        # Initialize model and tokenizer
        self.device = device
        self.batch_size = batch_size
        self.threshold = threshold
        
        # Load model and create classification pipeline
        self.classifier = pipeline(
            "zero-shot-classification",
            model=model_name,
            device=0 if device == "cuda" else -1
        )
        
        # Define immigration-related labels for classification
        self.immigration_labels = [
            "immigration",
        ]
        
        print(f"Immigration classifier initialized with {model_name}")
    
    def is_immigration_related(self, title: str) -> bool:
        """
        Determine if a single article title is immigration-related.
        
        Args:
            title: The article title text
            
        Returns:
            Boolean indicating if the article is immigration-related
        """
        results = self.classify_titles([title])
        return results[0]
    
    def classify_titles(self, titles: List[str]) -> List[bool]:
        """
        Classify a list of article titles to determine if they're immigration-related.
        
        Args:
            titles: List of article titles
            
        Returns:
            List of booleans indicating for each title if it's immigration-related
        """
        # Skip empty batch
        if not titles:
            return []
        
        results = []
        
        # Process in batches for efficiency
        for i in range(0, len(titles), self.batch_size):
            batch = titles[i:i+self.batch_size]
            
            # Skip empty strings or None values
            valid_indices = [j for j, title in enumerate(batch) if title and isinstance(title, str)]
            valid_batch = [batch[j] for j in valid_indices]
            
            if not valid_batch:
                # If no valid titles in this batch, mark all as False
                batch_results = [False] * len(batch)
            else:
                # Run classification on valid titles
                outputs = self.classifier(
                    valid_batch, 
                    self.immigration_labels, 
                    multi_label=True
                )
                
                # Process classification results
                batch_results = [False] * len(batch)
                
                for idx, output in enumerate(outputs):
                    # Get the scores for immigration-related labels
                    scores = output['scores']
                    labels = output['labels']
                    
                    # Check if any immigration-related label has a high enough score
                    max_score = max(scores)
                    if max_score >= self.threshold:
                        orig_idx = valid_indices[idx]
                        batch_results[orig_idx] = True
            
            results.extend(batch_results)
        
        return results

    def classify_articles(self, articles: List[Dict[str, Any]], title_key: str = 'title') -> List[bool]:
        """
        Classify a list of article dictionaries based on their titles.
        
        Args:
            articles: List of article dictionaries
            title_key: Key to access the title in each article dict
            
        Returns:
            List of booleans indicating for each article if it's immigration-related
        """
        titles = [article.get(title_key, "") for article in articles]
        return self.classify_titles(titles)


def get_immigration_classifier(model_name=None, batch_size=8, threshold=0.7, device=None):
    """
    Factory function to create and return an immigration classifier.
    
    Args:
        model_name: Optional model name to override default
        batch_size: Batch size for processing
        threshold: Confidence threshold
        device: Device to run on (auto-detected if None)
        
    Returns:
        ImmigrationClassifier instance
    """
    # Can switch to different models based on needs:
    # - "facebook/bart-large-mnli": Good zero-shot classifier (default)
    # - "MoritzLaurer/deberta-v3-large-zeroshot-v1.1-all-33": Better but larger
    # - "cross-encoder/nli-deberta-v3-small": Smaller, faster option
    if model_name is None:
        model_name = "facebook/bart-large-mnli"
        
    return ImmigrationClassifier(
        model_name=model_name,
        batch_size=batch_size,
        threshold=threshold,
        device=device
    )


# Example usage:
if __name__ == "__main__":
    # Test the classifier
    classifier = get_immigration_classifier()
    
    test_titles = [
        # Simple examples
        "New immigration policy announced by administration",
        "Local sports team wins championship",
        "Migrants face challenges at southern border",
        "Weather forecast shows rain for the weekend",
        "School board approves new budget",
        "Asylum seekers waiting for court hearings",
        
        # Hard positive examples (should be classified as immigration-related)
        "Administration unveils new framework for those seeking harbor within our borders",
        "Cross-border movements surge as regional instability continues",
        "New paper documents detail mandatory requirements for foreign nationals",
        "Study examines long-term integration outcomes for newcomers",
        "Policy shift impacts those awaiting status regularization hearings",
        "Children separated from guardians at entry points receive new processing guidelines",
        "Economic impact of demographic shifts from international relocations",
        "Lawmakers debate bipartisan framework for status adjustment pathways",
        "NGOs respond to influx of displaced persons seeking shelter",
        "Court rules on documentation requirements for non-citizen residents",
        
        # Hard negative examples (should NOT be classified as immigration-related)
        "Researchers document cross-border wildlife migration patterns",
        "City sanctuary provides refuge for endangered bird species",
        "Green card holders win local poker tournament",
        "Border collies demonstrate impressive herding techniques at dog show",
        "Company seeks naturalization of artificial plants for office spaces",
        "Digital visa platform launches for online game tournament",
        "Refugees from corporate merger seek new positions",
        "Urban planning requires path to citizenship engagement in neighborhood development",
        "Temporary protected status established for historic buildings during renovation",
        "Family separation anxiety common during first days of kindergarten",
    ]
    
    
    results = classifier.classify_titles(test_titles)
    
    for title, is_immigration in zip(test_titles, results):
        print(f"Immigration-related: {is_immigration} - {title}")