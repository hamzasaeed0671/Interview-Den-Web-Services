import json
import os
import requests
import time
import random
from typing import Dict, Any
import sys
import os
import re

# Add the parent directory to the path so we can import config
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import config

def determine_job_level(job_title: str, experience_required: str) -> str:
    """
    Determine job level based on job title and experience requirements
    
    Args:
        job_title: The job title
        experience_required: The experience requirements text
        
    Returns:
        Job level as a string
    """
    # Combine title and experience for analysis
    combined_text = f"{job_title} {experience_required}".lower()
    
    # Check for internship keywords
    internship_keywords = ["internship", "intern", "entry level", "internship program"]
    for keyword in internship_keywords:
        if keyword in combined_text:
            return "Internship"
    
    # Check for associate keywords
    associate_keywords = ["associate", "assistant", "trainee"]
    for keyword in associate_keywords:
        if keyword in combined_text:
            return "Associate"
    
    # Check for junior keywords
    junior_keywords = ["junior", "jr", "1-2 years", "1 to 2 years", "entry", "beginner"]
    for keyword in junior_keywords:
        if keyword in combined_text:
            return "Junior"
    
    # Check for mid-level keywords
    mid_level_keywords = ["mid-level", "mid level", "3-5 years", "3 to 5 years", "intermediate"]
    for keyword in mid_level_keywords:
        if keyword in combined_text:
            return "Junior"  # Mid-level is still considered Junior in our hierarchy
    
    # Check for senior keywords
    senior_keywords = ["senior", "sr", "lead", "6+ years", "6 years", "7 years", "8 years", "9 years", "10 years"]
    for keyword in senior_keywords:
        if keyword in combined_text:
            return "Senior"
    
    # Check for expert keywords
    expert_keywords = ["expert", "principal", "staff", "architect", "fellow", "10+ years"]
    for keyword in expert_keywords:
        if keyword in combined_text:
            return "Expert"
    
    # Default to junior if it's in the title
    if "junior" in job_title.lower():
        return "Junior"
    
    # Default to not specified
    return "Not specified"

def process_job_description_with_llm(job_description_text: str) -> Dict[str, Any]:
    """
    Process job description text with Groq's LLM to structure it into JSON format
    
    Args:
        job_description_text: Plain text job description
        
    Returns:
        Structured job description data as a dictionary
    """
    # Check cache first - create hash of input text for cache key
    import hashlib
    cache_key = hashlib.md5(job_description_text.encode()).hexdigest()
    cache_dir = os.path.join("temp", "cache")
    
    # Only use cache if temp directory exists
    cache_file = os.path.join(cache_dir, f"job_{cache_key}.json")
    if os.path.exists(cache_file):
        print("Using cached job description result...")
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
    You are a job description parsing assistant. Your task is to extract and structure information from a job description into a clean, structured JSON format.
    
    Important: Do NOT add any inferences or additional content. Only extract information that is explicitly present in the job description.
    
    Focus on commonly known and understood skills and technologies. Avoid obscure tools like Gulp, Grunt, etc. unless they are explicitly mentioned in the job description.
    
    Use the following JSON format:
    
    {
      "job_title": "The title of the job (e.g., Data Scientist, Software Developer)",
      "role_description": "Summary of tasks and responsibilities expected for the role",
      "experience_required": {
        "years_of_experience": "Number of years of experience required",
        "level": "The difficulty level of the job (Internship, Associate, Junior, Senior, or Expert)"
      },
      "skills_required": {
        "technical_skills": [
          "List of programming languages, frameworks, and commonly understood tools required"
        ],
        "soft_skills": [
          "List of soft skills required"
        ]
      },
      "preferred_skills": [
        "List of optional skills that can enhance your chances"
      ],
      "job_responsibilities": [
        "Task 1",
        "Task 2",
        "Task 3"
      ]
    }
    
    Instructions:
    1. Only include information that is explicitly mentioned in the job description.
    2. If specific information for a field is not provided, use "Not specified" for text fields or [] for arrays.
    3. For "years_of_experience", extract the number if mentioned, otherwise put "Not specified".
    4. For "level", determine the difficulty level based on the job title and experience requirements using these categories:
       - Internship: Entry-level positions, internships
       - Associate: Assistant positions, trainee roles
       - Junior: 1-3 years of experience, beginner roles
       - Senior: 5+ years of experience, lead roles
       - Expert: 10+ years of experience, principal/staff roles
    5. Separate technical skills (programming languages, frameworks, commonly understood tools) from soft skills (communication, teamwork).
    6. Differentiate between required skills and preferred/desired skills.
    7. Break down responsibilities into individual items in the list.
    8. Focus on commonly known and understood technologies (e.g., JavaScript, Python, React, Node.js, etc.)
    9. Avoid obscure tools like Gulp, Grunt, etc. unless explicitly mentioned.
    10. Provide your response as a valid JSON object only, with no additional text.
    """
    
    # Prepare the request
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # Prepare the request payload
    payload = {
        "messages": [
            {"role": "system", "content": system_message},
            {"role": "user", "content": job_description_text}
        ],
        "model": config.MODEL_NAME,
        "temperature": config.TEMPERATURE
    }
    
    # Make the API request with retry logic
    max_retries = 5
    base_delay = 2  # base delay in seconds
    
    for attempt in range(max_retries):
        try:
            print(f"Processing job description (attempt {attempt + 1}/{max_retries})...")
            
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
            job_data = json.loads(content)
        except json.JSONDecodeError:
            # If direct parsing fails, try to extract JSON from markdown code blocks
            import re
            json_match = re.search(r'```(?:json)?\s*({.*?})\s*```', content, re.DOTALL)
            if json_match:
                job_data = json.loads(json_match.group(1))
            else:
                # If all else fails, raise an error with the content for debugging
                raise Exception(f"Could not parse JSON from LLM response. Content: {content[:500]}...")
        
        # Add the determined job level if not already present
        if "experience_required" not in job_data:
            job_data["experience_required"] = {}
        
        if "level" not in job_data["experience_required"]:
            level = determine_job_level(
                job_data.get("job_title", ""), 
                str(job_data.get("experience_required", {}).get("years_of_experience", ""))
            )
            job_data["experience_required"]["level"] = level
        
        # Cache the result only if temp directory exists
        if os.path.exists("temp"):
            os.makedirs(cache_dir, exist_ok=True)
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(job_data, f, indent=2, ensure_ascii=False)
            
        return job_data
        
    except Exception as e:
        print(f"Error processing LLM response: {str(e)}")
        raise

def convert_job_description_to_json(job_file_path: str) -> Dict[str, Any]:
    """
    Convert a job description text file to structured JSON data
    
    Args:
        job_file_path: Path to the job description text file
        
    Returns:
        Structured job description data as a dictionary
    """
    # Read job description
    job_description_text = read_job_description(job_file_path)
    
    # Process with LLM
    structured_job = process_job_description_with_llm(job_description_text)
    
    return structured_job

def process_job_description(job_file_path: str, output_json_path: str = None) -> Dict[str, Any]:
    """
    Process a job description from text file to structured JSON (deprecated - use convert_job_description_to_json instead)
    
    Args:
        job_file_path: Path to the job description text file
        output_json_path: Optional path to save the JSON output
        
    Returns:
        Structured job description data as a dictionary
    """
    # Read job description
    job_description_text = read_job_description(job_file_path)
    
    # Process with LLM
    structured_job = process_job_description_with_llm(job_description_text)
    
    # Save to file if output path is provided
    if output_json_path:
        os.makedirs(os.path.dirname(output_json_path) or '.', exist_ok=True)
        with open(output_json_path, 'w', encoding='utf-8') as f:
            json.dump(structured_job, f, indent=2, ensure_ascii=False)
    
    return structured_job

def read_job_description(file_path: str) -> str:
    """
    Read job description from a text file
    
    Args:
        file_path: Path to the job description text file
        
    Returns:
        Job description text as a string
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Job description file not found at: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        text = f.read()
    
    return text