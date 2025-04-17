import spacy

def get_ner_labels_and_descriptions():
    """
    Get all the NER labels from spaCy's en_core_web_sm model along with their descriptions.
    """
    # Load the English model
    nlp = spacy.load("en_core_web_sm")
    
    # Get all entity labels used by the model
    entity_labels = nlp.get_pipe("ner").labels
    
    # Create a dictionary to store labels and descriptions
    ner_labels_dict = {}
    
    # Add descriptions for each label using spacy.explain()
    for label in entity_labels:
        description = spacy.explain(label) or "No description available"
        ner_labels_dict[label] = description
    
    return ner_labels_dict

def print_ner_labels_and_descriptions():
    """
    Print all NER labels and their descriptions in a formatted way.
    """
    labels_dict = get_ner_labels_and_descriptions()
    
    print(f"{'Label':<10} | Description")
    print("-" * 60)
    
    for label, description in sorted(labels_dict.items()):
        print(f"{label:<10} | {description}")
    
    print(f"\nTotal NER labels in en_core_web_sm: {len(labels_dict)}")

if __name__ == "__main__":
    print_ner_labels_and_descriptions()