#!/usr/bin/env python3
"""
Test script to demonstrate the new JSON-based functions for resume processing, 
job description processing, and matching.
"""

import json
import os
import resume
import job_parser
import resume_match

def main():
    # Test converting a resume PDF to JSON
    print("=== Testing Resume to JSON Conversion ===")
    resume_pdf_path = "data/Waleed.pdf"  # Using the default resume
    job_description_path = "data/JobDescription1.txt"  # Using the first job description
    
    resume_json_data = None
    if os.path.exists(resume_pdf_path):
        try:
            # Convert resume to JSON
            resume_json_data = resume.convert_resume_to_json(resume_pdf_path, job_description_path)
            print("Resume successfully converted to JSON!")
            print(f"Resume name: {resume_json_data.get('Name', 'Not found')}")
            print(f"Total experience: {resume_json_data.get('Experience', {}).get('Total Years', 0)} years")
            print(f"Skills count: {len(resume_json_data.get('Skills', []))}")
        except Exception as e:
            print(f"Error converting resume: {e}")
    else:
        print(f"Resume file not found: {resume_pdf_path}")
    
    print("\n" + "="*50 + "\n")
    
    # Test converting a job description to JSON
    print("=== Testing Job Description to JSON Conversion ===")
    job_json_data = None
    if os.path.exists(job_description_path):
        try:
            # Convert job description to JSON
            job_json_data = job_parser.convert_job_description_to_json(job_description_path)
            print("Job description successfully converted to JSON!")
            print(f"Job title: {job_json_data.get('job_title', 'Not specified')}")
            technical_skills = job_json_data.get('skills_required', {}).get('technical_skills', [])
            print(f"Required technical skills: {', '.join(technical_skills)}")
            print(f"Responsibilities count: {len(job_json_data.get('job_responsibilities', []))}")
        except Exception as e:
            print(f"Error converting job description: {e}")
    else:
        print(f"Job description file not found: {job_description_path}")
    
    print("\n" + "="*50 + "\n")
    
    # Output the JSON data to files
    if resume_json_data:
        with open('resume_output.json', 'w', encoding='utf-8') as f:
            json.dump(resume_json_data, f, indent=2, ensure_ascii=False)
        print("Resume JSON data saved to resume_output.json")
    
    if job_json_data:
        with open('job_output.json', 'w', encoding='utf-8') as f:
            json.dump(job_json_data, f, indent=2, ensure_ascii=False)
        print("Job JSON data saved to job_output.json")
    
    # Uncommenting the matching part as requested
    print("=== Testing Resume-Job Matching with JSON Data ===")
    try:
        if resume_json_data and job_json_data:
            # Match using JSON data directly
            evaluation = resume_match.evaluate_match_from_json(resume_json_data, job_json_data)
            
            print("Resume-job matching completed!")
            print(f"Overall match score: {evaluation.get('match_score', 'N/A')}/100")
            print(f"Skill match score: {evaluation.get('skill_match_score', 'N/A')}/100")
            print(f"Experience match score: {evaluation.get('experience_match_score', 'N/A')}/100")
            
            # Show pass/fail status
            pass_fail = evaluation.get('pass_fail', {})
            status = pass_fail.get('status', 'UNKNOWN')
            print(f"Status: {status}")
            
            if status == 'FAIL':
                print("Failed criteria:")
                for criterion in pass_fail.get('failed_criteria', []):
                    print(f"  - {criterion}")
            
            # Save evaluation to file
            with open('match_evaluation.json', 'w', encoding='utf-8') as f:
                json.dump(evaluation, f, indent=2, ensure_ascii=False)
            print("Match evaluation saved to match_evaluation.json")
        else:
            print("Required JSON data not available for matching test")
    except Exception as e:
        print(f"Error in matching: {e}")

if __name__ == "__main__":
    main()