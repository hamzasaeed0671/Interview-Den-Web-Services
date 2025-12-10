# ./Part3/grader.py (FINAL CORRECTED VERSION)

import os
import json
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langchain_core.prompts import SystemMessagePromptTemplate, MessagesPlaceholder
from dotenv import load_dotenv

# Load environment variables for the API key when run standalone or imported
load_dotenv()

# --- Pydantic Schema (Internal Definition) ---
class InterviewRating(BaseModel):
    """Structured output for the final candidate rating."""
    overall_score: int = Field(..., description="Score out of 100 based on overall fit for the job.")
    strengths: List[str] = Field(..., description="3 key strengths demonstrated in the interview.")
    weaknesses: List[str] = Field(..., description="3 key gaps or weaknesses identified.")
    hiring_recommendation: str = Field(..., description="Final recommendation, e.g., 'Strong Hire', 'Proceed with Caution', 'No Hire'")

# --- Configuration (Internal Definition) ---
# CRITICAL FIX: Use a stable, currently supported Groq model
MODEL_NAME = "moonshotai/kimi-k2-instruct-0905"
EVALUATION_FILE = "final_evaluation_report.json"

# --- LLM Setup (Fixed Temperature for Evaluation) ---
# Ensures deterministic, structured output
rating_llm_fixed_temp = ChatGroq(
    model_name=MODEL_NAME,
    temperature=0.0, 
)

# --- Helper: Grade Agent Definition (MODIFIED) ---
def get_grading_chain(agent_role: str):
    """
    Creates a structured output chain for a specific grading agent role.
    """
    
    # 1. Define the specific instruction based on the agent's job
    vague_penalty_instruction = """
    ***VAGUENESS PENALTY: CRITICALLY DEDUCT POINTS IF*** a candidate's answer is overly vague, uses generic buzzwords without specific examples, or avoids providing concrete technical details when asked. Vagueness must be treated as a significant weakness.
    """
    
    if agent_role == "Initial Scorer":
        debate_prompt = f"""
        You are the primary scoring agent. Your **#1 priority** is to assess the candidate's **Mentality and Approach** to problem-solving.
        
        **SCORING GUIDELINE (CRITICAL):** Grade with leniency, focusing on **potential and curiosity**. Start the score high (e.g., 90/100) and deduct points only for specific, major errors or complete knowledge failures required for the job. Do not score harshly on minor confusion.
        {vague_penalty_instruction}
        
        Provide a holistic score and detailed summary strictly based on the transcript, assessing:
        1. **Mentality:** Self-awareness, curiosity, handling ambiguity, and problem-solving method.
        2. **Technical Depth:** Accuracy against the job level and resume project claims.
        """
    else: # Challenger Grader
        debate_prompt = f"""
        You are the secondary, skeptical grading agent. Your job is to **CRITICALLY REVIEW** the Initial Scorer's findings below.
        1. **Initial Score:** {{initial_score_json}} 
        2. **Action:** Challenge the initial score if you find bias, missing context, or flawed logic. **Specifically, assess if the Initial Scorer was strict enough on vagueness and generalities.**
        {vague_penalty_instruction}
        3. **Final Task:** Provide your final, independent score and justification using the schema. Your score should only agree if the Initial Scorer's logic is perfect.
        
        CRITICAL RULE: While you must critique weaknesses, your final recommendation should reflect the overall Consensus Score's passing threshold.
        """

    # 2. Construct the grading prompt
    grader_instruction = f"""
    --- AGENT ROLE: {agent_role} ---
    {debate_prompt}
    
    Your final analysis must consider:
    - Technical Depth (compared to the {{job_level}} target).
    - Mental Aptitude (problem-solving approach, self-awareness, handling uncertainty).
    - Communication (clarity, confidence, professionalism).

    --- CRITICAL FORMATTING RULE ---
    The lists for 'strengths' and 'weaknesses' MUST contain only **simple strings**, one for each point. 
    DO NOT use nested lists (e.g., [['point 1']]), markdown bullet points, or numbering within the JSON strings.
    
    GENERATE A JSON OBJECT STRICTLY FOLLOWING THE PYTHON SCHEMA. Do not include any text, prose, or conversation outside the JSON.
    """
    
    rating_prompt = SystemMessagePromptTemplate.from_template(grader_instruction)

    # 3. Create the final chain with structured output
    grading_chain = rating_llm_fixed_temp.with_structured_output(
        schema=InterviewRating,
        method="json_schema"
    )
    
    return rating_prompt, grading_chain

# --- Public Function for Phase 2 (Accepts data directly) ---
def evaluate_candidate(context: Dict):
    """
    Runs the two-agent evaluation process using the context dictionary passed from the interviewer.
    """
    if not context:
        return

    # Define the passing threshold here (70/100 as requested)
    PASSING_THRESHOLD = 70 
    
    print("\n--- Grader.py: Initiating Final Candidate Evaluation ---")
    
    # --- Setup Context Variables ---
    job_level = context.get('job_level', 'General')
    # CRITICAL: We now rely on 'transcript' being the list of messages
    transcript_data = context['transcript'] 
    
    # Prepare message list for LLM (Transcript + Context)
    rating_messages: List[BaseMessage] = [
        HumanMessage(content="--- JOB AND CANDIDATE CONTEXT ---"),
        HumanMessage(content=f"Job Level: {job_level}"),
        HumanMessage(content=f"Job Description: {context.get('job_description', 'N/A')}"),
        HumanMessage(content=f"Candidate Resume: {context.get('resume_content', 'N/A')}"),
        HumanMessage(content="--- CONVERSATION TRANSCRIPT ---"),
    ]
    for msg in transcript_data:
        # This KeyError is fixed because interviewer.py now sends 'type'
        if msg['type'] == 'human':
            rating_messages.append(HumanMessage(content=msg['content']))
        elif msg['type'] == 'ai':
            rating_messages.append(AIMessage(content=msg['content']))
    rating_messages.append(HumanMessage(content="--- END TRANSCRIPT ---"))


    # --- AGENT 1: Initial Scorer ---
    print("[INFO] Agent 1 (Initial Scorer) running...")
    scorer_prompt, scorer_chain = get_grading_chain("Initial Scorer")
    
    # Inject Agent 1's specific prompt variables
    agent_1_messages = scorer_prompt.format_messages(job_level=job_level) + rating_messages
    initial_rating_obj = scorer_chain.invoke(agent_1_messages)
    
    
    # --- AGENT 2: Challenger Grader ---
    # Convert Agent 1's result to JSON for Agent 2 to review
    initial_score_json = initial_rating_obj.model_dump_json()
    print("[INFO] Agent 2 (Challenger) running to validate initial score...")
    
    challenger_prompt, challenger_chain = get_grading_chain("Challenger Grader")
    
    # Inject Agent 2's specific prompt variables (including the JSON score)
    agent_2_messages = challenger_prompt.format_messages(job_level=job_level, initial_score_json=initial_score_json) + rating_messages
    final_rating_obj = challenger_chain.invoke(agent_2_messages)

    
    # --- Consensus and Final Report ---
    
    # Calculate Average Score (Consensus)
    avg_score = round((initial_rating_obj.overall_score + final_rating_obj.overall_score) / 2)
    
    # --- CRITICAL PYTHON FIX: Override Recommendation Based on Score ---
    final_recommendation = final_rating_obj.hiring_recommendation
    
    if avg_score >= PASSING_THRESHOLD:
        final_recommendation = "Strong Hire (Exceeded Threshold)"
    elif avg_score >= 55: # Setting a slightly lower bar for 'Proceed'
        final_recommendation = "Proceed with Caution (Meets Potential)"
    else:
        final_recommendation = "No Hire (Fails Minimum Criteria)"

    # Use the Challenger's summary as the final report due to its critical review
    final_report = final_rating_obj.model_dump()
    final_report['overall_score'] = avg_score
    final_report['hiring_recommendation'] = final_recommendation # Overwrite LLM's recommendation
    
    # Save the final result to a separate JSON file
    with open(EVALUATION_FILE, 'w', encoding='utf-8') as f:
        json.dump(final_report, f, indent=4)
    
    print(f"[INFO] Final evaluation (Consensus Score) saved to {EVALUATION_FILE}")

    # Display Report (This output will be visible on the Uvicorn backend console)
    print("\n--- FINAL EVALUATION REPORT (Consensus) ---")
    print(f"AGENT 1 SCORE: {initial_rating_obj.overall_score}/100")
    print(f"AGENT 2 SCORE: {final_rating_obj.overall_score}/100")
    print(f"CONSENSUS SCORE: {avg_score}/100")
    print("-------------------------------------------")
    
    # We return the dictionary for the API endpoint
    return final_report


if __name__ == "__main__":
    # This standalone block is only for isolated testing (requires interview_transcript.json)
    def load_transcript_for_standalone_test():
        if os.path.exists("interview_transcript.json"):
             with open("interview_transcript.json", 'r', encoding='utf-8') as f:
                return json.load(f)
        return None
    
    context_data = load_transcript_for_standalone_test()
    if context_data:
        # Simulate the API call context (which is the combined transcript context)
        evaluate_candidate(context_data)
    else:
        print("[CRITICAL] Cannot run Grader.py standalone. Run test.py first to create context.")