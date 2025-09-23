# Synthetic Dataset Generator (SDG)

A Flask-based API service that generates synthetic Q/A datasets from user-uploaded files using LiteLLM.

## Features

- Upload multiple files of different types (PDF, DOCX, TXT, ZIP) through a REST API
- Generate synthetic question-answer pairs using LLMs via LiteLLM
- Automatically calculate the number of Q/A pairs based on combined text length
- Output datasets in JSONL format (train.jsonl, valid.jsonl, test.jsonl)
- Generate fake data from XLSX templates with customizable row counts
- Support for XLSForm structure with single and multiple choice questions
- Support for multiple file formats:
  - PDF (.pdf)
  - Word Documents (.docx)
  - Plain Text (.txt)
  - ZIP archives containing any of the above
  - Excel Templates (.xlsx) for fake data generation
- Automatic language detection and generation in the same language as input text
- Streamlit web interface for easy file upload and dataset generation

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Copy `.env.example` to `.env` and configure as needed:
   ```bash
   cp .env.example .env
   ```

3. Run the application:
   ```bash
   python -m app.main
   ```

The server will start on `http://localhost:5001`.

## API Endpoints

### Health Check
```
GET /api/health
```

Example:
```bash
curl http://localhost:5001/api/health
```

### Upload Files and Generate Dataset
```
POST /api/upload
```

Form data:
- `file`: A single file to process
- `files`: Multiple files to process (use multiple `files` parameters)

Examples:
```bash
# Single file
curl -X POST -F "file=@document.pdf" http://localhost:5001/api/upload

# Multiple files
curl -X POST -F "files=@document1.pdf" -F "files=@document2.docx" http://localhost:5001/api/upload

# ZIP file containing multiple documents
curl -X POST -F "file=@documents.zip" http://localhost:5001/api/upload
```

The API supports the following file types:
- PDF (.pdf)
- Word Documents (.docx)
- Plain Text (.txt)
- ZIP archives (.zip) containing any of the above

### Generate Fake Data from XLSX Template
```
POST /api/fake-data
```

Form data:
- `file`: XLSX template file
- `row_count`: Number of rows to generate (optional, default: 10)
- `format`: Output format ('csv' or 'xlsx', optional, default: 'csv')

Examples:
```bash
# Generate 100 rows of fake data in CSV format
curl -X POST -F "file=@template.xlsx" -F "row_count=100" http://localhost:5001/api/fake-data

# Generate 50 rows of fake data in XLSX format
curl -X POST -F "file=@template.xlsx" -F "row_count=50" -F "format=xlsx" http://localhost:5001/api/fake-data

# Generate fake data from XLSForm with choices
curl -X POST -F "file=@survey.xlsx" -F "row_count=25" http://localhost:5001/api/fake-data
```

### Check Task Status
```
GET /api/status/<task_id>
```

Example:
```bash
curl http://localhost:5001/api/status/123e4567-e89b-12d3-a456-426614174000
```

## Web Interface (Streamlit)

The project includes a Streamlit web interface for easier interaction with the API:

1. Install Streamlit dependencies:
   ```bash
   pip install -r streamlit_app/requirements.txt
   ```

2. Run the Streamlit app (with the Flask API running):
   ```bash
   streamlit run streamlit_app/app.py
   ```

3. Access the web interface at http://localhost:8501

## Example with a Sample File

1. Create a sample text file:
   ```bash
   echo "The quick brown fox jumps over the lazy dog. This is a sample text for testing our synthetic dataset generator." > sample.txt
   ```

2. Upload the file and generate datasets:
   ```bash
   curl -X POST -F "file=@sample.txt" http://localhost:5001/api/upload
   ```

3. You can also try with other supported formats:
   ```bash
   # For PDF files
   curl -X POST -F "file=@document.pdf" http://localhost:5001/api/upload
   
   # For Word documents
   curl -X POST -F "file=@document.docx" http://localhost:5001/api/upload
   
   # For multiple files
   curl -X POST -F "files=@document1.pdf" -F "files=@document2.docx" http://localhost:5001/api/upload
   
   # For ZIP files containing multiple documents
   curl -X POST -F "file=@documents.zip" http://localhost:5001/api/upload
   
   # For XLSX template to generate fake data
   curl -X POST -F "file=@template.xlsx" -F "row_count=50" http://localhost:5001/api/fake-data
   ```

4. Check the output files in the `output` directory:
   ```bash
   ls -la output/
   cat output/train.jsonl
   ```

## Configuration

The application can be configured using environment variables:

- `LITELLM_PROVIDER`: LiteLLM provider (default: ollama_chat)
- `MODEL_NAME`: Model name (default: gemma3:4b-it-fp16)
- `FLASK_ENV`: Flask environment (default: development)

Copy the `.env.example` file to `.env` and modify as needed:
```bash
cp .env.example .env
```

Then edit the `.env` file to set your preferred LLM provider and model.

## Dataset Format

The generated datasets are in JSONL format with each line containing a JSON object:
```json
{"prompt": "What is the capital of France?", "completion": "Paris."}
```

For fake data generation, the output will be either CSV or XLSX files with columns matching the field names from the template.

For XLSForm templates with choices:
- Single choice fields will contain one value from the available choices
- Multiple choice fields will contain an array of values from the available choices
- Choice values use the `name` field from the XLSForm choices sheet (not the `label`)

Example CSV output for XLSForm:
```csv
name,age,gender,skills,registration_date
John Smith,32,male,[python,javascript],2024-05-15
Jane Doe,28,female,[java,csharp],2024-05-16
```

## How It Works

1. User uploads one or more files (PDF, DOCX, TXT, or ZIP)
2. The system processes files:
   - For ZIP files, extracts and processes contained documents
   - For other files, extracts text content based on file type:
     - PDF files are parsed using PyPDF2
     - Word documents are parsed using python-docx
     - Text files are read directly
3. The system calculates the number of Q/A pairs based on combined text length:
   - 1 pair per 1000 characters (minimum 3 pairs)
   - Split into train/valid/test sets (80/10/10)
4. For each text chunk, the system detects the language automatically
5. LiteLLM generates Q/A pairs using the configured provider and model in the detected language
6. Datasets are saved as JSONL files in the `output` directory

For XLSX template processing:
1. User uploads an XLSX file with column headers representing field names
2. System detects if the file is an XLSForm (has survey and choices sheets)
3. For XLSForms, parses the survey structure and choice lists
4. LiteLLM generates realistic fake data based on the field names, types, and choices
5. For select_multiple fields, data is generated as arrays using the choice name values
6. The generated data is saved as either CSV or XLSX in the `output` directory