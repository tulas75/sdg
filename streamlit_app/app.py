import os
from io import BytesIO
import time
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
This app allows you to generate synthetic datasets using AI.
You can either generate Q/A datasets from documents or fake data from XLSForm templates.
""")

# API configuration
API_URL = os.getenv("API_URL", "http://127.0.0.1:5000/api")
HEALTH_ENDPOINT = f"{API_URL}/health"
UPLOAD_ENDPOINT = f"{API_URL}/upload"
FAKE_DATA_ENDPOINT = f"{API_URL}/fake-data"

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
        with st.spinner("Uploading files..."):
            # Upload files and get task ID
            response = requests.post(UPLOAD_ENDPOINT, files=files_to_upload, timeout=30)
            
        if response.status_code == 200:
            result = response.json()
            task_id = result.get('task_id')
            if not task_id:
                st.error("Failed to get task ID from the server.")
                return None
            
            # Poll for task status
            status_url = f"{API_URL}/status/{task_id}"
            return poll_task_status(status_url)
        else:
            st.error(f"Upload Error: {response.status_code} - {response.text}")
            return None
    except requests.exceptions.ConnectionError:
        st.error("Failed to connect to the API. Please make sure the Flask API is running.")
        return None
    except Exception as e:
        st.error(f"Error uploading files: {str(e)}")
        return None


# Function to generate fake data from XLSForm
def generate_fake_data(file, row_count, output_format):
    if not file:
        st.warning("Please select an XLSForm file to upload.")
        return None
    
    # Prepare files and data for upload
    files = {"file": (file.name, file, file.type)}
    data = {"row_count": str(row_count), "format": output_format}
    
    try:
        with st.spinner("Generating fake data..."):
            # Upload file and get task ID
            response = requests.post(FAKE_DATA_ENDPOINT, files=files, data=data, timeout=30)
            
        if response.status_code == 200:
            result = response.json()
            task_id = result.get('task_id')
            if not task_id:
                st.error("Failed to get task ID from the server.")
                return None
            
            # Poll for task status
            status_url = f"{API_URL}/status/{task_id}"
            return poll_task_status(status_url)
        else:
            st.error(f"Upload Error: {response.status_code} - {response.text}")
            return None
    except requests.exceptions.ConnectionError:
        st.error("Failed to connect to the API. Please make sure the Flask API is running.")
        return None
    except Exception as e:
        st.error(f"Error generating fake data: {str(e)}")
        return None


# Function to poll task status
def poll_task_status(status_url):
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        while True:
            response = requests.get(status_url, timeout=30)
            if response.status_code == 200:
                status_data = response.json()
                status = status_data.get('status', 'unknown')
                
                if status == 'processing':
                    status_text.text("Processing... This may take several minutes depending on the file size and number of rows.")
                    # We don't have a progress percentage, so we'll just keep the progress bar at 50%
                    progress_bar.progress(50)
                    time.sleep(2)  # Poll every 2 seconds
                elif status == 'completed':
                    progress_bar.progress(100)
                    status_text.text("Processing complete!")
                    return status_data.get('result')
                elif status == 'failed':
                    progress_bar.progress(100)
                    status_text.text("Processing failed!")
                    st.error(f"Processing failed: {status_data.get('message', 'Unknown error')}")
                    return None
                elif status == 'not_found':
                    st.error("Task not found on the server.")
                    return None
                else:
                    status_text.text(f"Status: {status}")
                    time.sleep(2)  # Poll every 2 seconds
            else:
                st.error(f"Error checking status: {response.status_code} - {response.text}")
                return None
    except requests.exceptions.ConnectionError:
        st.error("Lost connection to the API while checking status.")
        return None
    except Exception as e:
        st.error(f"Error while checking status: {str(e)}")
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
        with open(file_path, 'rb') as f:
            content = f.read()
        # Determine mime type based on file extension
        if file_path.endswith('.csv'):
            mime_type = 'text/csv'
        elif file_path.endswith('.xlsx'):
            mime_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        else:
            mime_type = 'application/json'
            
        st.download_button(
            label=label,
            data=content,
            file_name=os.path.basename(file_path),
            mime=mime_type
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
    st.code(f"Fake Data: {FAKE_DATA_ENDPOINT}")

# Create tabs for different functionalities
tab1, tab2 = st.tabs(["📚 Generate Q/A Datasets", "📊 Generate Fake Data"])

# Tab 1: Generate Q/A Datasets from documents
with tab1:
    st.header("Upload Files")
    st.markdown("Generate question-answer datasets from your documents (PDF, DOCX, TXT, or ZIP)")
    
    # File uploader
    uploaded_files = st.file_uploader(
        "Choose files to process",
        type=["pdf", "docx", "txt", "zip"],
        accept_multiple_files=True,
        key="qa_files"
    )
    
    # Process button
    if st.button("Generate Datasets", type="primary", key="generate_qa"):
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
                    st.metric("Total Files Processed", str(len(uploaded_files)))
                
                with col2:
                    st.metric("Q/A Pairs Generated", str(result.get("qa_count", "N/A")))
                
                with col3:
                    st.metric("Output Files", "3")  # train, valid, test
                
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

# Tab 2: Generate Fake Data from XLSForm
with tab2:
    st.header("Upload XLSForm Template")
    st.markdown("Generate fake data from your XLSForm template with customizable row count")
    
    # File uploader for XLSForm
    xlsform_file = st.file_uploader(
        "Choose XLSForm file to process",
        type=["xlsx"],
        key="fake_data_file"
    )
    
    # Parameters
    col1, col2 = st.columns(2)
    with col1:
        row_count = st.number_input("Number of rows", min_value=1, max_value=10000, value=100, step=10)
    with col2:
        output_format = st.selectbox("Output format", ["csv", "xlsx"], index=0)
    
    # Generate button
    if st.button("Generate Fake Data", type="primary", key="generate_fake"):
        if not xlsform_file:
            st.warning("Please upload an XLSForm file before generating fake data.")
        else:
            # Generate fake data
            result = generate_fake_data(xlsform_file, row_count, output_format)
            
            if result:
                st.success("Fake data generated successfully!")
                
                # Display results
                st.subheader("Results")
                col1, col2 = st.columns(2)
                
                with col1:
                    st.metric("Rows Generated", str(result.get("row_count", "N/A")))
                
                with col2:
                    st.metric("Output Format", result.get("format", "N/A").upper())
                
                # Display output file
                st.subheader("Generated File")
                output_file = result.get('output_file')
                
                if output_file:
                    with st.expander("Generated Data Preview", expanded=False):
                        if output_file.endswith('.csv'):
                            # Show CSV preview
                            try:
                                with open(output_file, 'r', encoding='utf-8') as f:
                                    lines = f.readlines()[:10]  # Show first 10 lines
                                    st.text(''.join(lines))
                            except Exception as e:
                                st.error(f"Error reading CSV file: {str(e)}")
                        else:
                            st.info("Preview not available for XLSX files. Please download to view.")
                    
                    # Download button
                    st.subheader("Download Generated Data")
                    create_download_link(output_file, f"Download Fake Data ({output_format.upper()})")

# Information section
st.markdown("---")
st.header("ℹ️ How It Works")

# Create tabs for different how-it-works sections
how_tab1, how_tab2 = st.tabs(["📚 Q/A Dataset Generation", "📊 Fake Data Generation"])

with how_tab1:
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

with how_tab2:
    st.markdown("""
    1. **Upload XLSForm**: Upload your XLSForm template with survey structure
    2. **Processing**: The system parses your XLSForm structure and choices
    3. **AI Generation**: Using an LLM, the system generates realistic fake data
    4. **Data Creation**: Data is generated respecting field types and choice constraints
    5. **Download**: Download the generated data in CSV or XLSX format
    """)
    
    st.header("📋 XLSForm Support")
    st.markdown("""
    - **Survey Sheet**: Field definitions with types and labels
    - **Choices Sheet**: Choice lists for select questions
    - **Field Types**: Text, integer, decimal, date, select_one, select_multiple
    - **Output Formats**: CSV or XLSX with proper data formatting
    """)
