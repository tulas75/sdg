# Synthetic Dataset Generator API - Usage Example

## Starting the Server

```bash
python -m app.main
```

The server will start on `http://localhost:5000`.

## API Endpoints

### Health Check

```bash
curl http://localhost:5000/api/health
```

### Upload File and Generate Dataset

```bash
# Single file
curl -X POST -F "file=@/path/to/your/file.pdf" http://localhost:5000/api/upload

# Multiple files
curl -X POST -F "files=@/path/to/your/file1.pdf" -F "files=@/path/to/your/file2.docx" http://localhost:5000/api/upload

# ZIP file containing multiple documents
curl -X POST -F "file=@/path/to/your/documents.zip" http://localhost:5000/api/upload
```

The API supports the following file types:
- PDF (.pdf)
- Word Documents (.docx)
- Plain Text (.txt)
- ZIP archives (.zip) containing any of the above

## Example with a Sample File

1. Create a sample text file:
   ```bash
   echo "The quick brown fox jumps over the lazy dog. This is a sample text for testing our synthetic dataset generator." > sample.txt
   ```

2. Upload the file and generate datasets:
   ```bash
   curl -X POST -F "file=@sample.txt" http://localhost:5000/api/upload
   ```

3. You can also try with other supported formats:
   ```bash
   # For PDF files
   curl -X POST -F "file=@document.pdf" http://localhost:5000/api/upload
   
   # For Word documents
   curl -X POST -F "file=@document.docx" http://localhost:5000/api/upload
   
   # For multiple files
   curl -X POST -F "files=@document1.pdf" -F "files=@document2.docx" http://localhost:5000/api/upload
   
   # For ZIP files containing multiple documents
   curl -X POST -F "file=@documents.zip" http://localhost:5000/api/upload
   ```

4. Check the output files in the `output` directory:
   ```bash
   ls -la output/
   cat output/train.jsonl
   ```

## Environment Configuration

Copy the `.env.example` file to `.env` and modify as needed:
```bash
cp .env.example .env
```

Then edit the `.env` file to set your preferred LLM provider and model.