"""Utility functions for processing XLSX files and generating fake data."""
import json
import os
import random
from typing import Dict, List, Any, Tuple

import pandas as pd
import litellm


def extract_fields_from_xlsx(file_path: str) -> Dict[str, Any]:
    """
    Extract field information from an XLSX file, supporting XLSForm structure.
    
    Args:
        file_path: Path to the XLSX file
        
    Returns:
        Dictionary containing fields information and choices if XLSForm structure is detected
    """
    try:
        # Read the Excel file and check what sheets are available
        excel_file = pd.ExcelFile(file_path)
        sheet_names = excel_file.sheet_names
        
        # Check if this is an XLSForm (has survey and choices sheets)
        is_xlsform = 'survey' in sheet_names and 'choices' in sheet_names
        
        if not is_xlsform:
            # Treat as simple data template
            df = pd.read_excel(file_path, sheet_name=0, nrows=5)  # Read first 5 rows to get sample data
            
            fields = []
            for column in df.columns:
                # Get the first non-null value as sample
                sample_value = df[column].dropna().iloc[0] if not df[column].dropna().empty else ""
                
                fields.append({
                    'name': str(column),
                    'sample_value': str(sample_value) if pd.notna(sample_value) else ""
                })
                
            return {
                'fields': fields,
                'is_xlsform': False
            }
        
        # Parse XLSForm structure
        survey_df = pd.read_excel(file_path, sheet_name='survey')
        choices_df = pd.read_excel(file_path, sheet_name='choices')
        
        # Extract fields from survey sheet
        fields = []
        choice_lists = {}
        
        # Group choices by list name
        if 'list_name' in choices_df.columns:
            for list_name in choices_df['list_name'].unique():
                if pd.notna(list_name):  # Only process non-NaN list names
                    choice_lists[list_name] = choices_df[choices_df['list_name'] == list_name]['name'].dropna().tolist()
        
        # Process survey questions
        for _, row in survey_df.iterrows():
            # Skip structural elements like 'begin group' and 'begin repeat'
            row_type = str(row.get('type', '')).strip().lower()
            if row_type in ['begin_group', 'end_group', 'begin_repeat', 'end_repeat', 'note']:
                continue
                
            if 'type' not in row or 'name' not in row or pd.isna(row['type']) or pd.isna(row['name']):
                continue
                
            field_info = {
                'name': str(row['name']),
                'type': str(row['type']),
                'label': str(row.get('label', row['name'])) if pd.notna(row.get('label', row['name'])) else str(row['name'])
            }
            
            # Check if this is a select question with choices
            if 'select' in str(row['type']) and 'choice_filter' not in row:
                # Extract list name from type (e.g., "select_one countries" -> "countries")
                parts = str(row['type']).split()
                if len(parts) > 1:
                    list_name = parts[-1]
                    if list_name in choice_lists:
                        field_info['choices'] = choice_lists[list_name]
                        
            fields.append(field_info)
            
        return {
            'fields': fields,
            'is_xlsform': True
        }
    except Exception as e:
        raise Exception(f"Error extracting fields from XLSX file: {str(e)}")


def generate_fake_data_with_llm(fields_info: Dict[str, Any], row_count: int, provider: str, model: str) -> List[Dict[str, Any]]:
    """
    Generate fake data for the given fields using an LLM.
    
    Args:
        fields_info: Dictionary containing fields information and XLSForm flag
        row_count: Number of rows to generate
        provider: LiteLLM provider
        model: Model name
        
    Returns:
        List of dictionaries representing rows of fake data
    """
    fields = fields_info['fields']
    is_xlsform = fields_info['is_xlsform']
    
    if is_xlsform:
        # Create a prompt for XLSForm structure
        field_descriptions = "\n".join([
            f"- {field['name']} ({field['type']}): {field.get('label', field['name'])}" + 
            (f" [Choices: {', '.join(str(choice) for choice in field['choices'])}]" if 'choices' in field else "")
            for field in fields
        ])
    else:
        # Create a prompt for simple template
        field_descriptions = "\n".join([f"- {field['name']}: Sample value '{field['sample_value']}'" for field in fields])
    
    prompt = f"""
    Based on the following field descriptions from an Excel template, generate {row_count} rows of realistic fake data.
    
    Field descriptions:
    {field_descriptions}
    
    Please generate exactly {row_count} rows of data in JSON format.
    
    Requirements:
    - Generate exactly {row_count} JSON objects in an array
    - Each object should have all the field names as keys
    - Generate realistic, diverse values appropriate for each field type:
    """
    
    if is_xlsform:
        prompt += """
      * For text fields: Generate realistic text responses
      * For integer/decimal fields: Generate appropriate numbers within realistic ranges
      * For date fields: Generate valid dates in YYYY-MM-DD format
      * For select_one fields: Choose one value from the provided choices
      * For select_multiple fields: Choose multiple values from the provided choices (as a JSON array)
      * For name fields: Generate realistic full names
      * For email fields: Generate valid email addresses with realistic names and common domains
      * For age fields: Generate realistic ages between 18-80
      * For city fields: Generate real city names from around the world
      * For salary fields: Generate realistic salary numbers (30000-200000)
      * For address fields: Generate realistic street addresses
      * For phone fields: Generate realistic phone numbers in format +1-XXX-XXX-XXXX
    """
    else:
        prompt += """
      * For name fields: Generate realistic full names
      * For email fields: Generate valid email addresses with realistic names and common domains
      * For age fields: Generate realistic ages between 18-80
      * For city fields: Generate real city names from around the world
      * For salary fields: Generate realistic salary numbers (30000-200000)
      * For numeric fields: Generate appropriate numbers within realistic ranges
      * For date fields: Generate valid dates in YYYY-MM-DD format
      * For address fields: Generate realistic street addresses
      * For phone fields: Generate realistic phone numbers in format +1-XXX-XXX-XXXX
    """
    
    prompt += """
    - Ensure data is varied and not repetitive
    - All generated values should be realistic and make sense in context
    - For select questions, only use values from the provided choices
    - For select_multiple questions, return the choices as a JSON array
    
    Return ONLY a JSON array containing {row_count} objects. No other text or formatting.
    """
    
    if is_xlsform:
        prompt += """
    Example format for XLSForm:
    [
      {
        "name": "John Smith",
        "age": 32,
        "city": "New York",
        "country": "USA",  // select_one from choices
        "skills": ["Python", "JavaScript"]  // select_multiple from choices as array
      }
    ]
    """
    else:
        prompt += """
    Example format for simple template:
    [
      {
        "name": "John Smith",
        "email": "john.smith@gmail.com",
        "age": 32,
        "city": "New York",
        "salary": 75000
      }
    ]
    """
    
    try:
        # Call LiteLLM
        response = litellm.completion(
            model=f"{provider}/{model}",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=4000
        )
        
        # Extract the response content
        content = response['choices'][0]['message']['content']
        
        # Try to parse the response as JSON
        content = content.strip()
        
        # Remove markdown code block markers if present
        if content.startswith("```json"):
            content = content[7:]  # Remove ```json
        elif content.startswith("```"):
            content = content[3:]  # Remove ```
        if content.endswith("```"):
            content = content[:-3]  # Remove ```
            
        # Parse as JSON
        fake_data = json.loads(content)
        
        # Ensure we have the right number of rows
        if len(fake_data) < row_count:
            # Add more fallback rows if we don't have enough
            additional_rows = generate_fallback_fake_data(fields_info, row_count - len(fake_data))
            fake_data.extend(additional_rows)
        elif len(fake_data) > row_count:
            # Trim if we have too many
            fake_data = fake_data[:row_count]
            
        return fake_data
    except json.JSONDecodeError as e:
        # If JSON parsing fails, log the error and content for debugging
        print(f"Error parsing JSON from LLM response: {e}")
        print(f"LLM response content: {content}")
        # Fallback: Generate simple fake data if LLM fails
        print("Using fallback data generation")
        return generate_fallback_fake_data(fields_info, row_count)
    except Exception as e:
        # Fallback: Generate simple fake data if LLM fails
        print(f"Error generating fake data with LLM: {e}")
        return generate_fallback_fake_data(fields_info, row_count)


def _generate_xlsform_field_value(field, first_names, last_names, domains, cities):
    """Generate a field value for XLSForm fields."""
    field_name = str(field['name']) if pd.notna(field['name']) else ""
    field_type = str(field.get('type', 'text')) if pd.notna(field.get('type', 'text')) else 'text'
    
    # Handle select questions with choices
    if 'choices' in field:
        if 'select_multiple' in field_type:
            # Select multiple choices (1-3)
            num_choices = random.randint(1, min(3, len(field['choices'])))
            selected = random.sample(field['choices'], num_choices)
            return selected  # Return as list
        else:
            # Select one choice
            return random.choice(field['choices'])
    
    # Handle other field types with a mapping approach
    field_mappings = {
        'name': lambda: f"{random.choice(first_names)} {random.choice(last_names)}",
        'email': lambda: f"{random.choice(first_names).lower()}.{random.choice(last_names).lower()}{random.randint(1, 99)}@{random.choice(domains)}",
        'phone': lambda: f"+1-{random.randint(100, 999)}-{random.randint(100, 999)}-{random.randint(1000, 9999)}",
        'address': lambda: f"{random.randint(100, 9999)} {random.choice(['Main St', 'First Ave', 'Elm St', 'Oak St', 'Pine St', 'Maple Ave', 'Cedar St', 'Park Ave', 'Washington St', 'Lake St'])}",
        'city': lambda: random.choice(cities),
        'date': lambda: f"2024-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}",
        'age': lambda: random.randint(18, 80),
        'salary': lambda: random.randint(30000, 120000),
        'integer': lambda: random.randint(1, 1000),
        'number': lambda: random.randint(1, 1000),
        'decimal': lambda: round(random.uniform(1, 1000), 2)
    }
    
    # Check for matching field types
    for key, func in field_mappings.items():
        if key in field_name.lower() or field_type == key:
            return func()
    
    # Default to text field
    return f"Sample {field_name} {random.randint(1, 1000)}"


def generate_fallback_fake_data(fields_info: Dict[str, Any], row_count: int) -> List[Dict[str, Any]]:
    """
    Generate fallback fake data when LLM fails.
    
    Args:
        fields_info: Dictionary containing fields information and XLSForm flag
        row_count: Number of rows to generate
        
    Returns:
        List of dictionaries representing rows of fake data
    """
    fields = fields_info['fields']
    is_xlsform = fields_info['is_xlsform']
    
    fake_data = []
    
    # Sample data for different field types
    first_names = ["John", "Jane", "Michael", "Sarah", "David", "Emily", "Christopher", "Jessica", "Matthew", "Ashley",
                   "Daniel", "Lisa", "James", "Maria", "Robert", "Michelle", "William", "Jennifer", "Thomas", "Elizabeth"]
    last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez",
                  "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin"]
    domains = ["gmail.com", "yahoo.com", "hotmail.com", "outlook.com"]
    cities = ["New York", "Los Angeles", "Chicago", "Houston", "Phoenix", "Philadelphia", "San Antonio", "San Diego", 
              "Dallas", "San Jose", "Austin", "Jacksonville", "Fort Worth", "Columbus", "San Francisco", "Charlotte",
              "Indianapolis", "Seattle", "Denver", "Washington"]
    
    for _ in range(row_count):
        row = {}
        for field in fields:
            if is_xlsform:
                row[field['name']] = _generate_xlsform_field_value(field, first_names, last_names, domains, cities)
            else:
                row[field['name']] = _generate_simple_field_value(field, first_names, last_names, domains, cities)
                
        fake_data.append(row)
        
    return fake_data


def _generate_simple_field_value(field, first_names, last_names, domains, cities):
    """Generate a field value for simple template fields."""
    field_name = str(field['name']).lower() if pd.notna(field['name']) else ""
    sample_value = str(field['sample_value']) if pd.notna(field['sample_value']) else ""
    
    # Handle name fields specifically for better fake data
    if 'name' in field_name or 'nome' in field_name or 'cognome' in field_name:
        if 'cognome' in field_name or 'surname' in field_name or 'lastname' in field_name:
            return random.choice(last_names)
        elif 'nome' in field_name or 'firstname' in field_name or 'given' in field_name:
            return random.choice(first_names)
        else:
            # General name field
            return f"{random.choice(first_names)} {random.choice(last_names)}"
    
    # Handle numeric fields
    if sample_value.replace('.', '', 1).isdigit():
        # Numeric field
        if '.' in sample_value:
            # For decimal numbers
            return round(random.uniform(1, 1000), 2)
        else:
            # For integers
            return random.randint(1, 1000)
    
    # Handle other field types with a mapping approach
    field_mappings = {
        'email': lambda: f"{random.choice(first_names).lower()}.{random.choice(last_names).lower()}{random.randint(1, 99)}@{random.choice(domains)}",
        'phone': lambda: f"+1-{random.randint(100, 999)}-{random.randint(100, 999)}-{random.randint(1000, 9999)}",
        'address': lambda: f"{random.randint(100, 9999)} {random.choice(['Main St', 'First Ave', 'Elm St', 'Oak St', 'Pine St', 'Maple Ave', 'Cedar St', 'Park Ave', 'Washington St', 'Lake St'])}",
        'city': lambda: random.choice(cities),
        'date': lambda: f"2024-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}",
        'age': lambda: random.randint(18, 80),
        'salary': lambda: random.randint(30000, 120000)
    }
    
    # Check for matching field types
    for key, func in field_mappings.items():
        if key in field_name:
            return func()
    
    # Default to text field
    return f"Sample {field['name']} {random.randint(1, 1000)}"



def save_fake_data_to_file(fake_data: List[Dict[str, Any]], file_path: str, file_format: str = "csv") -> str:
    """
    Save fake data to a file in the specified format.
    
    Args:
        fake_data: List of dictionaries representing rows of data
        file_path: Path to save the file
        file_format: Format to save the file in ('csv' or 'xlsx')
        
    Returns:
        Path to the saved file
    """
    try:
        # Convert lists to JSON strings for CSV format
        if file_format.lower() == "csv":
            processed_data = []
            for row in fake_data:
                processed_row = {}
                for key, value in row.items():
                    # Convert lists to bracket format without quotes for CSV
                    if isinstance(value, list):
                        # Format as [item1,item2,item3] without quotes for simple identifiers
                        list_str = "[" + ",".join(str(item) for item in value) + "]"
                        processed_row[key] = list_str
                    else:
                        processed_row[key] = value
                processed_data.append(processed_row)
            
            # Save as CSV
            df = pd.DataFrame(processed_data)
            df.to_csv(file_path, index=False)
        elif file_format.lower() == "xlsx":
            # For XLSX, we can preserve the list structure
            df = pd.DataFrame(fake_data)
            df.to_excel(file_path, index=False)
        else:
            raise ValueError(f"Unsupported file format: {file_format}")
            
        return file_path
    except Exception as e:
        raise Exception(f"Error saving fake data to {file_format} file: {str(e)}")
