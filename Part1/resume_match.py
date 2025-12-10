import json
import os
import sys
import requests
import argparse
import time
import random
from typing import Dict, Any
import sys
import os

# Add the parent directory to the path so we can import config
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import config

def load_json_file(file_path: str) -> Dict[str, Any]:
    """
    Load JSON data from a file
    
    Args:
        file_path: Path to the JSON file
        
    Returns:
        JSON data as a dictionary
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found at: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    return data

def compare_resume_with_job(resume_data: Dict[str, Any], job_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compare a resume with a job description using the LLM
    
    Args:
        resume_data: Structured resume data
        job_data: Structured job description data
        
    Returns:
        Matching evaluation as a dictionary
    """
    # Get API key from config file
    try:
        api_key = config.get_current_api_key()
    except ValueError as e:
        raise ValueError("Groq API key is not set. Please provide API keys in the GROQ_API_KEYS configuration")
    
    if not api_key:
        raise ValueError("Groq API key is not set. Please provide API keys in the GROQ_API_KEYS configuration")
    
    # Get API key from config file
    try:
        api_key = config.get_current_api_key()
    except ValueError as e:
        raise ValueError("Groq API key is not set. Please provide API keys in the GROQ_API_KEYS configuration")
    
    if not api_key:
        raise ValueError("Groq API key is not set. Please provide API keys in the GROQ_API_KEYS configuration")
    
    # System message to define the task for the LLM
    system_message = """
    You are a fair and intelligent resume evaluation assistant. Your task is to compare a candidate's resume against a job description and provide a structured evaluation of the match.
    
    Compare the provided structured resume and job description data with the following priorities:
    - Technical Skills: High weight (look for exact matches and similar technologies)
    - Experience & Projects: High weight (must closely align with job responsibilities)
    - Soft Skills: Low weight (acknowledge them, but do not inflate the score)
    
    Be FAIR and INTELLIGENT in your evaluation:
    - Recognize that similar technologies (e.g., React experience can be relevant for Angular positions) should be considered
    - Consider the job level when evaluating experience (be more lenient for junior positions, stricter for senior positions)
    - Look for transferable skills and related experience
    - Consider the candidate's potential to learn rather than just current skills
    - Only count skills that are explicitly mentioned in the resume, not inferred ones
    - Require concrete evidence of experience with technologies mentioned in job description
    - Be skeptical of vague or generic project descriptions
    - Don't give benefit of the doubt for missing information
    - Penalize significantly for missing core technical skills
    - Focus on commonly known and understood technologies (avoid obscure tools like Gulp, Grunt, etc.)
    
    Generate the following scores:
    - match_score (0-100): Overall alignment between the resume and job description
    - skill_match_score (0-100): Based on overlap between technical skills required and those in the resume
    - experience_match_score (0-100): Based on both job experience and relevant projects
    
    Provide:
    - A few recruiter-style comments (short, relevant, and evidence-based)
    - A list of required skills that are missing or not strongly evident in the resume
    - A list of areas where the candidate is clearly overqualified for the job
    
    Your response should be a JSON object with the following structure:
    {
      "match_score": (number between 0-100),
      "skill_match_score": (number between 0-100),
      "experience_match_score": (number between 0-100),
      "comments": [
        "Comment 1",
        "Comment 2",
        "Comment 3"
      ],
      "missing_skills": ["Skill 1", "Skill 2"],
      "overqualified_in": ["Area 1", "Area 2"]
    }
    
    Notes:
    1. Consider Experience and Projects together when evaluating experience relevance and depth.
    2. Be specific and factual in your comments and evaluations.
    3. Base your evaluation only on the information provided in the resume and job description.
    4. Be honest but fair in your assessment - this is for screening candidates.
    5. Focus on commonly known and understood technologies (e.g., JavaScript, Python, React, Node.js, etc.)
    6. Avoid obscure tools like Gulp, Grunt, etc. unless explicitly mentioned.
    7. Provide your response as a valid JSON object only, with no additional text.
    """
    
    # Prepare user message with resume and job description data
    user_message = f"""
    RESUME DATA:
    {json.dumps(resume_data, indent=2)}
    
    JOB DESCRIPTION DATA:
    {json.dumps(job_data, indent=2)}
    
    Please evaluate the match between this resume and job description.
    
    Consider the following when evaluating:
    1. Job Level: {job_data.get('job_level', 'not specified')}
    2. For similar technologies (e.g., React vs Angular, Python vs Java), give partial credit
    3. For junior positions, be more lenient with experience requirements
    4. For senior positions, be stricter with technical depth requirements
    5. Look for transferable skills and related experience that could compensate for direct skill gaps
    6. Focus on commonly known and understood technologies (e.g., JavaScript, Python, React, Node.js, etc.)
    7. Avoid obscure tools like Gulp, Grunt, etc. unless explicitly mentioned.
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
            {"role": "user", "content": user_message}
        ],
        "model": config.MODEL_NAME,
        "temperature": config.TEMPERATURE
    }
    
    # Make the API request
    max_retries = 5
    base_delay = 2  # base delay in seconds
    
    for attempt in range(max_retries):
        try:
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
    
    # Parse the response
    try:
        result = response.json()
        
        # Extract content from the response
        content = result["choices"][0]["message"]["content"]
        
        # Extract JSON from the content
        try:
            # Try to parse the response as JSON directly
            match_result = json.loads(content)
            
            return match_result
            
        except json.JSONDecodeError:
            # If direct parsing fails, try to extract JSON from markdown code blocks
            import re
            json_match = re.search(r'```(?:json)?\s*({.*?})\s*```', content, re.DOTALL)
            if json_match:
                match_result = json.loads(json_match.group(1))
                
                return match_result
            else:
                # If all else fails, raise an error with the content for debugging
                raise Exception(f"Could not parse JSON from LLM response. Content: {content[:500]}...")
        
    except Exception as e:
        print(f"Error processing LLM response: {str(e)}")
        raise

def evaluate_match_from_json(resume_data: Dict[str, Any], job_data: Dict[str, Any],
                           overall_threshold: int = 70, skill_threshold: int = 65, 
                           experience_threshold: int = 60) -> Dict[str, Any]:
    """
    Evaluate the match between a resume and a job description using JSON data
    
    Args:
        resume_data: Resume data as a dictionary
        job_data: Job description data as a dictionary
        overall_threshold: Minimum required overall match score
        skill_threshold: Minimum required skill match score
        experience_threshold: Minimum required experience match score
        
    Returns:
        Matching evaluation as a dictionary
    """
    # Compare resume with job description
    evaluation = compare_resume_with_job(resume_data, job_data)
    
    # Determine pass/fail status based on thresholds and check for fraud
    evaluation = determine_pass_fail(evaluation, overall_threshold, skill_threshold, experience_threshold, resume_data)
    
    return evaluation

def evaluate_match(resume_file: str, job_file: str, output_file: str = None,
                overall_threshold: int = 70, skill_threshold: int = 65, 
                experience_threshold: int = 60) -> Dict[str, Any]:
    """
    Evaluate the match between a resume and a job description (deprecated - use evaluate_match_from_json instead)
    
    Args:
        resume_file: Path to the resume JSON file
        job_file: Path to the job description JSON file
        output_file: Optional path to save the evaluation output
        overall_threshold: Minimum required overall match score
        skill_threshold: Minimum required skill match score
        experience_threshold: Minimum required experience match score
        
    Returns:
        Matching evaluation as a dictionary
    """
    # Load resume and job description data
    resume_data = load_json_file(resume_file)
    job_data = load_json_file(job_file)
    
    # Compare resume with job description
    evaluation = compare_resume_with_job(resume_data, job_data)
    
    # Determine pass/fail status based on thresholds and check for fraud
    evaluation = determine_pass_fail(evaluation, overall_threshold, skill_threshold, experience_threshold, resume_data)
    
    # Save to file if output path is provided
    if output_file:
        os.makedirs(os.path.dirname(output_file) or '.', exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(evaluation, f, indent=2, ensure_ascii=False)
    
    return evaluation

def determine_pass_fail(evaluation: Dict[str, Any], 
                   overall_threshold: int = 70, 
                   skill_threshold: int = 65, 
                   experience_threshold: int = 60,
                   resume_data: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Determine if a candidate passes or fails based on evaluation scores and thresholds
    
    Args:
        evaluation: The evaluation dictionary with match scores
        overall_threshold: Minimum required overall match score (default: 70)
        skill_threshold: Minimum required skill match score (default: 65)
        experience_threshold: Minimum required experience match score (default: 60)
        resume_data: Original resume data for fraud detection
        
    Returns:
        Updated evaluation dictionary with pass/fail status
    """
    # Check for fraudulent resume first
    is_fraudulent = False
    fraud_type = None
    red_flags = []
    
    if resume_data:
        # Check for fraud using the new format where flags are at the root level
        is_fraudulent = resume_data.get("is_fraudulent", False)
        if is_fraudulent:
            fraud_type = resume_data.get("fraud_type", None)
            red_flags = resume_data.get("red_flags", [])
    
    # Extract scores
    overall_score = evaluation.get('match_score', 0)
    skill_score = evaluation.get('skill_match_score', 0)
    experience_score = evaluation.get('experience_match_score', 0)
    
    # Get missing skills and areas of improvement
    missing_skills = evaluation.get('missing_skills', [])
    comments = evaluation.get('comments', [])
    
    # Check minimum requirements or fraudulent resume
    failed_criteria = []
    
    if is_fraudulent:
        # Automatic fail for fraudulent resumes
        failed_criteria.append(f"Fraudulent resume detected: {fraud_type}")
        # Add red flags as additional failure criteria
        for flag in red_flags:
            failed_criteria.append(f"Red flag: {flag}")
        # Override scores for fraudulent resumes
        evaluation['match_score'] = 0
        evaluation['skill_match_score'] = 0
        evaluation['experience_match_score'] = 0
    else:
        # Normal criteria checking for non-fraudulent resumes
        if overall_score < overall_threshold:
            failed_criteria.append(f"Overall match score ({overall_score}) below minimum threshold ({overall_threshold})")
        
        if skill_score < skill_threshold:
            failed_criteria.append(f"Skill match score ({skill_score}) below minimum threshold ({skill_threshold})")
        
        if experience_score < experience_threshold:
            failed_criteria.append(f"Experience match score ({experience_score}) below minimum threshold ({experience_threshold})")
    
    # Determine pass/fail status
    is_pass = not failed_criteria and not is_fraudulent
    pass_fail = {
        "status": "PASS" if is_pass else "FAIL",
        "failed_criteria": failed_criteria
    }
    
    # Generate personalized feedback message
    if is_fraudulent:
        # Feedback for fraudulent resumes
        message = "Thank you for your application. Our evaluation system has flagged potential inconsistencies or concerns with your resume. "
        
        if red_flags:
            message += "Specifically, we noticed: "
            for flag in red_flags[:3]:  # Include at most 3 red flags in the message
                message += f"{flag}. "
        
        message += "\n\nWe recommend reviewing your resume to ensure all information is accurate, specific, and properly reflects your actual experience and skills. "
        message += "Consider providing more concrete examples of your work, being more specific about your experience level, "
        message += "and focusing on quality over quantity when listing skills and accomplishments."
    
    elif is_pass:
        # Passing candidate message
        message = "Congratulations on your application! Based on our assessment, your profile aligns well with the position requirements. "
        
        # Add personalized improvement suggestions if available
        if missing_skills:
            message += f"To further strengthen your candidacy, we recommend focusing on developing skills in: {', '.join(missing_skills[:3])}. "
        
        # Add positive reinforcement
        message += "We look forward to the next steps in the application process."
    else:
        # Failing candidate message
        message = "Thank you for your interest in this position. After careful review of your application, we've identified some areas for improvement "
        message += "that would strengthen your alignment with this role's requirements. "
        
        # Add specific improvement suggestions
        if missing_skills:
            message += f"We recommend focusing on developing the following key skills: {', '.join(missing_skills[:5])}. "
        
        # Add encouragement
        if skill_score < skill_threshold:
            message += "Acquiring additional technical expertise in these areas would significantly enhance your candidacy for similar roles in the future. "
        elif experience_score < experience_threshold:
            message += "Gaining more practical experience in these areas would significantly enhance your profile for similar positions. "
        
        message += "We appreciate your application and encourage you to continue developing your skills in these areas."
    
    # Add feedback message to the evaluation
    pass_fail["feedback_message"] = message
    
    # Add pass/fail information to evaluation
    evaluation["pass_fail"] = pass_fail
    
    return evaluation

def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description="Compare a resume with a job description and provide a matching evaluation")
    parser.add_argument("resume", help="Path to the resume JSON file")
    parser.add_argument("job", help="Path to the job description JSON file")
    parser.add_argument("-o", "--output", help="Output path for the evaluation JSON file (default: output/match_evaluation.json)",
                      default="output/match_evaluation.json")
    parser.add_argument("--overall-threshold", type=int, default=70, help="Minimum required overall match score (default: 70)")
    parser.add_argument("--skill-threshold", type=int, default=65, help="Minimum required skill match score (default: 65)")
    parser.add_argument("--experience-threshold", type=int, default=60, help="Minimum required experience match score (default: 60)")
    args = parser.parse_args()
    
    try:
        print(f"Loading resume from: {args.resume}")
        print(f"Loading job description from: {args.job}")
        
        # Evaluate the match
        evaluation = evaluate_match(
            args.resume, 
            args.job, 
            args.output,
            args.overall_threshold,
            args.skill_threshold,
            args.experience_threshold
        )
        
        print(f"Match evaluation saved to: {args.output}")
        
        # Print a summary
        print("\nMatch Evaluation Summary:")
        print(f"Overall Match Score: {evaluation.get('match_score', 'N/A')}/100")
        print(f"Skill Match Score: {evaluation.get('skill_match_score', 'N/A')}/100")
        print(f"Experience Match Score: {evaluation.get('experience_match_score', 'N/A')}/100")
        
        # Print pass/fail result
        pass_fail = evaluation.get('pass_fail', {})
        status = pass_fail.get('status', 'UNKNOWN')
        
        # Use colors for the status if supported
        if status == 'PASS':
            print(f"\n✅ RESULT: {status}")
        else:
            print(f"\n❌ RESULT: {status}")
            
            # Print failed criteria
            if 'failed_criteria' in pass_fail:
                print("\nFailed Criteria:")
                for criterion in pass_fail['failed_criteria']:
                    print(f"- {criterion}")
        
        # Print the feedback message
        if 'feedback_message' in pass_fail:
            print("\nFeedback Message:")
            print(pass_fail['feedback_message'])
        
        print("\nComments:")
        for comment in evaluation.get('comments', []):
            print(f"- {comment}")
        
        print("\nMissing Skills:")
        for skill in evaluation.get('missing_skills', []):
            print(f"- {skill}")
        
        print("\nOverqualified In:")
        for area in evaluation.get('overqualified_in', []):
            print(f"- {area}")
        
    except Exception as e:
        print(f"Error evaluating match: {str(e)}")

if __name__ == "__main__":
    main()