"""
immigration_classifier.py - Classify if articles are immigration-related using Llama-3.2-3B-Instruct
running locally on GPU with optimized batch processing.
"""

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from typing import List, Dict, Any, Optional
from tqdm import tqdm
import re
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class LlamaImmigrationClassifier:
    """Classifier that uses Llama-3.2-3B-Instruct to determine if articles are immigration-related."""
    
    def __init__(
        self,
        model_name: str = "meta-llama/Llama-3.2-3B-Instruct",
        batch_size: int = 8,  # Increased default batch size
        device: Optional[str] = None,
        max_length: int = 2048,
        temperature: float = 0.1
    ):
        """
        Initialize the Llama-based immigration classifier.
        
        Args:
            model_name: HuggingFace model to use
            batch_size: Number of articles to process at once
            device: Device to run inference on ('cuda', 'cpu', etc.)
                   If None, will auto-detect GPU availability
            max_length: Maximum token length for generated responses
            temperature: Sampling temperature (lower = more deterministic)
        """
        # Auto-detect GPU if available
        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"
        
        # Log device being used
        print(f"Using device: {device}")
        if device == "cuda":
            print(f"GPU: {torch.cuda.get_device_name(0)}")
            
        self.device = device
        self.batch_size = batch_size
        self.max_length = max_length
        self.temperature = temperature
        
        # Load model and tokenizer
        print(f"Loading Llama model: {model_name}")
        try:
            # Get Hugging Face access token from environment
            hf_token = os.environ.get("HUGGINGFACE_TOKEN")
            if not hf_token:
                print("WARNING: HUGGINGFACE_TOKEN not found in .env file")
                print("You may not be able to access Llama models without authentication")
                
            self.tokenizer = AutoTokenizer.from_pretrained(
                model_name,
                token=hf_token
            )
            
            # Set padding token and use left-padding for decoder-only models
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
            self.tokenizer.padding_side = 'left'  # Important for decoder-only models
            
            # Configure model to use optimizations for inference
            self.model = AutoModelForCausalLM.from_pretrained(
                model_name,
                torch_dtype=torch.float16 if device == "cuda" else torch.float32,
                device_map="auto" if device == "cuda" else None,
                low_cpu_mem_usage=True,
                token=hf_token
            )
            
            print("Model loaded successfully")
            
        except Exception as e:
            print(f"Error loading model: {e}")
            raise
            
    def _create_prompt(self, title: str) -> str:
        """
        Create a prompt for the language model.
        
        Args:
            title: Article title
            
        Returns:
            Formatted prompt string
        """
        prompt = f"""<|begin_of_text|><|system|>
You are an expert at identifying articles related to immigration. 
Analyze if the following article title is related to immigration, refugees, migrants, asylum seekers, 
border policy, deportation, visas, or other immigration-related topics.
Respond with ONLY a single word: YES or NO.<|end_of_text|>

<|user|>
Article Title: {title}

Is this article about immigration?<|end_of_text|>

<|assistant|>"""
        return prompt
    
    def _parse_response(self, response: str) -> bool:
        """
        Parse the model's response to determine if it's a positive classification.
        
        Args:
            response: Raw model output
            
        Returns:
            Boolean indicating if article is immigration-related
        """
        # Clean up response and extract just the YES/NO
        clean_response = response.strip().upper()
        
        # Use regex to find YES/NO
        yes_match = re.search(r'\bYES\b', clean_response)
        no_match = re.search(r'\bNO\b', clean_response)
        
        if yes_match and not no_match:
            return True
        elif no_match and not yes_match:
            return False
        else:
            # If ambiguous or neither YES/NO found, look at first word
            first_word = clean_response.split()[0] if clean_response else ""
            return first_word == "YES"
    
    def is_immigration_related(self, title: str) -> bool:
        """
        Determine if a single article is immigration-related based on its title.
        
        Args:
            title: Article title
            
        Returns:
            Boolean indicating if article is immigration-related
        """
        if not title or not isinstance(title, str):
            return False
        
        # Use the batch classifier with a single item for consistency
        return self.classify_titles([title])[0]
    
    def classify_titles(self, titles: List[str]) -> List[bool]:
        """
        Classify a batch of article titles to determine if they're immigration-related.
        Optimized for GPU batch processing.
        
        Args:
            titles: List of article titles
            
        Returns:
            List of booleans indicating for each article if it's immigration-related
        """
        if not titles:
            return []
        
        # Filter out invalid titles and keep track of their indices
        valid_titles = []
        valid_indices = []
        
        for i, title in enumerate(titles):
            if title and isinstance(title, str):
                valid_titles.append(title)
                valid_indices.append(i)
        
        # If no valid titles, return all False
        if not valid_titles:
            return [False] * len(titles)
        
        # Create prompts for all valid titles
        prompts = [self._create_prompt(title) for title in valid_titles]
        
        # Process in batches
        results = []
        
        for i in tqdm(range(0, len(prompts), self.batch_size), desc="Classifying articles"):
            batch_prompts = prompts[i:i+self.batch_size]
            
            # Tokenize inputs - process the whole batch at once
            inputs = self.tokenizer(batch_prompts, padding=True, return_tensors="pt").to(self.device)
            
            # Generate outputs in a single batch
            with torch.no_grad():
                generated_ids = self.model.generate(
                    **inputs,
                    max_new_tokens=20,
                    do_sample=True,
                    temperature=self.temperature,
                    top_p=0.95,
                    pad_token_id=self.tokenizer.eos_token_id
                )
            
            # Get the length of each input sequence (they can be different due to padding)
            input_lengths = [len(self.tokenizer.encode(prompt)) for prompt in batch_prompts]
            
            # Get only the generated tokens for each sequence
            batch_results = []
            for j, length in enumerate(input_lengths):
                # Extract generated tokens for this sequence
                generated_text = self.tokenizer.decode(
                    generated_ids[j, length:], 
                    skip_special_tokens=True
                )
                batch_results.append(self._parse_response(generated_text))
            
            results.extend(batch_results)
        
        # Create the final result list with the same length as the input
        final_results = [False] * len(titles)
        for i, result in zip(valid_indices, results):
            final_results[i] = result
        
        return final_results
    
    def classify_articles(self, articles: List[Dict[str, Any]], title_key: str = 'title') -> List[bool]:
        """
        Classify a list of article dictionaries based only on their titles.
        
        Args:
            articles: List of article dictionaries
            title_key: Key to access title in article dict
            
        Returns:
            List of booleans indicating for each article if it's immigration-related
        """
        titles = [article.get(title_key, "") for article in articles]
        return self.classify_titles(titles)


def get_immigration_classifier(device=None, batch_size=8):
    """
    Factory function to create and return a Llama-based immigration classifier.
    
    Args:
        device: Device to run on (auto-detected if None)
        batch_size: Batch size for processing
        
    Returns:
        LlamaImmigrationClassifier instance
    """
    return LlamaImmigrationClassifier(
        device=device,
        batch_size=batch_size
    )


# Example usage
if __name__ == "__main__":
    # Check if HF token is configured
    if not os.environ.get("HUGGINGFACE_TOKEN"):
        print("⚠️ HUGGINGFACE_TOKEN not found in environment")
        print("Please create a .env file with your token:")
        print("HUGGINGFACE_TOKEN=your_hf_token_here")
        print("You can get a token at: https://huggingface.co/settings/tokens")
        exit(1)
        
    # Test the classifier
    classifier = get_immigration_classifier(batch_size=8)
    
    test_titles = [
        "New immigration policy announced by administration",
        "Local sports team wins championship",
        "Migrants face challenges at southern border",
        "Weather forecast shows rain for the weekend",
        "School board approves new budget",
        "Asylum seekers waiting for court hearings",
        "Bronx Times Reporter: June7, 2024"
    ]
    
    results = classifier.classify_titles(test_titles)
    
    for title, is_immigration in zip(test_titles, results):
        print(f"Immigration-related: {is_immigration} - {title}")