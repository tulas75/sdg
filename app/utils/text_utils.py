"""Utility functions for text processing and Q/A pair calculation."""
import math
from typing import Dict


def calculate_qa_count(text_length: int) -> Dict[str, int]:
    """
    Calculate the number of Q/A pairs based on text length.
    
    Args:
        text_length: Length of the input text in characters
        
    Returns:
        Dictionary with counts for train, validation, and test sets
    """
    # Base calculation: 1 Q/A pair per 1000 characters, with a minimum of 3 pairs
    total_qa_pairs = max(3, math.ceil(text_length / 1000))
    
    # Split into train/valid/test (80/10/10)
    train_count = math.ceil(total_qa_pairs * 0.8)
    valid_count = math.ceil(total_qa_pairs * 0.1)
    test_count = total_qa_pairs - train_count - valid_count
    
    # Ensure we have at least 1 pair for valid and test if text is long enough
    if total_qa_pairs >= 3:
        if valid_count == 0:
            valid_count = 1
            train_count -= 1
        if test_count == 0:
            test_count = 1
            train_count -= 1
    
    return {
        'train': max(1, train_count),
        'valid': max(1, valid_count),
        'test': max(1, test_count),
        'total': total_qa_pairs
    }