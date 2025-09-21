#!/usr/bin/env python3
"""
Script to run both the Flask API and Streamlit app together.
"""

import subprocess
import sys
import time
import requests
import threading

def check_api_health():
    """Check if the API is healthy."""
    try:
        response = requests.get("http://127.0.0.1:5000/api/health", timeout=5)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False

def start_api():
    """Start the Flask API server."""
    print("Starting Flask API server...")
    api_process = subprocess.Popen(
        [sys.executable, "-m", "app.main"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    return api_process

def start_streamlit():
    """Start the Streamlit app."""
    print("Starting Streamlit app...")
    streamlit_process = subprocess.Popen(
        ["streamlit", "run", "streamlit_app/app.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    return streamlit_process

def main():
    """Main function to start both services."""
    print("Starting Synthetic Dataset Generator with Streamlit interface...")
    
    # Start the API
    api_process = start_api()
    
    # Wait a moment for the API to start
    time.sleep(3)
    
    # Check if API is healthy
    if check_api_health():
        print("✓ Flask API is running")
    else:
        print("✗ Failed to start Flask API")
        api_process.terminate()
        return
    
    # Start Streamlit
    streamlit_process = start_streamlit()
    
    print("\nServices started successfully!")
    print("Flask API: http://127.0.0.1:5000")
    print("Streamlit App: http://localhost:8501")
    print("\nPress Ctrl+C to stop both services.")
    
    try:
        # Wait for both processes
        while True:
            if api_process.poll() is not None:
                print("Flask API process has stopped.")
                streamlit_process.terminate()
                break
            if streamlit_process.poll() is not None:
                print("Streamlit process has stopped.")
                api_process.terminate()
                break
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down services...")
        api_process.terminate()
        streamlit_process.terminate()
        print("Services stopped.")

if __name__ == "__main__":
    main()