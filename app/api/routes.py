"""API routes for file upload and dataset generation."""
import os
import zipfile
import uuid
import threading
import time
from typing import Union, Tuple, Dict, Any, List
from flask import Blueprint, request, current_app, jsonify
from werkzeug.utils import secure_filename
from app.utils.dataset_generator import generate_dataset_from_files
from app.utils.xlsx_handler import extract_fields_from_xlsx, generate_fake_data_with_llm, save_fake_data_to_file


bp = Blueprint('api', __name__, url_prefix='/api')

# In-memory storage for task status (in production, use a database)
task_status = {}

def generate_task_id():
    """Generate a unique task ID."""
    return str(uuid.uuid4())

def update_task_status(task_id, status, message="", result=None):
    """Update the status of a task."""
    task_status[task_id] = {
        'status': status,  # 'queued', 'processing', 'completed', 'failed'
        'message': message,
        'result': result,
        'timestamp': time.time()
    }

def get_task_status(task_id):
    """Get the status of a task."""
    return task_status.get(task_id, {'status': 'not_found', 'message': 'Task not found'})


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
    
    # Generate a task ID
    task_id = generate_task_id()
    
    # Save all files
    file_paths = []
    for file in files:
        if file and file.filename != '':
            # Secure the filename
            filename = secure_filename(file.filename)
            
            # Save the file
            file_path = os.path.join(upload_dir, filename)
            file.save(file_path)
            file_paths.append(file_path)
    
    if not file_paths:
        return {'error': 'No valid files provided'}, 400
    
    # Get configuration from environment
    provider = os.getenv('LITELLM_PROVIDER', 'ollama_chat')
    model = os.getenv('MODEL_NAME', 'gemma3:4b-it-fp16')
    
    # Start the processing in a background thread
    thread = threading.Thread(
        target=process_files_async,
        args=(task_id, file_paths, provider, model)
    )
    thread.start()
    
    # Return task ID immediately
    return {
        'task_id': task_id,
        'message': 'File upload successful. Processing started.',
        'status_url': f'/api/status/{task_id}'
    }


def process_files_async(task_id, file_paths, provider, model):
    """Process files asynchronously and update task status."""
    try:
        # Update task status to processing
        update_task_status(task_id, 'processing', 'Processing files...')
        
        # Generate dataset from multiple files
        result = generate_dataset_from_files(
            file_paths=file_paths,
            provider=provider,
            model=model
        )
        
        # Update task status to completed
        update_task_status(task_id, 'completed', 
                          f'Dataset generated successfully from {len(file_paths)} file(s)', 
                          result)
    except Exception as e:
        # Update task status to failed
        update_task_status(task_id, 'failed', str(e))


@bp.route('/fake-data', methods=['POST'])
def generate_fake_data() -> Union[Dict[str, Any], Tuple[Dict[str, str], int]]:
    """Generate fake data from an XLSX template."""
    # Check if file was provided
    if 'file' not in request.files:
        return {'error': 'No file provided'}, 400
    
    file = request.files['file']
    if file.filename == '':
        return {'error': 'Empty filename'}, 400
    
    # Get parameters
    try:
        row_count = int(request.form.get('row_count', 10))  # Default to 10 rows
        output_format = request.form.get('format', 'csv')  # Default to CSV
    except ValueError:
        return {'error': 'Invalid row_count parameter'}, 400
    
    # Validate output format
    if output_format not in ['csv', 'xlsx']:
        return {'error': 'Invalid format. Supported formats: csv, xlsx'}, 400
    
    # Create uploads directory if it doesn't exist
    upload_dir = os.path.join(os.getcwd(), 'uploads')
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir)
    
    # Generate a task ID
    task_id = generate_task_id()
    
    # Secure the filename
    filename = secure_filename(file.filename)
    
    # Save the file
    file_path = os.path.join(upload_dir, filename)
    file.save(file_path)
    
    # Get configuration from environment
    provider = os.getenv('LITELLM_PROVIDER', 'ollama_chat')
    model = os.getenv('MODEL_NAME', 'gemma3:4b-it-fp16')
    
    # Start the fake data generation in a background thread
    thread = threading.Thread(
        target=generate_fake_data_async,
        kwargs={
            'task_id': task_id,
            'file_path': file_path,
            'row_count': row_count,
            'output_format': output_format,
            'provider': provider,
            'model': model
        }
    )
    thread.start()
    
    # Return task ID immediately
    return {
        'task_id': task_id,
        'message': f'XLSX template upload successful. Fake data generation started for {row_count} rows.',
        'status_url': f'/api/status/{task_id}'
    }


def generate_fake_data_async(**kwargs):
    """Generate fake data asynchronously and update task status."""
    task_id = kwargs['task_id']
    file_path = kwargs['file_path']
    row_count = kwargs['row_count']
    output_format = kwargs['output_format']
    provider = kwargs['provider']
    model = kwargs['model']
    
    try:
        # Update task status to processing
        update_task_status(task_id, 'processing', 'Processing XLSX template...')
        
        # Extract fields from XLSX file (now supports XLSForm)
        fields_info = extract_fields_from_xlsx(file_path)
        
        # Update task status
        update_task_status(task_id, 'processing', f'Generating {row_count} rows of fake data...')
        
        # Generate fake data using LLM
        fake_data = generate_fake_data_with_llm(fields_info, row_count, provider, model)
        
        # Create output directory if it doesn't exist
        output_dir = os.path.join(os.getcwd(), 'output')
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        # Generate output filename
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        output_filename = f"{base_name}_fake_data.{output_format}"
        output_file_path = os.path.join(output_dir, output_filename)
        
        # Save fake data to file
        saved_file_path = save_fake_data_to_file(fake_data, output_file_path, output_format)
        
        # Update task status to completed
        update_task_status(task_id, 'completed', 
                          f'Fake data generated successfully with {row_count} rows', 
                          {
                              'output_file': saved_file_path,
                              'row_count': row_count,
                              'format': output_format
                          })
    except Exception as e:
        # Update task status to failed
        update_task_status(task_id, 'failed', str(e))


@bp.route('/status/<task_id>', methods=['GET'])
def get_status(task_id) -> Dict[str, Any]:
    """Get the status of a processing task."""
    status = get_task_status(task_id)
    return status