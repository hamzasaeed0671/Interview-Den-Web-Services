#!/usr/bin/env python3
"""
Simplified Agent-based quiz generator using LangChain + Groq.
(No 'agent_scratchpad' prompt issue)
"""

import os
import re
import sys
import json
import uuid
from typing import Dict, List, Any

from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage

# Allow importing config.py from project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import config


# ==============================
# 🔹 Question Generator Agent
# ==============================
class QuestionGeneratorAgent:
    """Generates multiple-choice technical questions."""

    def __init__(self):
        api_key = config.get_current_api_key()
        self.llm = ChatGroq(api_key=api_key, model_name=config.MODEL_NAME)
        print("🧩 QuestionGeneratorAgent initialized.")

    def generate_questions(self, job_data: Dict[str, Any], num_questions: int) -> List[Dict[str, Any]]:
        job_title = job_data.get("job_title", "Unknown Title")
        skills = ", ".join(job_data.get("skills_required", {}).get("technical_skills", []))
        responsibilities = "; ".join(job_data.get("job_responsibilities", []))
        experience = job_data.get("experience_required", {}).get("years_of_experience", "Not specified")
        level = job_data.get("experience_required", {}).get("level", "Not specified")

        # Define difficulty descriptions
        level_descriptions = {
            "Internship": "Focus on fundamental concepts and basic skills appropriate for someone new to the field",
            "Associate": "Cover core skills with some practical application for early career professionals",
            "Junior": "Include practical scenarios and common problem-solving for developers with some experience",
            "Senior": "Emphasize complex scenarios, architecture decisions, and advanced concepts for experienced professionals",
            "Expert": "Focus on cutting-edge technologies, system design, and expert-level problem-solving for industry leaders"
        }
        
        level_description = level_descriptions.get(level, "Appropriate for the role's requirements")

        prompt_text = (
            f"You are an expert technical interviewer.\n\n"
            f"Job Title: {job_title}\n"
            f"Skills: {skills}\n"
            f"Responsibilities: {responsibilities}\n"
            f"Experience Level: {level} - {level_description}\n"
            f"Years of Experience: {experience}\n\n"
            f"Generate {num_questions} concise, technically accurate multiple-choice questions (MCQs) "
            f"appropriate for a {level} level candidate.\n"
            f"The questions should match the difficulty level:\n"
            f"- Internship: Basic concepts, fundamental knowledge\n"
            f"- Associate: Core skills, simple applications\n"
            f"- Junior: Practical scenarios, common problem-solving\n"
            f"- Senior: Complex scenarios, architecture decisions\n"
            f"- Expert: Advanced concepts, system design, cutting-edge technologies\n\n"
            f"Each question must follow this format:\n\n"
            f"1. Question text\nA. Option A\nB. Option B\nC. Option C\nD. Option D\nCorrect answer: X\n"
        )

        try:
            messages = [
                SystemMessage(content="You are an expert quiz generator."),
                HumanMessage(content=prompt_text)
            ]
            result = self.llm.invoke(messages)
            raw_output = result.content
            return self._parse_questions(raw_output)
        except Exception as e:
            print(f"❌ Error generating questions: {e}")
            return []

    def _parse_questions(self, text: str) -> List[Dict[str, Any]]:
        pattern = re.compile(
            r"(?:\d+\.\s*)?(.*?)\nA\.\s*(.*?)\nB\.\s*(.*?)\nC\.\s*(.*?)\nD\.\s*(.*?)\n(?:Correct answer|Answer):\s*([A-D])",
            re.DOTALL | re.IGNORECASE
        )
        matches = pattern.findall(text)
        if not matches:
            # Only save debug file if directory exists
            if os.path.exists(config.QUIZ_DATA_DIR):
                debug_path = os.path.join(config.QUIZ_DATA_DIR, "debug_agent_raw_output.txt")
                with open(debug_path, "w", encoding="utf-8") as f:
                    f.write(text)
                print(f"⚠️ Could not parse any questions. Raw output saved to {debug_path}")
            else:
                print("⚠️ Could not parse any questions.")
            return []

        parsed = []
        seen = set()
        for q, a, b, c, d, correct in matches:
            q = q.strip()
            if q and q not in seen:
                seen.add(q)
                parsed.append({
                    "question": q,
                    "options": [
                        {"letter": "A", "text": a.strip()},
                        {"letter": "B", "text": b.strip()},
                        {"letter": "C", "text": c.strip()},
                        {"letter": "D", "text": d.strip()},
                    ],
                    "correct_answer": correct.strip().upper()
                })
        return parsed


# ==============================
# 🔹 Question Scorer Agent
# ==============================
class QuestionScorerAgent:
    """Validates whether generated questions are relevant and well-formed."""

    def __init__(self):
        api_key = config.get_current_api_key()
        self.llm = ChatGroq(api_key=api_key, model_name=config.MODEL_NAME, verbose=True)

    def score_question(self, question: Dict[str, Any], job_data: Dict[str, Any]) -> bool:
        q_text = question.get("question", "")
        opts = "\n".join([f"{o['letter']}. {o['text']}" for o in question["options"]])
        level = job_data.get("experience_required", {}).get("level", "Not specified")
        
        # Define difficulty descriptions for scoring
        level_descriptions = {
            "Internship": "questions should focus on fundamental concepts and basic skills",
            "Associate": "questions should cover core skills with some practical application",
            "Junior": "questions should include practical scenarios and common problem-solving",
            "Senior": "questions should emphasize complex scenarios, architecture decisions, and advanced concepts",
            "Expert": "questions should focus on cutting-edge technologies, system design, and expert-level problem-solving"
        }
        
        level_description = level_descriptions.get(level, "questions should be appropriate for the role's requirements")
        
        full_prompt = (
            f"Question:\n{q_text}\n\n"
            f"Options:\n{opts}\n\n"
            f"Correct Answer: {question['correct_answer']}\n\n"
            f"Job Level: {level}\n\n"
            f"This question is for a {level} level position. The questions at this level should {level_description}.\n\n"
            f"Is this a valid, relevant technical MCQ appropriate for a {level} level candidate? "
            f"Check that the difficulty matches the level and the content is relevant to the job.\n"
            f"Respond only 'VALID' or 'INVALID'."
        )
        
        try:
            result = self.llm.invoke([HumanMessage(content=full_prompt)])
            output = result.content.strip().upper()
            return output == "VALID"
        except Exception as e:
            print(f"⚠️ Scoring error: {e}")
            return False


# ==============================
# 🔹 Quiz Generator Orchestrator
# ==============================
class AgentBasedQuizGenerator:
    def __init__(self):
        self.generator = QuestionGeneratorAgent()
        self.scorer = QuestionScorerAgent()
        # Don't create directories by default
        print("🔍 AgentBasedQuizGenerator initialized.")

    def generate_quiz(self, job_data: Dict[str, Any], num_questions: int) -> str:
        all_questions = []
        seen = set()
        attempts = 0
        MAX_ATTEMPTS = num_questions * 2

        while len(all_questions) < num_questions and attempts < MAX_ATTEMPTS:
            remaining = num_questions - len(all_questions)
            new_questions = self.generator.generate_questions(job_data, remaining)
            for q in new_questions:
                if q["question"] in seen:
                    continue
                if self.scorer.score_question(q, job_data):
                    all_questions.append(q)
                    seen.add(q["question"])
                if len(all_questions) >= num_questions:
                    break
            attempts += 1

        print(f"✅ Generated {len(all_questions)}/{num_questions} valid questions.")
        return self._save_quiz(job_data, all_questions)

    def _save_quiz(self, job_data: Dict[str, Any], questions: List[Dict[str, Any]]) -> str:
        # Only create directory if it doesn't exist
        if not os.path.exists(config.QUIZ_DATA_DIR):
            os.makedirs(config.QUIZ_DATA_DIR, exist_ok=True)
        
        slug = ''.join(c if c.isalnum() else '_' for c in job_data.get('job_title', 'unknown').lower())
        level = job_data.get("experience_required", {}).get("level", "").lower()
        if level:
            slug += f"_{level}"
        quiz_id = f"quiz_{slug}_{uuid.uuid4().hex[:8]}"
        file_path = os.path.join(config.QUIZ_DATA_DIR, f"{quiz_id}.json")

        # Add metadata including level information
        metadata = {
            "question_count": len(questions),
            "level": job_data.get("experience_required", {}).get("level", "Not specified")
        }

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump({
                "quiz_id": quiz_id,
                "job_info": job_data,
                "metadata": metadata,
                "questions": questions
            }, f, indent=2, ensure_ascii=False)

        print(f"💾 Quiz saved at: {file_path}")
        return quiz_id