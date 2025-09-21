# Test script for the Streamlit app

import requests
import os

# Test the health endpoint
def test_api_health():
    try:
        response = requests.get("http://127.0.0.1:5000/api/health")
        print(f"API Health Check: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error connecting to API: {e}")
        return False

# Test file upload
def test_file_upload():
    # Create a simple test file
    test_content = "This is a test document for the Synthetic Dataset Generator. It contains some sample text to generate question-answer pairs."
    
    with open("test.txt", "w") as f:
        f.write(test_content)
    
    try:
        with open("test.txt", "rb") as f:
            files = {"files": ("test.txt", f, "text/plain")}
            response = requests.post("http://127.0.0.1:5000/api/upload", files=files)
        
        print(f"Upload Response Status: {response.status_code}")
        if response.status_code == 200:
            print(f"Upload Response: {response.json()}")
        else:
            print(f"Upload Error: {response.text}")
            
    except Exception as e:
        print(f"Error uploading file: {e}")
    finally:
        # Clean up test file
        if os.path.exists("test.txt"):
            os.remove("test.txt")

if __name__ == "__main__":
    print("Testing Synthetic Dataset Generator API")
    print("=" * 40)
    
    # Test health check
    print("1. Testing API Health:")
    if test_api_health():
        print("✓ API is healthy\n")
        
        # Test file upload
        print("2. Testing File Upload:")
        test_file_upload()
    else:
        print("✗ API is not accessible")