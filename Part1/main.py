import argparse
import os
import json
import datetime
import sys
import resume
import job_parser
import resume_match
import config

def save_resume_json(resume_data, pdf_path, output_folder="temp"):
    """
    Save resume data as JSON in the temp folder
    
    Args:
        resume_data: The structured resume data
        pdf_path: Path to the original PDF resume
        output_folder: Folder to save the JSON output
        
    Returns:
        Path to the saved JSON file
    """
    # Create output folder if it doesn't exist
    os.makedirs(output_folder, exist_ok=True)
    
    # Generate timestamp for the filename
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    resume_name = os.path.splitext(os.path.basename(pdf_path))[0]
    
    # Create JSON filename
    json_file = os.path.join(output_folder, f"{resume_name}_{timestamp}.json")
    
    # Save the JSON data
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(resume_data, f, indent=2, ensure_ascii=False)
    
    return json_file

def save_job_json(job_data, job_path, output_folder="temp"):
    """
    Save job description data as JSON in the temp folder
    
    Args:
        job_data: The structured job description data
        job_path: Path to the original job description file
        output_folder: Folder to save the JSON output
        
    Returns:
        Path to the saved JSON file
    """
    # Create output folder if it doesn't exist
    os.makedirs(output_folder, exist_ok=True)
    
    # Generate timestamp for the filename
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    job_name = os.path.splitext(os.path.basename(job_path))[0]
    
    # Create JSON filename
    json_file = os.path.join(output_folder, f"{job_name}_{timestamp}.json")
    
    # Save the JSON data
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(job_data, f, indent=2, ensure_ascii=False)
    
    return json_file

def parse_resume(args):
    """Process and structure a resume"""
    # Validate PDF path
    resume_path = args.resume
    if not os.path.exists(resume_path):
        print(f"Error: Resume file not found at {resume_path}")
        return
    
    # Validate job description path
    job_path = args.job
    if not os.path.exists(job_path):
        print(f"Warning: Job description file not found at {job_path}. Proceeding without job description.")
        job_path = None
    
    # Set up output path if provided by user
    output_path = args.output
    
    try:
        print(f"Processing resume from: {resume_path}")
        if job_path:
            print(f"Using job description from: {job_path}")
        
        # Convert resume PDF to JSON data
        structured_resume = resume.convert_resume_to_json(resume_path, job_path)
        
        # Save JSON to the output folder with timestamp
        json_file = save_resume_json(structured_resume, resume_path, args.output_dir)
        
        # Also save to the user-specified output path if provided
        if output_path:
            os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(structured_resume, f, indent=2, ensure_ascii=False)
            print(f"Saved resume to user-specified path: {output_path}")
        
        print(f"Structured data saved to: {json_file}")
        
        # Print a summary
        print("\nResume Summary:")
        print(f"Name: {structured_resume.get('Name', 'Not found')}")
        
        contact = structured_resume.get('Contact', {})
        print(f"Email: {contact.get('Email', 'Not found')}")
        
        experience = structured_resume.get('Experience', {})
        print(f"Total Experience: {experience.get('Total Years', 0)} years")
        
        skills = structured_resume.get('Skills', [])
        print(f"Skills: {', '.join(skills[:5])}{'...' if len(skills) > 5 else ''}")
        
        # Check for fraud detection
        is_fraudulent = structured_resume.get('is_fraudulent', False)
        
        if is_fraudulent:
            print("\n⚠️ FRAUD ALERT ⚠️")
            print(f"Fraud Type: {structured_resume.get('fraud_type', 'Unknown')}")
            print("\nRed Flags:")
            for flag in structured_resume.get('red_flags', []):
                print(f"- {flag}")
        
        # Print inferred skills information
        print("\nNote: The Skills section includes both explicitly mentioned skills and intelligently inferred skills")
        print("based on the resume content and the job description requirements.")
        
        return structured_resume
        
    except Exception as e:
        print(f"Error processing resume: {str(e)}")
        return None

def parse_job(args):
    """Process and structure a job description"""
    # Validate job description path
    job_path = args.job
    if not os.path.exists(job_path):
        print(f"Error: Job description file not found at {job_path}")
        return
    
    # Set up output path if provided by user
    output_path = args.output
    
    try:
        print(f"Processing job description from: {job_path}")
        
        # Convert job description to JSON data
        structured_job = job_parser.convert_job_description_to_json(job_path)
        
        # Save to output folder with timestamp
        json_file = save_job_json(structured_job, job_path, args.output_dir)
        
        # Also save to the user-specified output path if provided
        if output_path:
            os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(structured_job, f, indent=2, ensure_ascii=False)
            print(f"Saved job description to user-specified path: {output_path}")
        
        print(f"Structured data saved to: {json_file}")
        
        # Print a summary
        print("\nJob Description Summary:")
        print(f"Title: {structured_job.get('job_title', 'Not specified')}")
        
        experience = structured_job.get('experience_required', {})
        print(f"Experience Required: {experience.get('years_of_experience', 'Not specified')}")
        
        skills_required = structured_job.get('skills_required', {})
        technical_skills = skills_required.get('technical_skills', [])
        print(f"Technical Skills: {', '.join(technical_skills[:5])}{'...' if len(technical_skills) > 5 else ''}")
        
        responsibilities = structured_job.get('job_responsibilities', [])
        print(f"Responsibilities: {len(responsibilities)} items")
        
        return structured_job
        
    except Exception as e:
        print(f"Error processing job description: {str(e)}")
        return None

def match_resume_job_from_json(resume_data: dict, job_data: dict, output_file: str = None,
                              overall_threshold: int = 70, skill_threshold: int = 65, 
                              experience_threshold: int = 60):
    """Compare a resume with a job description and evaluate the match using JSON data"""
    try:
        print("Evaluating match using JSON data...")
        
        # Evaluate the match with thresholds
        evaluation = resume_match.evaluate_match_from_json(
            resume_data, 
            job_data, 
            overall_threshold,
            skill_threshold,
            experience_threshold
        )
        
        # Save to file if output path is provided
        if output_file:
            os.makedirs(os.path.dirname(output_file) or '.', exist_ok=True)
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(evaluation, f, indent=2, ensure_ascii=False)
            print(f"Match evaluation saved to: {output_file}")
        
        # Print a summary
        print("\nMatch Evaluation Summary:")
        print(f"Overall Match Score: {evaluation.get('match_score', 'N/A')}/100")
        print(f"Skill Match Score: {evaluation.get('skill_match_score', 'N/A')}/100")
        print(f"Experience Match Score: {evaluation.get('experience_match_score', 'N/A')}/100")
        
        # Print pass/fail result
        pass_fail = evaluation.get('pass_fail', {})
        status = pass_fail.get('status', 'UNKNOWN')
        
        # Use symbols for the status
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
        
        return evaluation
        
    except Exception as e:
        print(f"Error evaluating match: {str(e)}")
        return None

def match_resume_job(args):
    """Compare a resume with a job description and evaluate the match"""
    # Validate resume JSON path
    resume_file = args.resume
    if not os.path.exists(resume_file):
        print(f"Error: Resume JSON file not found at {resume_file}")
        return
    
    # Validate job description JSON path
    job_file = args.job
    if not os.path.exists(job_file):
        print(f"Error: Job description JSON file not found at {job_file}")
        return
    
    try:
        print(f"Loading resume from: {resume_file}")
        print(f"Loading job description from: {job_file}")
        
        # Evaluate the match with thresholds
        evaluation = resume_match.evaluate_match(
            resume_file, 
            job_file, 
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
        
        # Use symbols for the status
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
        
        return evaluation
        
    except Exception as e:
        print(f"Error evaluating match: {str(e)}")
        return None

def process_both(resume_path, job_path, output_dir="output"):
    """Process both resume and job description"""
    # Create args object for resume parsing
    class Args:
        pass
    
    resume_args = Args()
    resume_args.resume = resume_path
    resume_args.job = job_path
    resume_args.output = None
    resume_args.output_dir = output_dir
    
    # Create args object for job parsing
    job_args = Args()
    job_args.job = job_path
    job_args.output = None
    job_args.output_dir = output_dir
    
    # Process both
    print("\n========== PROCESSING RESUME ==========")
    resume_data = parse_resume(resume_args)
    
    print("\n========== PROCESSING JOB DESCRIPTION ==========")
    job_data = parse_job(job_args)
    
    print("\n========== PROCESSING COMPLETE ==========")
    print("Both resume and job description processed successfully")
    
    return resume_data, job_data

def process_all(resume_path, job_path, output_dir="output", 
               overall_threshold=70, skill_threshold=65, experience_threshold=60):
    """Process resume, job description, and evaluate the match"""
    # Process both resume and job description
    resume_data, job_data = process_both(resume_path, job_path, "temp")
    
    if resume_data and job_data:
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        # Save resume and job data to files for matching in the output directory
        resume_file = os.path.join(output_dir, "latest_resume.json")
        job_file = os.path.join(output_dir, "latest_job.json")
        
        with open(resume_file, 'w', encoding='utf-8') as f:
            json.dump(resume_data, f, indent=2, ensure_ascii=False)
        
        with open(job_file, 'w', encoding='utf-8') as f:
            json.dump(job_data, f, indent=2, ensure_ascii=False)
        
        # Create args object for match evaluation
        class Args:
            pass
        
        match_args = Args()
        match_args.resume = resume_file
        match_args.job = job_file
        match_args.output = os.path.join(output_dir, "match_evaluation.json")
        match_args.overall_threshold = overall_threshold
        match_args.skill_threshold = skill_threshold
        match_args.experience_threshold = experience_threshold
        
        # Evaluate the match
        print("\n========== EVALUATING MATCH ==========")
        evaluation = match_resume_job(match_args)
        
        return resume_data, job_data, evaluation
    
    return resume_data, job_data, None

def main():
    # Check for the legacy format
    if len(sys.argv) > 1 and sys.argv[1] not in ['resume', 'job', 'both', 'match', 'all']:
        # Legacy format detected, convert to new format
        parser = argparse.ArgumentParser(description="Process resumes and job descriptions using LLM (Legacy Mode)")
        parser.add_argument("-r", "--resume", help=f"Path to the resume PDF file or JSON file (default: {config.DEFAULT_RESUME_PATH})", 
                        default=config.DEFAULT_RESUME_PATH)
        parser.add_argument("-j", "--job", help=f"Path to the job description file or JSON file (default: {config.DEFAULT_JOB_DESCRIPTION_PATH})", 
                        default=config.DEFAULT_JOB_DESCRIPTION_PATH)
        parser.add_argument("-o", "--output", help="Output path for the JSON file (default: output in same directory with same name)")
        parser.add_argument("-d", "--output-dir", help="Output directory for the intermediate JSON files ('temp') or final match files ('output')", default="temp")
        parser.add_argument("-m", "--mode", help="Processing mode: resume, job, both, match, or all (default: resume)", 
                           choices=['resume', 'job', 'both', 'match', 'all'], default='resume')
        parser.add_argument("--overall-threshold", type=int, default=70, help="Minimum required overall match score (default: 70)")
        parser.add_argument("--skill-threshold", type=int, default=65, help="Minimum required skill match score (default: 65)")
        parser.add_argument("--experience-threshold", type=int, default=60, help="Minimum required experience match score (default: 60)")
        
        args = parser.parse_args()
        
        if args.mode == 'resume':
            parse_resume(args)
        elif args.mode == 'job':
            parse_job(args)
        elif args.mode == 'both':
            process_both(args.resume, args.job, args.output_dir)
        elif args.mode == 'match':
            # Create args object for match evaluation
            class MatchArgs:
                pass
            
            match_args = MatchArgs()
            match_args.resume = args.resume
            match_args.job = args.job
            # Always use 'output' directory for match results
            match_args.output = os.path.join("output", "match_evaluation.json") if not args.output else args.output
            
            match_resume_job(match_args)
        elif args.mode == 'all':
            # For 'all' mode, always use 'output' directory for final results
            process_all(
                args.resume, 
                args.job, 
                "output",
                args.overall_threshold,
                args.skill_threshold,
                args.experience_threshold
            )
            
    else:
        # New format with subcommands
        parser = argparse.ArgumentParser(description="Process resumes and job descriptions using LLM")
        subparsers = parser.add_subparsers(dest="command", help="Command to execute")
        
        # Resume parsing command
        resume_parser = subparsers.add_parser("resume", help="Parse and structure a resume")
        resume_parser.add_argument("-r", "--resume", help=f"Path to the resume PDF file (default: {config.DEFAULT_RESUME_PATH})", 
                            default=config.DEFAULT_RESUME_PATH)
        resume_parser.add_argument("-j", "--job", help=f"Path to the job description file (default: {config.DEFAULT_JOB_DESCRIPTION_PATH})", 
                            default=config.DEFAULT_JOB_DESCRIPTION_PATH)
        resume_parser.add_argument("-o", "--output", help="Output path for the JSON file (default: output in same directory with same name)")
        resume_parser.add_argument("-d", "--output-dir", help="Output directory for the intermediate JSON files (default: temp)", default="temp")
        
        # Job description parsing command
        job_parser = subparsers.add_parser("job", help="Parse and structure a job description")
        job_parser.add_argument("-j", "--job", help=f"Path to the job description file (default: {config.DEFAULT_JOB_DESCRIPTION_PATH})", 
                            default=config.DEFAULT_JOB_DESCRIPTION_PATH)
        job_parser.add_argument("-o", "--output", help="Output path for the JSON file (default: output in same directory with same name)")
        job_parser.add_argument("-d", "--output-dir", help="Output directory for the intermediate JSON files (default: temp)", default="temp")
        
        # Process both resume and job description command
        both_parser = subparsers.add_parser("both", help="Parse and structure both a resume and a job description")
        both_parser.add_argument("-r", "--resume", help=f"Path to the resume PDF file (default: {config.DEFAULT_RESUME_PATH})", 
                            default=config.DEFAULT_RESUME_PATH)
        both_parser.add_argument("-j", "--job", help=f"Path to the job description file (default: {config.DEFAULT_JOB_DESCRIPTION_PATH})", 
                            default=config.DEFAULT_JOB_DESCRIPTION_PATH)
        both_parser.add_argument("-d", "--output-dir", help="Output directory for the intermediate JSON files (default: temp)", default="temp")
        
        # Match resume and job description command
        match_parser = subparsers.add_parser("match", help="Compare a resume with a job description and evaluate the match")
        match_parser.add_argument("resume", help="Path to the resume JSON file")
        match_parser.add_argument("job", help="Path to the job description JSON file")
        match_parser.add_argument("-o", "--output", help="Output path for the evaluation JSON file (default: output/match_evaluation.json)",
                              default="output/match_evaluation.json")
        match_parser.add_argument("--overall-threshold", type=int, default=70, help="Minimum required overall match score (default: 70)")
        match_parser.add_argument("--skill-threshold", type=int, default=65, help="Minimum required skill match score (default: 65)")
        match_parser.add_argument("--experience-threshold", type=int, default=60, help="Minimum required experience match score (default: 60)")
        
        # Process everything (resume, job, and match) command
        all_parser = subparsers.add_parser("all", help="Process a resume and job description, then evaluate the match")
        all_parser.add_argument("-r", "--resume", help=f"Path to the resume PDF file (default: {config.DEFAULT_RESUME_PATH})", 
                            default=config.DEFAULT_RESUME_PATH)
        all_parser.add_argument("-j", "--job", help=f"Path to the job description file (default: {config.DEFAULT_JOB_DESCRIPTION_PATH})", 
                            default=config.DEFAULT_JOB_DESCRIPTION_PATH)
        all_parser.add_argument("-d", "--output-dir", help="Output directory for final match files (intermediate files go to temp folder) (default: output)", default="output")
        all_parser.add_argument("--overall-threshold", type=int, default=70, help="Minimum required overall match score (default: 70)")
        all_parser.add_argument("--skill-threshold", type=int, default=65, help="Minimum required skill match score (default: 65)")
        all_parser.add_argument("--experience-threshold", type=int, default=60, help="Minimum required experience match score (default: 60)")
        
        # Parse arguments
        args = parser.parse_args()
        
        # Default to resume parsing if no command is provided
        if not args.command:
            print("No command specified. Defaulting to resume parsing.")
            args.command = "resume"
        
        # Execute the appropriate function based on the command
        if args.command == "resume":
            parse_resume(args)
        elif args.command == "job":
            parse_job(args)
        elif args.command == "both":
            process_both(args.resume, args.job, args.output_dir)
        elif args.command == "match":
            match_resume_job(args)
        elif args.command == "all":
            process_all(
                args.resume, 
                args.job, 
                args.output_dir,
                args.overall_threshold,
                args.skill_threshold,
                args.experience_threshold
            )

if __name__ == "__main__":
    main() 