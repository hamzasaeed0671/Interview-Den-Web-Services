# ./api.py
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query
from pydantic import BaseModel
import tempfile, json, os, uuid
from typing import Dict, Any, Optional 
# from fastapi.middleware.cors import CORSMiddleware
# from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Response, Query
from fastapi.responses import StreamingResponse
# from pydantic import BaseModel
# import tempfile, json, uuid, traceback, os
# from typing import Dict, Any, Optional
# import edge_tts
import traceback

# Import all logic functions from main.py
from main import (
    TRANSCRIPT_FILE, parse_resume_logic, parse_job_logic, 
    match_logic, quiz_logic, start_interview_logic, chat_interview_logic,
    evaluate_candidate 
)

# Create FastAPI app instance FIRST
app = FastAPI(title="Resume–Job Matching API")

# THEN add CORS middleware configuration for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[ "https://fyp-production-9394.up.railway.app",  # Your frontend URL
        "http://localhost:3000",  ],
    allow_credentials=True,
    allow_methods=["*"],              # Allow all methods (POST, GET, etc.)
    allow_headers=["*"],              # Allow all headers
)

# --- GLOBAL IN-MEMORY CACHE FOR INTERVIEW SESSIONS ---
INTERVIEW_SESSIONS = {}

# --- Pydantic models ---
class InterviewStartInput(BaseModel):
    job_description_json: str
    resume_json: str

class InterviewChatInput(BaseModel):
    session_id: str
    candidate_reply: str

class InterviewResponse(BaseModel):
    session_id: str
    message: str
    is_finished: bool = False
    final_context: Optional[Dict[str, Any]] = None 


# @app.get("/api/voice")
# async def stream_voice(text: str = Query(..., description="Text to convert to speech"), voice: str = Query("en-US-AriaNeural", description="Voice name")):
#     """
#     Streams audio bytes directly to the client using edge-tts.
#     No disk writes - pure streaming for minimal latency (TTFB).
#     """
#     if not text or not text.strip():
#         raise HTTPException(status_code=400, detail="Text cannot be empty")
#     
#     # communicate = edge_tts.Communicate(text.strip(), voice)
#     
#     # async def audio_generator():
#     #     async for chunk in communicate.stream():
#     #         if chunk["type"] == "audio":
#     #             yield chunk["data"]
#     
#     # return StreamingResponse(audio_generator(), media_type="audio/mpeg")
#     return {"error": "Voice streaming is disabled"}



# --- Pydantic model for the new Grading Endpoint ---
class GradingInput(BaseModel):
    """Expects the full transcript context dictionary."""
    transcript_context: Dict[str, Any]


# ===================================================
# NEW GRADING ENDPOINT
# ===================================================

@app.post("/grade/transcript")
async def grade_transcript(data: GradingInput):
    """
    Accepts the final interview context and runs the grading process.
    """
    try:
        # Assuming the KeyErrors are fixed in interviewer.py, this should now succeed
        evaluation_result = evaluate_candidate(data.transcript_context)
        
        print("[API] Grading completed successfully.")
        return {
            "status": "Grading Complete",
            "evaluation": evaluation_result
        }
    except NotImplementedError:
        raise HTTPException(status_code=501, detail="Grading feature is not implemented (Part3/grader.py not found).")
    except Exception as e:
        # This traceback call is now safe
        traceback.print_exc() 
        print(f"[ERROR] Grading failed: {e}")
        # This will send the error detail back to the client
        raise HTTPException(status_code=500, detail=f"Internal server error during grading: {e}")


# ===================================================
# INTERACTIVE INTERVIEW ENDPOINTS (Unchanged)
# ===================================================

@app.post("/interview/start", response_model=InterviewResponse)
async def start_interview(data: InterviewStartInput):
    try:
        jd_data = json.loads(data.job_description_json)
        resume_data = json.loads(data.resume_json)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON format for Job Description or Resume content.")

    session_id = str(uuid.uuid4())

    try:
        first_message, interviewer_instance = start_interview_logic(jd_data, resume_data)
        INTERVIEW_SESSIONS[session_id] = interviewer_instance

        print(f"\n[API] Started new session: {session_id}")
        return InterviewResponse(
            session_id=session_id,
            message=first_message,
            is_finished=False
        )
    except Exception as e:
        print(f"[ERROR] Failed to start interview session: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start interview session: {e}")


@app.post("/interview/chat", response_model=InterviewResponse)
async def continue_interview(data: InterviewChatInput):
    session_id = data.session_id
    candidate_reply = data.candidate_reply

    if session_id not in INTERVIEW_SESSIONS:
        raise HTTPException(status_code=404, detail="Interview session not found or has expired.")

    interviewer_instance = INTERVIEW_SESSIONS[session_id]

    try:
        ai_response, is_finished, final_context = chat_interview_logic(interviewer_instance, candidate_reply)
        
        if is_finished:
            del INTERVIEW_SESSIONS[session_id]
            print(f"[API] Finished and cleared session: {session_id}")

        return InterviewResponse(
            session_id=session_id,
            message=ai_response,
            is_finished=is_finished,
            final_context=final_context 
        )

    except Exception as e:
        print(f"[ERROR] Failed to continue chat turn for session {session_id}: {e}")
        traceback.print_exc() 
        if session_id in INTERVIEW_SESSIONS:
            del INTERVIEW_SESSIONS[session_id]
        raise HTTPException(status_code=500, detail=f"Internal server error during chat turn: {e}")

# ===================================================
# EXISTING ENDPOINTS (Unchanged)
# ===================================================
@app.post("/parse/resume")
async def parse_resume(file: UploadFile = File(...), job_file: UploadFile = None):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(await file.read())
        resume_path = tmp.name

    job_path = None
    if job_file:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as tmpj:
            tmpj.write(await job_file.read())
            job_path = tmpj.name

    data = parse_resume_logic(resume_path, job_path)
    return data

@app.post("/parse/job")
async def parse_job(file: UploadFile = File(...)):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as tmp:
        tmp.write(await file.read())
        job_path = tmp.name
    data = parse_job_logic(job_path)
    return data

@app.post("/match")
async def match(resume_json: UploadFile = File(...), job_json: UploadFile = File(...)):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as rtmp, \
          tempfile.NamedTemporaryFile(delete=False, suffix=".json") as jtmp:
        rtmp.write(await resume_json.read())
        jtmp.write(await job_json.read())
        r_path, j_path = rtmp.name, jtmp.name
    data = match_logic(r_path, j_path)
    return data

@app.post("/quiz")
async def generate_quiz(job_json: UploadFile = File(...), questions: int = Form(5)):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as tmp:
        tmp.write(await job_json.read())
        job_path = tmp.name
    data = quiz_logic(job_path, questions)
    return data
# from fastapi.middleware.cors import CORSMiddleware
# from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Response, Query
# from fastapi.responses import StreamingResponse
# from pydantic import BaseModel
# import tempfile, json, uuid, traceback, os
# from typing import Dict, Any, Optional
# import edge_tts

# # Import valid logic
# from main import (
#     parse_resume_logic, parse_job_logic, 
#     match_logic, quiz_logic, start_interview_logic, chat_interview_logic,
#     evaluate_candidate 
# )

# app = FastAPI(title="Resume–Job Matching API")

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"], 
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# INTERVIEW_SESSIONS = {}

# class InterviewStartInput(BaseModel):
#     job_description_json: str
#     resume_json: str

# class InterviewChatInput(BaseModel):
#     session_id: str
#     candidate_reply: str

# class InterviewResponse(BaseModel):
#     session_id: str
#     message: str
#     is_finished: bool = False
#     final_context: Optional[Dict[str, Any]] = None 

# class GradingInput(BaseModel):
#     transcript_context: Dict[str, Any]

# # ===================================================
# # TTS STREAMING ENDPOINT (edge-tts)
# # ===================================================

# @app.get("/api/voice")
# async def stream_voice(text: str = Query(..., description="Text to convert to speech"), voice: str = Query("en-US-AriaNeural", description="Voice name")):
#     """
#     Streams audio bytes directly to the client using edge-tts.
#     No disk writes - pure streaming for minimal latency (TTFB).
#     """
#     if not text or not text.strip():
#         raise HTTPException(status_code=400, detail="Text cannot be empty")
    
#     communicate = edge_tts.Communicate(text.strip(), voice)
    
#     async def audio_generator():
#         async for chunk in communicate.stream():
#             if chunk["type"] == "audio":
#                 yield chunk["data"]
    
#     return StreamingResponse(audio_generator(), media_type="audio/mpeg")


# # ===================================================
# # INTERVIEW ENDPOINTS (TEXT ONLY)
# # ===================================================

# @app.post("/interview/start", response_model=InterviewResponse)
# async def start_interview(data: InterviewStartInput):
#     try:
#         jd_data = json.loads(data.job_description_json)
#         resume_data = json.loads(data.resume_json)
        
#         session_id = str(uuid.uuid4())
#         first_message, interviewer_instance = start_interview_logic(jd_data, resume_data)
        
#         if first_message is None:
#              first_message = "Hello, I am ready to interview you."

#         INTERVIEW_SESSIONS[session_id] = interviewer_instance
#         print(f"[API] Started Session: {session_id}")
        
#         return InterviewResponse(
#             session_id=session_id,
#             message=first_message,
#             is_finished=False
#         )
#     except Exception as e:
#         print(f"[ERROR] Start Interview: {e}")
#         traceback.print_exc()
#         raise HTTPException(status_code=500, detail=str(e))


# @app.post("/interview/chat", response_model=InterviewResponse)
# async def continue_interview(data: InterviewChatInput):
#     session_id = data.session_id
#     if session_id not in INTERVIEW_SESSIONS:
#         raise HTTPException(status_code=404, detail="Session not found.")

#     interviewer_instance = INTERVIEW_SESSIONS[session_id]

#     try:
#         # PURE TEXT LOGIC
#         ai_response, is_finished, final_context = chat_interview_logic(interviewer_instance, data.candidate_reply)
        
#         if is_finished:
#             del INTERVIEW_SESSIONS[session_id]

#         return InterviewResponse(
#             session_id=session_id,
#             message=ai_response,
#             is_finished=is_finished,
#             final_context=final_context 
#         )
#     except Exception as e:
#         print(f"[ERROR] Chat: {e}")
#         raise HTTPException(status_code=500, detail=str(e))

# @app.post("/grade/transcript")
# async def grade_transcript(data: GradingInput):
#     try:
#         evaluation_result = evaluate_candidate(data.transcript_context)
#         return { "status": "Grading Complete", "evaluation": evaluation_result }
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

# # ===================================================
# # PARSING ENDPOINTS
# # ===================================================
# @app.post("/parse/resume")
# async def parse_resume(file: UploadFile = File(...), job_file: UploadFile = None):
#     with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
#         tmp.write(await file.read())
#         r_path = tmp.name
#     j_path = None
#     if job_file:
#         with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as tmpj:
#             tmpj.write(await job_file.read())
#             j_path = tmpj.name
#     return parse_resume_logic(r_path, j_path)

# @app.post("/parse/job")
# async def parse_job(file: UploadFile = File(...)):
#     with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as tmp:
#         tmp.write(await file.read())
#         path = tmp.name
#     return parse_job_logic(path)

# @app.post("/match")
# async def match(resume_json: UploadFile = File(...), job_json: UploadFile = File(...)):
#     with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as rtmp, \
#           tempfile.NamedTemporaryFile(delete=False, suffix=".json") as jtmp:
#         rtmp.write(await resume_json.read())
#         jtmp.write(await job_json.read())
#         return match_logic(rtmp.name, jtmp.name)

# @app.post("/quiz")
# async def generate_quiz(job_json: UploadFile = File(...), questions: int = Form(5)):
#     with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as tmp:
#         tmp.write(await job_json.read())
#         return quiz_logic(tmp.name, questions)
