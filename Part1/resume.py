import json
import os
import requests
import time
import random
from typing import Dict, Any, List
import sys
import fitz  # PyMuPDF

# Add the parent directory to the path so we can import config
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import config

def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Extract text from a PDF file using PyMuPDF
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        Extracted text as a string
    """
    try:
        # Open the PDF file
        pdf_document = fitz.open(pdf_path)
        text = ""
        
        # Extract text from each page
        for page_num in range(len(pdf_document)):
            page = pdf_document[page_num]
            text += page.get_text()
        
        pdf_document.close()
        return text
    except Exception as e:
        raise Exception(f"Error extracting text from PDF: {str(e)}")

def process_resume_with_llm(resume_text: str, job_description: str = None) -> Dict[str, Any]:
    """
    Process resume text with Groq's LLM to structure it into JSON format
    
    Args:
        resume_text: Plain text resume
        job_description: Optional job description to tailor skills extraction
        
    Returns:
        Structured resume data as a dictionary
    """
    # Check cache first - create hash of input text for cache key
    import hashlib
    cache_key = hashlib.md5(resume_text.encode()).hexdigest()
    cache_dir = os.path.join("temp", "cache")
    
    # Only use cache if temp directory exists
    cache_file = os.path.join(cache_dir, f"resume_{cache_key}.json")
    if os.path.exists(cache_file):
        print("Using cached resume result...")
        with open(cache_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    # Get API key from config file
    try:
        api_key = config.get_current_api_key()
    except ValueError as e:
        raise ValueError("Groq API key is not set. Please provide API keys in the GROQ_API_KEYS configuration")
    
    if not api_key:
        raise ValueError("Groq API key is not set. Please provide API keys in the GROQ_API_KEYS configuration")
    
    # System message to define the task for the LLM
    system_message = """
    You are a resume parsing assistant. Your task is to extract and structure information from a resume into a clean, structured JSON format.
    
    Important: Do NOT add any inferences or additional content. Only extract information that is explicitly present in the resume.
    
    Use the following JSON format:
    
    {
      "Name": "Full name of the candidate",
      "Contact": {
        "Email": "Email address",
        "Phone": "Phone number",
        "LinkedIn": "LinkedIn profile URL (if available)",
        "GitHub": "GitHub profile URL (if available)",
        "Location": "City, Country"
      },
      "Summary": "Professional summary or objective statement",
      "Experience": {
        "Total Years": "Total years of experience (number)",
        "Positions": [
          {
            "Title": "Job title",
            "Company": "Company name",
            "Location": "Work location",
            "Duration": "Employment duration (e.g., Jan 2020 - Present)",
            "Description": "Key responsibilities and achievements"
          }
        ]
      },
      "Education": [
        {
          "Degree": "Degree obtained",
          "Institution": "University or institution name",
          "Location": "Institution location",
          "Graduation Year": "Year of graduation",
          "GPA": "GPA if mentioned"
        }
      ],
      "Skills": [
        "List of technical and soft skills mentioned in the resume"
      ],
      "Projects": [
        {
          "Name": "Project name",
          "Description": "Project description with technologies used",
          "Duration": "Project duration if mentioned"
        }
      ],
      "Certifications": [
        "List of certifications"
      ]
    }
    
    Instructions:
    1. Only include information that is explicitly mentioned in the resume.
    2. If specific information for a field is not provided, use "Not specified" for text fields or [] for arrays.
    3. For "Total Years", calculate based on the experience timeline if possible, otherwise put 0.
    4. Extract skills from all sections of the resume, not just a dedicated skills section.
    5. Focus on commonly known and understood technologies (e.g., JavaScript, Python, React, Node.js, etc.)
    6. Avoid obscure tools like Gulp, Grunt, etc. unless explicitly mentioned.
    7. Provide your response as a valid JSON object only, with no additional text.
    """
    
    # Prepare the request
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # Prepare the request payload
    user_message = f"Resume:\n{resume_text}"
    if job_description:
        user_message += f"\n\nJob Description for context:\n{job_description}"
    
    payload = {
        "messages": [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message}
        ],
        "model": config.MODEL_NAME,
        "temperature": config.TEMPERATURE
    }
    
    # Make the API request with retry logic
    max_retries = 5
    base_delay = 2  # base delay in seconds
    
    for attempt in range(max_retries):
        try:
            print(f"Processing resume (attempt {attempt + 1}/{max_retries})...")
            
            response = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers,
                json=payload
            )
            
            # If successful, no need to retry
            if response.status_code == 200:
                break
                
            # If rate limited or quota exceeded, try next API key
            if response.status_code == 429 or "quota" in response.text.lower():
                print(f"API key quota exceeded. Trying next API key...")
                api_key = config.cycle_api_key()
                headers["Authorization"] = f"Bearer {api_key}"
                continue
                
            # For other errors, raise exception
            response.raise_for_status()
            
        except requests.exceptions.RequestException as e:
            # If last attempt, raise the exception
            if attempt == max_retries - 1:
                raise Exception(f"Error in Groq API request after {max_retries} attempts: {str(e)}")
            
            # Otherwise, wait and retry
            delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
            print(f"Request failed. Retrying in {delay:.2f} seconds...")
            time.sleep(delay)
    
    # Process the response
    try:
        result = response.json()
        
        # Extract content from the response
        content = result["choices"][0]["message"]["content"]
        
        # Extract JSON from the content
        try:
            # Try to parse the response as JSON directly
            resume_data = json.loads(content)
        except json.JSONDecodeError:
            # If direct parsing fails, try to extract JSON from markdown code blocks
            import re
            json_match = re.search(r'```(?:json)?\s*({.*?})\s*```', content, re.DOTALL)
            if json_match:
                resume_data = json.loads(json_match.group(1))
            else:
                # If all else fails, raise an error with the content for debugging
                raise Exception(f"Could not parse JSON from LLM response. Content: {content[:500]}...")
        
        # Add fraud detection
        resume_data["is_fraudulent"] = False
        resume_data["fraud_type"] = "None"
        resume_data["red_flags"] = []
        
        # Simple fraud detection based on unrealistic claims
        fraud_checks = [
            ("15+ years", "Unrealistic experience claim"),
            ("20+ years", "Unrealistic experience claim"),
            ("expert in all", "Overstated expertise claim"),
            ("master of all", "Overstated expertise claim"),
            ("perfect GPA", "Unrealistic academic claim")
        ]
        
        resume_text_lower = resume_text.lower()
        for keyword, flag in fraud_checks:
            if keyword in resume_text_lower:
                resume_data["is_fraudulent"] = True
                resume_data["fraud_type"] = "Unrealistic Claims"
                if flag not in resume_data["red_flags"]:
                    resume_data["red_flags"].append(flag)
        
        # Cache the result only if temp directory exists
        if os.path.exists("temp"):
            os.makedirs(cache_dir, exist_ok=True)
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(resume_data, f, indent=2, ensure_ascii=False)
            
        return resume_data
        
    except Exception as e:
        print(f"Error processing LLM response: {str(e)}")
        raise

def convert_resume_to_json(resume_path: str, job_path: str = None) -> Dict[str, Any]:
    """
    Convert a resume PDF file to structured JSON data
    
    Args:
        resume_path: Path to the resume PDF file
        job_path: Optional path to job description text file
        
    Returns:
        Structured resume data as a dictionary
    """
    # Extract text from PDF
    resume_text = extract_text_from_pdf(resume_path)
    
    # Read job description if provided
    job_description = None
    if job_path:
        with open(job_path, 'r', encoding='utf-8') as f:
            job_description = f.read()
    
    # Process with LLM
    structured_resume = process_resume_with_llm(resume_text, job_description)
    
    return structured_resume

def process_resume(resume_path: str, job_path: str = None, output_json_path: str = None) -> Dict[str, Any]:
    """
    Process a resume from PDF to structured JSON (deprecated - use convert_resume_to_json instead)
    
    Args:
        resume_path: Path to the resume PDF file
        job_path: Optional path to job description text file
        output_json_path: Optional path to save the JSON output
        
    Returns:
        Structured resume data as a dictionary
    """
    # Extract text from PDF
    resume_text = extract_text_from_pdf(resume_path)
    
    # Read job description if provided
    job_description = None
    if job_path:
        with open(job_path, 'r', encoding='utf-8') as f:
            job_description = f.read()
    
    # Process with LLM
    structured_resume = process_resume_with_llm(resume_text, job_description)
    
    # Save to file if output path is provided
    if output_json_path:
        os.makedirs(os.path.dirname(output_json_path) or '.', exist_ok=True)
        with open(output_json_path, 'w', encoding='utf-8') as f:
            json.dump(structured_resume, f, indent=2, ensure_ascii=False)
    
    return structured_resume