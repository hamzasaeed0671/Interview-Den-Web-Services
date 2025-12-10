# ./main.py

import argparse
import os
import sys
import json
import datetime
from typing import Dict, Any, List, Optional 

# ===================================================
# 1. PATH SETUP – ensures modules load
# ===================================================

BASE_DIR = os.path.dirname(__file__)
PART1_DIR = os.path.join(BASE_DIR, "Part1")
PART2_DIR = os.path.join(BASE_DIR, "Part2")
PART3_DIR = os.path.join(BASE_DIR, "Part3") 

if PART1_DIR not in sys.path:
    sys.path.append(PART1_DIR)
if PART2_DIR not in sys.path:
    sys.path.append(PART2_DIR)
if PART3_DIR not in sys.path:
    sys.path.append(PART3_DIR)

# ===================================================
# 2. CORE IMPORTS (with corrected error handling)
# ===================================================

# Part 3 Imports 
try:
    from Part3.interviewer import start_interview_logic, chat_interview_logic, InterviewerBot 
    from Part3.grader import evaluate_candidate 
except ImportError as e:
    print(f"[WARNING] Could not import Part3 modules. Interview pipeline will fail: {e}")
    def start_interview_logic(*args, **kwargs): return None, None 
    def chat_interview_logic(*args, **kwargs): return "Error: Part3 not loaded.", True, None
    def evaluate_candidate(*args, **kwargs): raise NotImplementedError("Part3 modules not found.")
    class InterviewerBot: pass 

# Part 1/2 Imports 
try:
    from resume import convert_resume_to_json
    from job_parser import convert_job_description_to_json
    from resume_match import evaluate_match_from_json
    from test_generator import JobTestGenerator
except ImportError as e:
    print(f"[WARNING] Could not import Part1/Part2 modules. API logic may fail: {e}")
    def convert_resume_to_json(*args, **kwargs): return {"error": "Module not found"}
    def convert_job_description_to_json(*args, **kwargs): return {"error": "Module not found"}
    def evaluate_match_from_json(*args, **kwargs): return {"error": "Module not found"}
    class JobTestGenerator:
        def generate_quiz_from_json(self, *args, **kwargs): return "dummy_quiz_id"


# ===================================================
# 3. TOP-LEVEL VARIABLES/HELPERS
# ===================================================

TRANSCRIPT_FILE = "interview_transcript.json"

def load_data(file_path):
    """Helper to safely load JSON data"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return json.dumps(data, indent=4), data 
    except FileNotFoundError:
        return None, None
    except json.JSONDecodeError:
        print(f"[ERROR] Failed to parse JSON in: {file_path}")
        return None, None


# ===================================================
# 4. EXISTING API LOGIC FUNCTIONS (Unchanged)
# ===================================================
def parse_resume_logic(resume_path, job_path=None):
    if not os.path.exists(resume_path):
        raise FileNotFoundError(f"Resume not found: {resume_path}")
    if job_path and not os.path.exists(job_path):
        print(f"⚠️ Job path not found: {job_path}, skipping job context.")
        job_path = None
    data = convert_resume_to_json(resume_path, job_path)
    return data

def parse_job_logic(job_path):
    if not os.path.exists(job_path):
        raise FileNotFoundError(f"Job file not found: {job_path}")
    data = convert_job_description_to_json(job_path)
    return data

def match_logic(resume_json_path, job_json_path, overall=70, skill=65, exp=60):
    if not os.path.exists(resume_json_path):
        raise FileNotFoundError(f"Resume JSON not found: {resume_json_path}")
    if not os.path.exists(job_json_path):
        raise FileNotFoundError(f"Job JSON not found: {job_json_path}")
    with open(resume_json_path, encoding="utf-8") as r, open(job_json_path, encoding="utf-8") as j:
        resume_data, job_data = json.load(r), json.load(j)
    result = evaluate_match_from_json(resume_data, job_data, overall, skill, exp)
    return result

def quiz_logic(job_json_path, questions=5):
    if not os.path.exists(job_json_path):
        raise FileNotFoundError(f"Job JSON not found: {job_json_path}")
    with open(job_json_path, encoding="utf-8") as f:
        job_data = json.load(f)
    generator = JobTestGenerator()
    quiz_id = generator.generate_quiz_from_json(job_data, questions)
    
    quiz_dir = os.path.join(BASE_DIR, "Part2", "QuizData")
    quiz_files = [f for f in os.listdir(quiz_dir) if f.endswith(f"{quiz_id}.json")]
    
    if not quiz_files:
         quiz_files = [f for f in os.listdir(quiz_dir) if f.startswith(f"quiz_{job_data.get('Title', 'job')}") and f.endswith(".json")]
    
    if not quiz_files:
        raise FileNotFoundError(f"Quiz file not found after generation for ID: {quiz_id}")

    quiz_file = os.path.join(quiz_dir, quiz_files[0])

    with open(quiz_file, encoding="utf-8") as f:
        quiz_data = json.load(f)
    return quiz_data


# ===================================================
# 5. INTERVIEW PIPELINE FUNCTION (Deprecated for chat mode)
# ===================================================

def pipeline_main():
    """The original synchronous pipeline (now only for CLI compatibility)."""
    print("[INFO] The 'run-pipeline' command is DEPRECATED. Use 'python test.py' to run the interactive pipeline via the API.")
    return


# ===================================================
# 6. CLI WRAPPER 
# ===================================================

def main():
    parser = argparse.ArgumentParser(description="Resume & Job Matching CLI / Interview Pipeline")
    sub = parser.add_subparsers(dest="cmd")

    p0 = sub.add_parser("run-pipeline", help="Run the full AI Interview and Grader pipeline.")
    
    p1 = sub.add_parser("parse-resume", help="Parse a resume into structured JSON")
    p1.add_argument("--resume", required=True, help="Path to resume PDF")
    p1.add_argument("--job", help="Optional job description for context")

    p2 = sub.add_parser("parse-job", help="Parse a job description text file")
    p2.add_argument("--job", required=True, help="Path to job description file")

    p3 = sub.add_parser("match", help="Match a parsed resume and job JSON")
    p3.add_argument("--resume-json", required=True, help="Path to parsed resume JSON")
    p3.add_argument("--job-json", required=True, help="Path to parsed job JSON")

    p4 = sub.add_parser("generate-quiz", help="Generate quiz from job JSON")
    p4.add_argument("--job-json", required=True)
    p4.add_argument("--questions", type=int, default=5)

    args = parser.parse_args()

    try:
        if args.cmd == "run-pipeline":
            pipeline_main()
        elif args.cmd == "parse-resume":
            print(json.dumps(parse_resume_logic(args.resume, args.job), indent=2))
        elif args.cmd == "parse-job":
            print(json.dumps(parse_job_logic(args.job), indent=2))
        elif args.cmd == "match":
            print(json.dumps(match_logic(args.resume_json, args.job_json), indent=2))
        elif args.cmd == "generate-quiz":
            print(json.dumps(quiz_logic(args.job_json, args.questions), indent=2))
        else:
            parser.print_help()

    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    main()