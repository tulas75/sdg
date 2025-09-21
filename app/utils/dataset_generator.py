"""Dataset generator using LiteLLM."""
import os
import json
import random
import textwrap
from typing import Dict, Any, List
import litellm
from app.utils.text_utils import calculate_qa_count
from app.utils.file_handler import extract_text_from_file


def generate_qa_pairs(text: str, count: int, provider: str, model: str) -> List[Dict[str, str]]:
    """
    Generate Q/A pairs using LiteLLM.
    
    Args:
        text: Input text to generate Q/A pairs from
        count: Number of Q/A pairs to generate
        provider: LiteLLM provider
        model: Model name
        
    Returns:
        List of Q/A pairs in the format {"prompt": "...", "completion": "..."}
    """
    qa_pairs = []
    
    # Create the prompt for the LLM
    prompt = f"""
    Based on the following text, generate {count} high-quality question-answer pairs that would be suitable for training a language model.
    
    Types of questions to include (as appropriate for the text):
    - Factual questions about key information in the text
    - Conceptual questions that test understanding of main ideas
    - Inferential questions that require reasoning about the text
    - Summary questions that ask about the main points
    - Vocabulary questions about important terms (if applicable)
    
    Each pair should consist of:
    - A clear, concise question (prompt)
    - A complete, accurate answer (completion)
    
    Format each pair as a separate JSON object: {{"prompt": "question", "completion": "answer"}}
    
    Requirements:
    - Generate exactly {count} question-answer pairs
    - Ensure questions are diverse and not repetitive
    - Make questions unambiguous and answers comprehensive
    - Focus on the most important information in the text
    - Avoid yes/no questions unless they test specific factual information
    
    Text:
    {text}
    
    Please provide exactly {count} question-answer pairs in the specified JSON format.
    """
    
    try:
        # Call LiteLLM
        response = litellm.completion(
            model=f"{provider}/{model}",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,  # Reduced from 0.7 for more focused responses
            max_tokens=4000  # Added token limit for control
        )
        
        # Extract the response content
        content = response['choices'][0]['message']['content']
        
        # Try to parse the response as JSON
        # The LLM might return multiple JSON objects, a JSON array, or markdown code blocks
        content = content.strip()
        
        # Remove markdown code block markers if present
        if content.startswith("```json"):
            content = content[7:]  # Remove ```json
        elif content.startswith("```"):
            content = content[3:]  # Remove ```
        if content.endswith("```"):
            content = content[:-3]  # Remove ```
            
        # Try to parse as JSON array first
        try:
            parsed_content = json.loads(content)
            if isinstance(parsed_content, list):
                for item in parsed_content:
                    if isinstance(item, dict) and 'prompt' in item and 'completion' in item:
                        qa_pairs.append(item)
            elif isinstance(parsed_content, dict) and 'prompt' in parsed_content and 'completion' in parsed_content:
                qa_pairs.append(parsed_content)
        except json.JSONDecodeError:
            # If that fails, try line by line parsing
            lines = content.split('\n')
            for line in lines:
                line = line.strip()
                if line.startswith('{') and line.endswith('}'):
                    try:
                        qa_pair = json.loads(line)
                        if 'prompt' in qa_pair and 'completion' in qa_pair:
                            qa_pairs.append(qa_pair)
                    except json.JSONDecodeError:
                        continue
                
    except Exception as e:
        # Fallback: Generate simple Q/A pairs if LLM fails
        print(f"Error generating Q/A pairs with LLM: {e}")
        qa_pairs = generate_fallback_qa_pairs(text, count)
    
    # Ensure we have the right number of pairs
    if len(qa_pairs) < count:
        # Add more fallback pairs if we don't have enough
        additional_pairs = generate_fallback_qa_pairs(text, count - len(qa_pairs))
        qa_pairs.extend(additional_pairs)
    elif len(qa_pairs) > count:
        # Trim if we have too many
        qa_pairs = qa_pairs[:count]
        
    return qa_pairs


def generate_fallback_qa_pairs(text: str, count: int) -> List[Dict[str, str]]:
    """
    Generate fallback Q/A pairs when LLM fails.
    
    Args:
        text: Input text to generate Q/A pairs from
        count: Number of Q/A pairs to generate
        
    Returns:
        List of Q/A pairs in the format {"prompt": "...", "completion": "..."}
    """
    qa_pairs = []
    
    # Split text into sentences for better Q/A generation
    sentences = text.split('.')
    sentences = [s.strip() for s in sentences if s.strip()]
    
    # Extract key information for Q/A generation
    # Use first few sentences as context
    context = '. '.join(sentences[:min(5, len(sentences))]) + '.'
    
    # For large documents, extract key phrases
    words = text.split()
    key_phrases = []
    
    # Extract some key phrases from the text (every 50th word as a sample)
    for i in range(0, min(len(words), 200), 10):
        phrase = ' '.join(words[i:i+3])
        if len(phrase) > 5 and len(phrase) < 50:
            key_phrases.append(phrase)
    
    # Generate diverse fallback Q/A pairs
    for i in range(count):
        # Rotate through different question types
        question_type = i % 4
        
        if question_type == 0 and sentences:
            # Question about a sentence
            sentence_idx = i % len(sentences)
            qa_pairs.append({
                "prompt": f"What is the main point of this statement: '{sentences[sentence_idx][:100]}...'?",
                "completion": f"The statement conveys that {sentences[sentence_idx][:150]}..."
            })
        elif question_type == 1 and key_phrases:
            # Question about a key phrase
            phrase_idx = i % len(key_phrases)
            qa_pairs.append({
                "prompt": f"What does the phrase '{key_phrases[phrase_idx]}' refer to in this context?",
                "completion": f"In this context, '{key_phrases[phrase_idx]}' refers to a key concept discussed in the text."
            })
        elif question_type == 2:
            # Summary question
            qa_pairs.append({
                "prompt": "What are the key points covered in this document?",
                "completion": f"Based on the content, key points include: {context[:200]}..."
            })
        else:
            # General question about the document
            qa_pairs.append({
                "prompt": f"What is the main topic discussed in section {i+1}?",
                "completion": "The text discusses various aspects of the main subject matter."
            })
            
    return qa_pairs[:count]


def write_jsonl_file(filepath: str, qa_pairs: List[Dict[str, str]]) -> None:
    """
    Write Q/A pairs to a JSONL file.
    
    Args:
        filepath: Path to the output file
        qa_pairs: List of Q/A pairs
    """
    with open(filepath, 'w', encoding='utf-8') as f:
        for pair in qa_pairs:
            f.write(json.dumps(pair) + '\n')


def generate_dataset(file_path: str, provider: str, model: str) -> Dict[str, Any]:
    """
    Generate train/valid/test datasets from an input file.
    
    Args:
        file_path: Path to the input file
        provider: LiteLLM provider
        model: Model name
        
    Returns:
        Dictionary with paths to generated files and statistics
    """
    # Extract text from the input file based on its type
    text = extract_text_from_file(file_path)
    
    # Calculate Q/A pair counts
    counts = calculate_qa_count(len(text))
    
    # Generate all Q/A pairs at once
    all_qa_pairs = generate_qa_pairs(text, counts['total'], provider, model)
    
    # Randomly shuffle the Q/A pairs
    random.shuffle(all_qa_pairs)
    
    # Distribute Q/A pairs according to the calculated counts
    train_qa = all_qa_pairs[:counts['train']]
    valid_qa = all_qa_pairs[counts['train']:counts['train'] + counts['valid']]
    test_qa = all_qa_pairs[counts['train'] + counts['valid']:]
    
    # Create output directory if it doesn't exist
    output_dir = os.path.join(os.getcwd(), 'output')
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Write JSONL files
    train_file = os.path.join(output_dir, 'train.jsonl')
    valid_file = os.path.join(output_dir, 'valid.jsonl')
    test_file = os.path.join(output_dir, 'test.jsonl')
    
    write_jsonl_file(train_file, train_qa)
    write_jsonl_file(valid_file, valid_qa)
    write_jsonl_file(test_file, test_qa)
    
    return {
        'train_file': train_file,
        'valid_file': valid_file,
        'test_file': test_file,
        'qa_count': counts['total']
    }


def generate_dataset_from_files(file_paths: List[str], provider: str, model: str) -> Dict[str, Any]:
    """
    Generate train/valid/test datasets from multiple input files.
    
    Args:
        file_paths: List of paths to the input files
        provider: LiteLLM provider
        model: Model name
        
    Returns:
        Dictionary with paths to generated files and statistics
    """
    # Extract and concatenate text from all input files
    combined_text = ""
    for file_path in file_paths:
        try:
            text = extract_text_from_file(file_path)
            combined_text += f"\n\n--- Content from {os.path.basename(file_path)} ---\n\n{text}"
        except Exception as e:
            raise Exception(f"Error processing file {file_path}: {str(e)}")
    
    # Calculate Q/A pair counts based on combined text length
    counts = calculate_qa_count(len(combined_text))
    
    # Generate all Q/A pairs at once
    all_qa_pairs = generate_qa_pairs(combined_text, counts['total'], provider, model)
    
    # Randomly shuffle the Q/A pairs
    random.shuffle(all_qa_pairs)
    
    # Distribute Q/A pairs according to the calculated counts
    train_qa = all_qa_pairs[:counts['train']]
    valid_qa = all_qa_pairs[counts['train']:counts['train'] + counts['valid']]
    test_qa = all_qa_pairs[counts['train'] + counts['valid']:]
    
    # Create output directory if it doesn't exist
    output_dir = os.path.join(os.getcwd(), 'output')
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Write JSONL files
    train_file = os.path.join(output_dir, 'train.jsonl')
    valid_file = os.path.join(output_dir, 'valid.jsonl')
    test_file = os.path.join(output_dir, 'test.jsonl')
    
    write_jsonl_file(train_file, train_qa)
    write_jsonl_file(valid_file, valid_qa)
    write_jsonl_file(test_file, test_qa)
    
    return {
        'train_file': train_file,
        'valid_file': valid_file,
        'test_file': test_file,
        'qa_count': counts['total']
    }