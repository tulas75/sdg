# Synthetic Dataset Generator - Streamlit App

A Streamlit web interface for the Synthetic Dataset Generator API that allows users to easily upload documents and generate synthetic question-answer datasets.

## Features

- User-friendly web interface for uploading documents
- Support for multiple file types (PDF, DOCX, TXT, ZIP)
- Real-time API status monitoring
- Preview of generated datasets
- Direct download of train/validation/test datasets
- Responsive design that works on desktop and mobile

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Start the Flask API server (if not already running):
   ```bash
   python -m app.main
   ```

3. Run the Streamlit app:
   ```bash
   streamlit run streamlit_app/app.py
   ```

## Usage

1. Open your browser to the Streamlit app URL (typically http://localhost:8501)
2. Check that the API status shows as "running" in the sidebar
3. Upload one or more documents using the file uploader
4. Click "Generate Datasets" to process your files
5. Preview the generated datasets in the expandable sections
6. Download the train/validation/test datasets using the download buttons

## Supported File Types

- PDF (.pdf)
- Word Documents (.docx)
- Plain Text (.txt)
- ZIP archives (.zip) containing any of the above

## API Configuration

The Streamlit app connects to the Flask API at `http://localhost:5000/api` by default. You can change this by setting the `API_URL` environment variable:

```bash
API_URL=http://your-api-url streamlit run streamlit_app/app.py
```