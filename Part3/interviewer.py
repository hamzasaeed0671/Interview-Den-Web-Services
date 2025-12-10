# ./Part3/interviewer.py (FINAL CORRECTED VERSION)

import os
import json
import time
# CRITICAL FIX: Use Optional for older Python versions
from typing import List, Any, Dict, Tuple, Optional 
from dotenv import load_dotenv 
import traceback # Added for debugging safety

# --- 1. LOAD ENVIRONMENT VARIABLES IMMEDIATELY ---
load_dotenv() 

# --- 2. CRITICAL FALLBACK CHECK AND SET ---
if not os.getenv("GROQ_API_KEY"):
    print("[WARNING] GROQ_API_KEY not found in environment. Please set it in .env or system variables.")
    # FALLBACK_GROQ_KEY = "MISSING_KEY" 
    # os.environ["GROQ_API_KEY"] = FALLBACK_GROQ_KEY
# ---------------------------------------------------------------------------------


# LangChain Imports
from langchain_groq import ChatGroq
from langchain_core.prompts import SystemMessagePromptTemplate, HumanMessagePromptTemplate
# FIX: Use langchain_classic for ConversationBufferWindowMemory in LangChain 1.x
from langchain_classic.memory import ConversationBufferWindowMemory
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

# --- CONFIGURATION (Shared Constants) ---
MODEL_NAME = "moonshotai/kimi-k2-instruct-0905"  # Using a supported Groq model
SENTINEL_END_PHRASE = "<<END_INTERVIEW>>"
TERMINATION_TAG = "PROTOCOL_TERMINATE_UNPROFESSIONAL" 
WARNING_TAG = "PROTOCOL_WARNING_UNPROFESSIONAL" 
PIVOT_TAG = "PROTOCOL_PIVOT_TO_NEW_TOPIC" 
SOFT_CLOSE_TAG = "PROTOCOL_INITIATE_SOFT_CLOSE" 

MAX_WARNINGS = 1 
MAX_PRIMARY_QUESTIONS = 5
MAX_ELABORATIONS = 1 
MEMORY_WINDOW = 8
TRANSCRIPT_FILE = "interview_transcript.json"

REPETITION_PHRASES = [
    "To ensure clarity, I will repeat the question:",
    "Let me clarify that point for you:",
    "I'm happy to rephrase the question:"
]
# -----------------------------------------------------------------------


# B. LLM and Conversation Chain Setup (Defined globally once)
try:
    chat_llm = ChatGroq(
        model_name=os.getenv("GROQ_MODEL", MODEL_NAME),
        temperature=0.7, 
    )
except Exception as e:
    print(f"[FATAL ERROR] ChatGroq initialization failed: {e}")
    raise


# --- Helper Function for System Instruction ---
def _get_system_instruction(job_description, resume_content, job_level, candidate_name):
    """Centralized function to return the system instruction template."""
    return f"""
You are the **Ultra-Paced Expert Technical Interviewer AI** named **'InterviewerBot'**. Your persona is **highly professional, objective, supportive, and efficient**. Your primary goal is a **rapid, high-signal assessment** that feels conversational.

--- CONTEXT ---
Job Description: {job_description}
Candidate Resume: {resume_content}
The target role level is dynamically set to: **{job_level}**.

--- CORE INTERVIEW OBJECTIVES (EFFICIENCY & CLARITY) ---

1. **Primary Questions:** Limit total primary topics to **{MAX_PRIMARY_QUESTIONS} MAX**.
2. **Follow-up Limit (STRICT):** You **MUST** ask exactly **one (1)** follow-up question per primary topic. This forces a quick transition.

3. **Conversational Non-Answer Handling (CRITICAL NEW FOCUS):**
    * **Repetition/Clarification:** If the candidate's last message is a clear non-answer or an explicit request for repetition/clarification, you **MUST** preface your response with one of the specific starter phrases: "To ensure clarity, I will repeat the question:", "Let me clarify that point for you:", or "I'm happy to rephrase the question:", then state the *exact* last question/follow-up.
    * **Failed/Weak Answer:** Treat it as a technical turn and proceed with the single required follow-up (if not done yet), or pivot immediately (if done).

4. **Question Quality:** Use the first-person pronoun **'I'**. Every question MUST be based directly on the Resume or Job Description.

--- RULES (SIGNALING INTENT TO PYTHON) ---

1. **Disruptive Conduct Check:** If the candidate's last message is abusive, profane, or clearly insulting/dismissive, your **ENTIRE response MUST ONLY be the exact tag: {WARNING_TAG}**.
2. **Graceful Exit Signal:** Once you have completed your target number of primary topics, your final turn **must** contain a clear, non-technical wrap-up question.
3. **Sentinel Phrase:** When ready for the final goodbye, include the exact, standalone phrase: {SENTINEL_END_PHRASE}.
"""


class InterviewerBot:
    """
    Manages the state and logic for a single, ongoing AI interview session.
    """
    def __init__(self, job_desc_str: str, resume_content_str: str, job_level: str, candidate_name: str):
        
        self.job_description = job_desc_str
        self.resume_content = resume_content_str
        self.job_level = job_level
        self.candidate_name = candidate_name
        
        self.warning_count = 0
        self.primary_question_count = 0 
        self.elaboration_count = 0 
        self.is_finished = False
        self.is_in_soft_close = False
        self.transcript_history: List[Dict] = []
        
        self.memory = ConversationBufferWindowMemory(
            memory_key="history",
            input_key="input", 
            return_messages=True,
            k=MEMORY_WINDOW
        )
        self.llm = chat_llm 

    def get_system_instruction(self):
        return _get_system_instruction(self.job_description, self.resume_content, self.job_level, self.candidate_name)

    def init_session(self) -> str:
        """Starts the conversation with the first greeting."""
        initial_greeting = f"Hello {self.candidate_name}, thank you for joining me today. We have a short time, so let's jump right into the technical discussion. How are you doing?"
        # FIX: Use 'type': 'ai'
        self.transcript_history.append({"type": "ai", "content": initial_greeting})
        self.memory.chat_memory.add_ai_message(AIMessage(content=initial_greeting))
        return initial_greeting

    def _invoke_llm_for_response(self, action_guide: str) -> str:
        """Helper to invoke the LLM with the current memory state and an action guide."""
        
        messages = [
            SystemMessage(content=self.get_system_instruction()),
            *self.memory.chat_memory.messages,
            HumanMessage(content=action_guide)
        ]
        
        print("InterviewerBot: Thinking...")
        try:
            response = self.llm.invoke(messages)
            return response.content.strip()
        except Exception as e:
            error_message = f"[LLM_ERROR] The AI model failed to respond: {e}"
            print(error_message)
            return error_message


    def _handle_protocol_response(self, bot_text: str) -> str:
        """Handles tags and updates internal state."""
        
        if bot_text == WARNING_TAG:
            self.warning_count += 1
            self.transcript_history.append({"type": "PROTOCOL", "content": WARNING_TAG}) 
            
            if self.warning_count > MAX_WARNINGS:
                self.is_finished = True
                final_message = "I appreciate your time, but given the lack of professional engagement, I must conclude this interview now."
                self.transcript_history.append({"type": "PROTOCOL", "content": TERMINATION_TAG}) 
                self.transcript_history.append({"type": "ai", "content": final_message})
                return final_message
            
            warning_message = "I noticed your last response was unprofessional. Please maintain a professional demeanor. I'll re-ask the question."
            self.transcript_history.append({"type": "ai", "content": warning_message})
            self.memory.chat_memory.add_ai_message(AIMessage(content=warning_message))
            
            re_ask_message = "The candidate has been warned. Acknowledge this and output the *exact* last technical question (or follow-up) asked before the candidate's last message. DO NOT PIVOT. DO NOT REPEAT THE WARNING MESSAGE."
            
            bot_text = self._invoke_llm_for_response(re_ask_message)
        
        if SENTINEL_END_PHRASE in bot_text:
            self.is_finished = True
            final_message = bot_text.replace(SENTINEL_END_PHRASE, "").strip()
            self.transcript_history.append({"type": "PROTOCOL", "content": SENTINEL_END_PHRASE})
            self.transcript_history.append({"type": "ai", "content": final_message})
            return final_message
            
        # FIX: Use 'type': 'ai'
        self.transcript_history.append({"type": "ai", "content": bot_text})
        self.memory.chat_memory.add_ai_message(AIMessage(content=bot_text))
        
        return bot_text


    def process_turn(self, candidate_reply: str) -> Tuple[str, bool]:
        """Processes one turn of candidate input."""
        # FIX: Use 'type': 'human'
        self.transcript_history.append({"type": "human", "content": candidate_reply}) 
        self.memory.chat_memory.add_user_message(HumanMessage(content=candidate_reply))
        
        if self.is_in_soft_close:
            return self._continue_soft_close(candidate_reply)
        
        if self.primary_question_count >= MAX_PRIMARY_QUESTIONS:
            print(f"[PACING OVERRIDE] Max primary questions ({MAX_PRIMARY_QUESTIONS}) reached. Initiating graceful soft close.")
            return self._initiate_soft_close()

        if self.primary_question_count == 0:
            action_guide = "Analyze the candidate's LATEST message. If abusive/profane, output the protocol tag. Otherwise, acknowledge the greeting, then transition immediately to the first primary technical question (Question 1) based on the rules."
        elif self.elaboration_count < MAX_ELABORATIONS:
            action_guide = f"The candidate has responded. Based on the rules: If they asked for repetition/clarification, use one of the specific starter phrases and repeat the last question. Otherwise, you MUST now ask the single required follow-up question (Elaboration Count: {self.elaboration_count + 1}). Check for abuse and output the warning tag if detected."
        else:
            action_guide = f"The current topic is complete (Max Elaborations: {MAX_ELABORATIONS} reached). Acknowledge the candidate's last answer *briefly*, then gracefully pivot and ask a NEW primary technical question (Question {self.primary_question_count + 1}) based on the Resume/JD. Check for abuse and output the warning tag if detected."

        bot_text = self._invoke_llm_for_response(action_guide)
        final_bot_text = self._handle_protocol_response(bot_text)

        if self.is_finished: 
            return final_bot_text, True

        is_repetition = any(final_bot_text.startswith(phrase) for phrase in REPETITION_PHRASES)

        if not is_repetition:
            if self.primary_question_count == 0:
                self.primary_question_count = 1 
            elif self.elaboration_count >= MAX_ELABORATIONS:
                self.primary_question_count += 1
                self.elaboration_count = 0 
                self.transcript_history.append({"type": "PROTOCOL", "content": PIVOT_TAG})
            else:
                self.elaboration_count += 1
        else:
            print("[PACING EXCEPTION] Repetition detected. Elaboration count is NOT incremented.")

        return final_bot_text, self.is_finished
    
    def _initiate_soft_close(self) -> Tuple[str, bool]:
        self.is_in_soft_close = True
        soft_close_prompt = "The technical interview section is complete. Output ONLY the final soft close question (Rule 2: 'Do you have any final questions for me...')."
        
        bot_text = self._invoke_llm_for_response(soft_close_prompt)
        
        self.transcript_history.append({"type": "PROTOCOL", "content": SOFT_CLOSE_TAG})
        self.transcript_history.append({"type": "ai", "content": bot_text})
        self.memory.chat_memory.add_ai_message(AIMessage(content=bot_text))
        
        return bot_text, False

    def _continue_soft_close(self, candidate_reply: str) -> Tuple[str, bool]:
        final_signal_prompt = f"The candidate has replied to your soft close question. Reply conversationally to their final statement/question, and then immediately output the exact, standalone phrase: {SENTINEL_END_PHRASE}. DO NOT ASK NEW QUESTIONS OR FOLLOW-UPS."
        
        bot_text = self._invoke_llm_for_response(final_signal_prompt)
        
        if SENTINEL_END_PHRASE in bot_text:
            self.is_finished = True
            final_message = bot_text.replace(SENTINEL_END_PHRASE, "").strip()
            self.transcript_history.append({"type": "PROTOCOL", "content": SENTINEL_END_PHRASE})
            self.transcript_history.append({"type": "ai", "content": final_message})
            return final_message, True
        
        self.transcript_history.append({"type": "ai", "content": bot_text})
        self.memory.chat_memory.add_ai_message(AIMessage(content=bot_text))
        return bot_text, False
        

    def get_context_for_grading(self) -> Dict[str, Any]:
        """Prepares the final data structure needed by the grader and saves the transcript file."""
        final_context = {
            "timestamp": time.time(),
            "job_level": self.job_level,
            "candidate_name": self.candidate_name,
            "job_description": self.job_description,
            "resume_content": self.resume_content,
            "transcript": self.transcript_history
        }
        
        try:
            with open(TRANSCRIPT_FILE, 'w', encoding='utf-8') as f:
                json.dump(final_context, f, indent=4)
            print(f"\n[FINALIZATION] Successfully saved interview transcript to {TRANSCRIPT_FILE}.")
        except Exception as e:
            print(f"[ERROR] Could not save transcript file: {e}")
            
        return final_context


# ===================================================
# PUBLIC API ADAPTER FUNCTIONS (Called by main.py / api.py)
# ===================================================
try:
    from Part3.grader import evaluate_candidate
except ImportError:
    def evaluate_candidate(context):
        raise NotImplementedError("Part3/grader.py not found or evaluate_candidate is missing.")


def start_interview_logic(jd_data: Dict, resume_data: Dict) -> Tuple[str, InterviewerBot]:
    """Initializes the InterviewerBot instance and gets the first greeting."""
    job_desc_str = json.dumps(jd_data, indent=4)
    resume_content_str = json.dumps(resume_data, indent=4)
    job_level = jd_data.get('experience_required', {}).get('level', 'General')
    candidate_name = resume_data.get('Name', 'Candidate')
    
    interviewer = InterviewerBot(job_desc_str, resume_content_str, job_level, candidate_name)
    first_message = interviewer.init_session()
    
    return first_message, interviewer


def chat_interview_logic(interviewer_instance: InterviewerBot, candidate_reply: str) -> Tuple[str, bool, Optional[Dict]]:
    """
    Processes one chat turn.
    Returns: (ai_response: str, is_finished: bool, final_context: Optional[Dict])
    """
    
    try:
        ai_response, is_finished = interviewer_instance.process_turn(candidate_reply)
    except Exception as e:
        ai_response = f"Internal chat processing failure: {e}"
        is_finished = True
        print(f"[CRITICAL_PROCESS_ERROR] {ai_response}")

    final_context: Optional[Dict[str, Any]] = None

    if is_finished:
        final_context = interviewer_instance.get_context_for_grading()
        print("[FINALIZATION] Interview finished. Transcript prepared for external grading API call.")
        
    return ai_response, is_finished, final_context