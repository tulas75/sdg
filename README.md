# Synthetic Dataset Generator (SDG)

A Flask-based API service that generates synthetic Q/A datasets from user-uploaded files using LiteLLM.

## Features

- Upload multiple files of different types (PDF, DOCX, TXT, ZIP) through a REST API
- Generate synthetic question-answer pairs using LLMs via LiteLLM
- Automatically calculate the number of Q/A pairs based on combined text length
- Output datasets in JSONL format (train.jsonl, valid.jsonl, test.jsonl)
- Support for multiple file formats:
  - PDF (.pdf)
  - Word Documents (.docx)
  - Plain Text (.txt)
  - ZIP archives containing any of the above

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

## API Endpoints

### Health Check
```
GET /api/health
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
curl -X POST -F "file=@document.pdf" http://localhost:5000/api/upload

# Multiple files
curl -X POST -F "files=@document1.pdf" -F "files=@document2.docx" http://localhost:5000/api/upload

# ZIP file containing multiple documents
curl -X POST -F "file=@documents.zip" http://localhost:5000/api/upload
```

## Configuration

The application can be configured using environment variables:

- `LITELLM_PROVIDER`: LiteLLM provider (default: ollama_chat)
- `MODEL_NAME`: Model name (default: gemma3:4b-it-fp16)
- `FLASK_ENV`: Flask environment (default: development)

## Dataset Format

The generated datasets are in JSONL format with each line containing a JSON object:
```json
{"prompt": "What is the capital of France?", "completion": "Paris."}
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
4. LiteLLM generates Q/A pairs using the configured provider and model
5. Datasets are saved as JSONL files in the `output` directory