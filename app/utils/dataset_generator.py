"""Dataset generator using LiteLLM."""
import os
import json
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
        for i in range(count):
            qa_pairs.append({
                "prompt": f"What is this text about? (Q{i+1})",
                "completion": f"This is a text about the content provided. (A{i+1})"
            })
    
    # Ensure we have the right number of pairs
    if len(qa_pairs) < count:
        # Add more pairs if we don't have enough
        for i in range(count - len(qa_pairs)):
            qa_pairs.append({
                "prompt": f"Additional question about the text? (Q{i+1})",
                "completion": f"Additional answer based on the text content. (A{i+1})"
            })
    elif len(qa_pairs) > count:
        # Trim if we have too many
        qa_pairs = qa_pairs[:count]
        
    return qa_pairs


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
    
    # Generate Q/A pairs for each dataset
    train_qa = generate_qa_pairs(text, counts['train'], provider, model)
    valid_qa = generate_qa_pairs(text, counts['valid'], provider, model)
    test_qa = generate_qa_pairs(text, counts['test'], provider, model)
    
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
    
    # Generate Q/A pairs for each dataset
    train_qa = generate_qa_pairs(combined_text, counts['train'], provider, model)
    valid_qa = generate_qa_pairs(combined_text, counts['valid'], provider, model)
    test_qa = generate_qa_pairs(combined_text, counts['test'], provider, model)
    
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