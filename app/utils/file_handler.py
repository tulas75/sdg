"""Utility functions for extracting text from different file types."""
import os
import zipfile
from typing import Optional, List
import PyPDF2
from docx import Document


def extract_text_from_pdf(file_path: str) -> str:
    """
    Extract text from a PDF file.
    
    Args:
        file_path: Path to the PDF file
        
    Returns:
        Extracted text as a string
    """
    text = ""
    try:
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
    except Exception as e:
        raise Exception(f"Error extracting text from PDF: {str(e)}")
    
    return text


def extract_text_from_docx(file_path: str) -> str:
    """
    Extract text from a Word document (.docx).
    
    Args:
        file_path: Path to the Word document
        
    Returns:
        Extracted text as a string
    """
    try:
        doc = Document(file_path)
        text = ""
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        return text
    except Exception as e:
        raise Exception(f"Error extracting text from Word document: {str(e)}")


def extract_text_from_txt(file_path: str) -> str:
    """
    Extract text from a plain text file.
    
    Args:
        file_path: Path to the text file
        
    Returns:
        Extracted text as a string
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    except Exception as e:
        raise Exception(f"Error reading text file: {str(e)}")


def extract_text_from_zip(file_path: str) -> str:
    """
    Extract text from a ZIP file containing documents.
    
    Args:
        file_path: Path to the ZIP file
        
    Returns:
        Combined extracted text from all supported documents in the ZIP
    """
    combined_text = ""
    try:
        with zipfile.ZipFile(file_path, 'r') as zip_ref:
            # Get list of file names in the ZIP
            file_list = zip_ref.namelist()
            
            for file_name in file_list:
                # Skip directories
                if file_name.endswith('/'):
                    continue
                    
                # Process supported file types
                _, extension = os.path.splitext(file_name)
                extension = extension.lower()
                
                if extension in ['.txt', '.pdf', '.docx']:
                    # Extract the file to a temporary location
                    with zip_ref.open(file_name) as file:
                        # For text files, we can read directly
                        if extension == '.txt':
                            content = file.read().decode('utf-8', errors='ignore')
                            combined_text += f"\n\n--- Content from {file_name} ---\n\n{content}"
                        # For binary files, we need to save temporarily
                        else:
                            # Create a temporary file path
                            temp_dir = os.path.join(os.path.dirname(file_path), 'temp')
                            if not os.path.exists(temp_dir):
                                os.makedirs(temp_dir)
                                
                            temp_file_path = os.path.join(temp_dir, os.path.basename(file_name))
                            with open(temp_file_path, 'wb') as temp_file:
                                temp_file.write(file.read())
                            
                            # Extract text using appropriate handler
                            try:
                                if extension == '.pdf':
                                    content = extract_text_from_pdf(temp_file_path)
                                    combined_text += f"\n\n--- Content from {file_name} ---\n\n{content}"
                                elif extension == '.docx':
                                    content = extract_text_from_docx(temp_file_path)
                                    combined_text += f"\n\n--- Content from {file_name} ---\n\n{content}"
                            except Exception as e:
                                # Continue with other files even if one fails
                                print(f"Warning: Could not extract text from {file_name} in ZIP: {str(e)}")
                            finally:
                                # Clean up temporary file
                                if os.path.exists(temp_file_path):
                                    os.remove(temp_file_path)
    except Exception as e:
        raise Exception(f"Error extracting text from ZIP file: {str(e)}")
    
    return combined_text


def extract_text_from_file(file_path: str) -> str:
    """
    Extract text from a file based on its extension.
    
    Args:
        file_path: Path to the file
        
    Returns:
        Extracted text as a string
        
    Raises:
        Exception: If file type is not supported or extraction fails
    """
    _, extension = os.path.splitext(file_path)
    extension = extension.lower()
    
    if extension == '.pdf':
        return extract_text_from_pdf(file_path)
    elif extension == '.docx':
        return extract_text_from_docx(file_path)
    elif extension == '.txt' or extension == '':
        return extract_text_from_txt(file_path)
    elif extension == '.zip':
        return extract_text_from_zip(file_path)
    elif extension == '.xlsx':
        # XLSX files are handled differently for fake data generation, 
        # so we return a special marker
        return "[XLSX_FILE_FOR_FAKE_DATA_GENERATION]"
    else:
        raise Exception(f"Unsupported file type: {extension}")