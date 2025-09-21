"""API routes for file upload and dataset generation."""
import os
import zipfile
from typing import Union, Tuple, Dict, Any, List
from flask import Blueprint, request, current_app
from werkzeug.utils import secure_filename
from app.utils.dataset_generator import generate_dataset_from_files


bp = Blueprint('api', __name__, url_prefix='/api')


@bp.route('/health', methods=['GET'])
def health_check() -> Dict[str, str]:
    """Health check endpoint."""
    return {'status': 'healthy'}


@bp.route('/upload', methods=['POST'])
def upload_files() -> Union[Dict[str, Any], Tuple[Dict[str, str], int]]:
    """Upload one or more files for dataset generation."""
    # Handle multiple files
    files = []
    
    # Check if files were provided as a list or single file
    if 'files' in request.files:
        files = request.files.getlist('files')
    elif 'file' in request.files:
        files = [request.files['file']]
    else:
        return {'error': 'No file(s) provided'}, 400
    
    if not files or all(f.filename == '' for f in files):
        return {'error': 'Empty filename(s)'}, 400
    
    # Create uploads directory if it doesn't exist
    upload_dir = os.path.join(os.getcwd(), 'uploads')
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir)
    
    # Save all files
    file_paths = []
    for file in files:
        if file and file.filename != '':
            # Secure the filename
            filename = secure_filename(file.filename)
            
            # Save the file
            file_path = os.path.join(upload_dir, filename)
            file.save(file_path)
            
            # If it's a ZIP file, extract it and add individual files
            if filename.lower().endswith('.zip'):
                try:
                    with zipfile.ZipFile(file_path, 'r') as zip_ref:
                        # Extract all files
                        extract_dir = os.path.join(upload_dir, 'extracted')
                        if not os.path.exists(extract_dir):
                            os.makedirs(extract_dir)
                        zip_ref.extractall(extract_dir)
                        
                        # Add extracted files to file_paths
                        for root, dirs, extracted_files in os.walk(extract_dir):
                            for extracted_file in extracted_files:
                                extracted_file_path = os.path.join(root, extracted_file)
                                file_paths.append(extracted_file_path)
                except Exception as e:
                    return {'error': f'Error extracting ZIP file: {str(e)}'}, 500
            else:
                file_paths.append(file_path)
    
    if not file_paths:
        return {'error': 'No valid files provided'}, 400
    
    # Get configuration from environment
    provider = os.getenv('LITELLM_PROVIDER', 'ollama_chat')
    model = os.getenv('MODEL_NAME', 'gemma3:4b-it-fp16')
    
    try:
        # Generate dataset from multiple files
        result = generate_dataset_from_files(
            file_paths=file_paths,
            provider=provider,
            model=model
        )
        
        return {
            'message': f'Dataset generated successfully from {len(file_paths)} file(s)',
            'train_file': result['train_file'],
            'valid_file': result['valid_file'],
            'test_file': result['test_file'],
            'qa_count': result['qa_count'],
            'file_count': len(file_paths)
        }
    except Exception as e:
        return {'error': str(e)}, 500