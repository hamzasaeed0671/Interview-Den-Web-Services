# --- Test.py (Complete Final Client Logic - with separate transcript save) ---

import requests
import json
import os
from datetime import datetime
from typing import Dict, Any, Optional

# Assuming the API is running locally
API_URL = "http://127.0.0.1:8000"

# Existing paths (Part1)
RESUME_PATH = "Part1/data/Waleed.pdf"
JOB_PATH = "Part1/data/JobDescription2.txt"

# New paths for the pipeline test (Part3) - NOTE: These files must exist and be valid JSON
JD_JSON_PATH = "Part3/Data/JD.json"
RESUME_JSON_PATH = "Part3/Data/resume.json"

OUT_DIR = "TestData"
os.makedirs(OUT_DIR, exist_ok=True)


def save_json(data: Dict[str, Any], name: str) -> str:
    """Saves JSON data to a file in OUT_DIR with a timestamp."""
    path = os.path.join(OUT_DIR, f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return path


def load_json_file(file_path: str) -> Optional[str]:
    """Helper to safely load JSON content from a file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        print(f"[ERROR] Required file not found: {file_path}")
        return None
    except Exception as e:
        print(f"[ERROR] Failed to read {file_path}: {e}")
        return None

# ===================================================
# PHASE 1: EXISTING ENDPOINT TEST FUNCTIONS (REQUIRED)
# ===================================================

def parse_resume():
    print("=== Parsing Resume ===")
    if not os.path.exists(RESUME_PATH):
        print(f"[SKIP] Resume file not found at {RESUME_PATH}")
        return None
    try:
        with open(RESUME_PATH, "rb") as f:
            res = requests.post(f"{API_URL}/parse/resume", files={"file": ("resume.pdf", f)})
        res.raise_for_status()
        data = res.json()
        path = save_json(data, "resume_output")
        print(f"✓ Resume parsed → {path}")
        return data
    except requests.exceptions.RequestException as e:
        print(f"✗ Resume parsing failed: {e}")
        return None


def parse_job():
    print("\n=== Parsing Job ===")
    if not os.path.exists(JOB_PATH):
        print(f"[SKIP] Job file not found at {JOB_PATH}")
        return None
    try:
        with open(JOB_PATH, "rb") as f:
            res = requests.post(f"{API_URL}/parse/job", files={"file": ("job.txt", f)})
        res.raise_for_status()
        data = res.json()
        path = save_json(data, "job_output")
        print(f"✓ Job parsed → {path}")
        return data
    except requests.exceptions.RequestException as e:
        print(f"✗ Job parsing failed: {e}")
        return None


def match(resume_data, job_data):
    print("\n=== Matching Resume & Job ===")
    if not (resume_data and job_data):
        print("[SKIP] Matching skipped due to missing data.")
        return None
    try:
        rjson = json.dumps(resume_data)
        jjson = json.dumps(job_data)
        files = {
            "resume_json": ("resume.json", rjson, "application/json"),
            "job_json": ("job.json", jjson, "application/json"),
        }
        res = requests.post(f"{API_URL}/match", files=files)
        res.raise_for_status()
        data = res.json()
        path = save_json(data, "match_output")
        print(f"✓ Matching done → {path}")
        return data
    except requests.exceptions.RequestException as e:
        print(f"✗ Matching failed: {e}")
        return None


def quiz(job_data):
    print("\n=== Generating Quiz ===")
    if not job_data:
        print("[SKIP] Quiz generation skipped due to missing job data.")
        return None
    try:
        jjson = json.dumps(job_data)
        files = {"job_json": ("job.json", jjson, "application/json")}
        # Send 'questions' as form data
        res = requests.post(f"{API_URL}/quiz", files=files, data={"questions": 5})
        res.raise_for_status()
        data = res.json()
        path = save_json(data, "quiz_output")
        print(f"✓ Quiz generated → {path}")
        return data
    except requests.exceptions.RequestException as e:
        print(f"✗ Quiz generation failed: {e}")
        return None

# ===================================================
# PHASE 2: INTERACTIVE PIPELINE TEST FUNCTION
# ===================================================

def run_pipeline_test_interactive():
    print("\n\n=== Running Full Interview Pipeline (INTERACTIVE Chat) ===")
    
    jd_content_str = load_json_file(JD_JSON_PATH)
    resume_content_str = load_json_file(RESUME_JSON_PATH)
    
    if not jd_content_str or not resume_content_str:
        print("✗ Pipeline test skipped. One or both JSON files are missing or invalid.")
        return None

    # 1. START the Interview
    start_payload = {
        "job_description_json": jd_content_str,
        "resume_json": resume_content_str
    }
    
    session_id = None
    final_transcript = None
    evaluation_result = None

    try:
        print(f"Connecting to API at {API_URL}")
        res = requests.post(f"{API_URL}/interview/start", json=start_payload)
        res.raise_for_status() 
        start_data = res.json()
        
        session_id = start_data["session_id"]
        
        print(f"\n🎉 Session Started (ID: {session_id})")
        print("-" * 60)
        
        print(f"InterviewerBot: {start_data['message']}")
        is_finished = start_data["is_finished"]
        
        # 2. CHAT Loop
        while not is_finished:
            candidate_reply = input("You (Candidate): ")
            
            chat_payload = {
                "session_id": session_id,
                "candidate_reply": candidate_reply
            }
            
            res = requests.post(f"{API_URL}/interview/chat", json=chat_payload)
            res.raise_for_status()
            
            chat_data = res.json()
            is_finished = chat_data["is_finished"]
            
            print(f"InterviewerBot: {chat_data['message']}")
            
            if is_finished:
                final_transcript = chat_data.get('final_context') 
                print("-" * 60)
                print("✅ Interview Transcript received.")
                
        # 3. Save the raw transcript file FIRST
        if final_transcript:
            transcript_path = save_json(final_transcript, "interview_transcript") # <-- NEW SAVE LINE
            print(f"💾 Raw Transcript saved to: {transcript_path}")
            
            # 4. Call the new Grading API Endpoint
            print("⏳ Sending transcript to grading API...")
            grading_payload = {"transcript_context": final_transcript}
            
            grade_res = requests.post(f"{API_URL}/grade/transcript", json=grading_payload)
            grade_res.raise_for_status()
            
            evaluation_result = grade_res.json()
            print("✅ Grading API response received.")
        
        # 5. Save results (Transcript and Evaluation)
        combined_result = {}
        if final_transcript:
            combined_result.update({"transcript": final_transcript})
        if evaluation_result:
            combined_result.update({"evaluation_result": evaluation_result})


        if combined_result:
            path = save_json(combined_result, "final_interview_results_combined")
            print(f"💾 Final Interview Results (Transcript + Evaluation) saved to: {path}")
            return {"status": "success", "session_id": session_id, "results_path": path}
        
        return {"status": "success", "session_id": session_id}


    except requests.exceptions.RequestException as e:
        print(f"✗ Pipeline API call failed: {e}")
        try:
            # Check for API Response Detail even on failure
            if res.status_code == 500:
                print(f"API Response Detail: {res.json().get('detail', 'No detail provided')}")
            else:
                 print(f"HTTP Error: {res.status_code} {res.reason}")
        except:
            pass 
        return None

# ===================================================
# MAIN FUNCTION
# ===================================================


def main():
    # Phase 1: Test existing endpoints
    #resume_data = parse_resume()
    #job_data = parse_job()
    #match_data = match(resume_data, job_data)
    #quiz_data = quiz(job_data)

    # print("\n=== Summary (Phase 1) ===")
    # for name, ok in [
    #     ("Resume Parsing", bool(resume_data)),
    #     ("Job Parsing", bool(job_data)),
    #     ("Matching", bool(match_data)),
    #     ("Quiz Generation", bool(quiz_data)),
    # ]:
    #     print(f"{'✓' if ok else '✗'} {name}")
    # print("🎉 All existing endpoints tested.")
    
    # print("-" * 60)
    
    # Phase 2: Test the new full interactive pipeline endpoint
    pipeline_data = run_pipeline_test_interactive()
    
    print("\n=== Summary (Phase 2) ===")
    print(f"{'✓' if pipeline_data else '✗'} Interactive Interview Pipeline Test")
    
if __name__ == "__main__":
    main()