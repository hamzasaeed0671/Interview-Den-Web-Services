#!/usr/bin/env python3
"""
Unified quiz generator: uses LangChain Agent if available,
falls back to direct Groq API if not.
"""

import os
import sys
import json
import uuid
import re
import requests
from typing import List, Dict, Any

# Import config from project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import config

# ✅ Correct import — no silent ImportError anymore
try:
    from agent_generator import AgentBasedQuizGenerator
    AGENT_BASED_AVAILABLE = True
except ImportError as e:
    print(f"[WARNING] Could not import agent-based generator: {e}")
    AGENT_BASED_AVAILABLE = False


# =====================================
# 🔹 Fallback (Direct API) Implementation
# =====================================
class JobTestGenerator:
    """Fallback question generator using Groq API directly."""

    def __init__(self):
        # Don't create directories by default
        pass

    def generate_batch_questions(self, job_title, skills, responsibilities, experience, level, num_questions):
        skills_str = ", ".join(skills)
        resp_str = "; ".join(responsibilities)
        
        # Define difficulty descriptions
        level_descriptions = {
            "Internship": "Focus on fundamental concepts and basic skills appropriate for someone new to the field",
            "Associate": "Cover core skills with some practical application for early career professionals",
            "Junior": "Include practical scenarios and common problem-solving for developers with some experience",
            "Senior": "Emphasize complex scenarios, architecture decisions, and advanced concepts for experienced professionals",
            "Expert": "Focus on cutting-edge technologies, system design, and expert-level problem-solving for industry leaders"
        }
        
        level_description = level_descriptions.get(level, "Appropriate for the role's requirements")

        prompt = f"""
You are a technical interviewer. 
Generate {num_questions} multiple-choice questions (MCQs) for the following role.

Job Title: {job_title}
Skills: {skills_str}
Responsibilities: {resp_str}
Experience: {experience}
Level: {level} - {level_description}

The questions should match the difficulty level:
- Internship: Basic concepts, fundamental knowledge
- Associate: Core skills, simple applications
- Junior: Practical scenarios, common problem-solving
- Senior: Complex scenarios, architecture decisions
- Expert: Advanced concepts, system design, cutting-edge technologies

Each question must have:
- Four options labeled A, B, C, D
- One correct answer clearly indicated as "Correct answer: X"
- Appropriate difficulty for a {level} level candidate

Use this exact format:

1. Question text
A. Option A
B. Option B
C. Option C
D. Option D
Correct answer: A
"""

        api_key = config.get_current_api_key()
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": config.MODEL_NAME,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": getattr(config, "TEMPERATURE", 0.7),
            "max_tokens": 4096
        }

        try:
            response = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers,
                json=data,
                timeout=90
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            return self._parse_questions(content)
        except Exception as e:
            print(f"[ERROR] Fallback generation failed: {e}")
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
                debug_path = os.path.join(config.QUIZ_DATA_DIR, "debug_fallback_raw_output.txt")
                with open(debug_path, "w", encoding="utf-8") as f:
                    f.write(text)
                print(f"[WARNING] Could not parse any questions. Raw output saved to {debug_path}")
            else:
                print("[WARNING] Could not parse any questions.")
            return []

        questions, seen = [], set()
        for q, a, b, c, d, correct in matches:
            q = q.strip()
            if not q or q in seen:
                continue
            seen.add(q)
            questions.append({
                "question": q,
                "options": [
                    {"letter": "A", "text": a.strip()},
                    {"letter": "B", "text": b.strip()},
                    {"letter": "C", "text": c.strip()},
                    {"letter": "D", "text": d.strip()},
                ],
                "correct_answer": correct.strip().upper()
            })
        return questions

    def generate_quiz_from_json(self, job_data: Dict[str, Any], num_questions: int) -> str:
        if AGENT_BASED_AVAILABLE:
            try:
                print("[INFO] Using Agent-based generator...")
                generator = AgentBasedQuizGenerator()
                return generator.generate_quiz(job_data, num_questions)
            except Exception as e:
                print(f"[WARNING] Agent-based failed: {e}\n[INFO] Falling back to direct API...")

        print("[INFO] Using fallback Groq API generator...")
        questions = self.generate_batch_questions(
            job_data.get("job_title", "Unknown"),
            job_data.get("skills_required", {}).get("technical_skills", []),
            job_data.get("job_responsibilities", []),
            job_data.get("experience_required", {}).get("years_of_experience", "Not specified"),
            job_data.get("experience_required", {}).get("level", "Not specified"),
            num_questions
        )

        if not questions:
            raise RuntimeError("No questions generated (agent and fallback both failed).")

        return self._save_quiz(job_data, questions)

    def _save_quiz(self, job_info, questions):
        # Only create directory if it doesn't exist
        if not os.path.exists(config.QUIZ_DATA_DIR):
            os.makedirs(config.QUIZ_DATA_DIR, exist_ok=True)
        
        slug = ''.join(c if c.isalnum() else '_' for c in job_info.get('job_title', 'Unknown Job').lower())
        level = job_info.get("experience_required", {}).get("level", "").lower()
        if level:
            slug += f"_{level}"
        quiz_id = f"quiz_{slug}_{uuid.uuid4().hex[:8]}"
        file_path = os.path.join(config.QUIZ_DATA_DIR, f"{quiz_id}.json")

        # Add metadata including level information
        metadata = {
            "question_count": len(questions),
            "level": job_info.get("experience_required", {}).get("level", "Not specified")
        }

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump({
                "quiz_id": quiz_id,
                "job_info": job_info,
                "metadata": metadata,
                "questions": questions
            }, f, indent=2, ensure_ascii=False)

        print(f"[INFO] Quiz saved at: {file_path}")
        return quiz_id


# =====================================
# 🔹 CLI Entry Point
# =====================================
def main():
    import argparse
    parser = argparse.ArgumentParser(description="Generate technical quiz from job JSON (Agent + Fallback).")
    parser.add_argument("--json", required=True)
    parser.add_argument("--questions", type=int, default=getattr(config, "DEFAULT_NUM_QUESTIONS", 5))
    args = parser.parse_args()

    with open(args.json, "r", encoding="utf-8") as f:
        job_data = json.load(f)

    generator = JobTestGenerator()
    quiz_id = generator.generate_quiz_from_json(job_data, args.questions)
    print(f"[SUCCESS] Quiz generated successfully: {quiz_id}")


if __name__ == "__main__":
    main()