import os
from io import BytesIO
import streamlit as st
import requests

# Streamlit app configuration
st.set_page_config(
    page_title="Synthetic Dataset Generator",
    page_icon="🔄",
    layout="wide"
)

# App title and description
st.title("🔄 Synthetic Dataset Generator")
st.markdown("""
This app allows you to generate synthetic question-answer datasets from your documents using AI.
Upload one or more files (PDF, DOCX, TXT, or ZIP) and get train/validation/test datasets in JSONL format.
""")

# API configuration
API_URL = os.getenv("API_URL", "http://127.0.0.1:5000/api")
HEALTH_ENDPOINT = f"{API_URL}/health"
UPLOAD_ENDPOINT = f"{API_URL}/upload"

# Check API health
@st.cache_data(ttl=60)
def check_api_health():
    try:
        response = requests.get(HEALTH_ENDPOINT, timeout=5)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False

# Function to upload files and generate datasets
def upload_files_and_generate(files):
    if not files:
        st.warning("Please select at least one file to upload.")
        return None
    
    # Prepare files for upload
    files_to_upload = []
    for file in files:
        files_to_upload.append(("files", (file.name, file, file.type)))
    
    try:
        with st.spinner("Processing files and generating datasets... This may take several minutes depending on the file size and number of files."):
            # For large files, we remove the timeout to avoid premature termination
            # This is intentional as processing thousands of pages can take a long time
            response = requests.post(UPLOAD_ENDPOINT, files=files_to_upload)  # pylint: disable=missing-timeout
            
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"API Error: {response.status_code} - {response.text}")
            return None
    except requests.exceptions.Timeout:
        st.error("Request timed out. The file processing may take longer than expected. Please try again with smaller files or wait a bit longer.")
        return None
    except requests.exceptions.ConnectionError:
        st.error("Failed to connect to the API. Please make sure the Flask API is running.")
        return None
    except Exception as e:
        st.error(f"Error connecting to the API: {str(e)}")
        return None

# Function to read file content
def read_file_content(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        st.error(f"Error reading file {file_path}: {str(e)}")
        return None

# Function to create download link for files
def create_download_link(file_path, label):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        st.download_button(
            label=label,
            data=content,
            file_name=os.path.basename(file_path),
            mime='application/json'
        )
    except Exception as e:
        st.error(f"Error preparing download for {file_path}: {str(e)}")

# Sidebar for API status
with st.sidebar:
    st.header("⚙️ API Status")
    if check_api_health():
        st.success("API is running")
    else:
        st.error("API is not accessible")
        st.info("Make sure the Flask API is running on localhost:5000")
    
    st.markdown("---")
    st.markdown("**API Endpoints:**")
    st.code(f"Health: {HEALTH_ENDPOINT}")
    st.code(f"Upload: {UPLOAD_ENDPOINT}")

# Main content
st.header("Upload Files")

# File uploader
uploaded_files = st.file_uploader(
    "Choose files to process",
    type=["pdf", "docx", "txt", "zip"],
    accept_multiple_files=True
)

# Process button
if st.button("Generate Datasets", type="primary"):
    if not uploaded_files:
        st.warning("Please upload at least one file before generating datasets.")
    else:
        # Upload files and generate datasets
        result = upload_files_and_generate(uploaded_files)
        
        if result:
            st.success("Datasets generated successfully!")
            
            # Display results
            st.subheader("Results")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Total Files Processed", result.get("file_count", "N/A"))
            
            with col2:
                st.metric("Q/A Pairs Generated", result.get("qa_count", "N/A"))
            
            with col3:
                st.metric("Output Files", 3)  # train, valid, test
            
            # Display file paths
            st.subheader("Generated Files")
            
            train_file = result.get('train_file')
            valid_file = result.get('valid_file')
            test_file = result.get('test_file')
            
            if train_file:
                with st.expander("Train Dataset Preview", expanded=False):
                    train_content = read_file_content(train_file)
                    if train_content:
                        # Show first few lines
                        lines = train_content.split('\n')[:5]
                        st.code('\n'.join(lines), language='json')
            
            if valid_file:
                with st.expander("Validation Dataset Preview", expanded=False):
                    valid_content = read_file_content(valid_file)
                    if valid_content:
                        # Show first few lines
                        lines = valid_content.split('\n')[:5]
                        st.code('\n'.join(lines), language='json')
            
            if test_file:
                with st.expander("Test Dataset Preview", expanded=False):
                    test_content = read_file_content(test_file)
                    if test_content:
                        # Show first few lines
                        lines = test_content.split('\n')[:5]
                        st.code('\n'.join(lines), language='json')
            
            # Download buttons
            st.subheader("Download Datasets")
            
            # Create download buttons for each file
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if train_file:
                    create_download_link(train_file, "Download Train Dataset")
            
            with col2:
                if valid_file:
                    create_download_link(valid_file, "Download Validation Dataset")
            
            with col3:
                if test_file:
                    create_download_link(test_file, "Download Test Dataset")

# Information section
st.markdown("---")
st.header("ℹ️ How It Works")
st.markdown("""
1. **Upload Files**: Upload one or more documents (PDF, DOCX, TXT, or ZIP)
2. **Processing**: The system extracts text from your documents
3. **AI Generation**: Using an LLM, the system generates question-answer pairs
4. **Dataset Creation**: Datasets are split into train/validation/test sets (80/10/10)
5. **Download**: Download the generated datasets in JSONL format
""")

st.header("📁 Supported File Types")
st.markdown("""
- **PDF (.pdf)**: Portable Document Format files
- **Word Documents (.docx)**: Microsoft Word documents
- **Text Files (.txt)**: Plain text files
- **ZIP Archives (.zip)**: Compressed files containing any of the above
""")