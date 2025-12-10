#!/usr/bin/env python3
import os
import json
import argparse
from typing import Dict, List, Any
from config import QUIZ_DATA_DIR

class QuizRunner:
    """
    Simple quiz runner to load and run quizzes from JSON files.
    """
    
    def __init__(self):
        """Initialize the quiz runner."""
        if not os.path.exists(QUIZ_DATA_DIR):
            os.makedirs(QUIZ_DATA_DIR)
    
    def load_quiz(self, quiz_id: str) -> Dict[str, Any]:
        """
        Load a quiz from a JSON file.
        
        Args:
            quiz_id: The ID of the quiz to load
            
        Returns:
            The quiz data
        """
        file_path = os.path.join(QUIZ_DATA_DIR, f"{quiz_id}.json")
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Quiz with ID {quiz_id} not found.")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            quiz_data = json.load(f)
        
        return quiz_data
    
    def format_quiz_for_candidate(self, quiz_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format the quiz for candidate display (without correct answers).
        
        Args:
            quiz_data: The full quiz data
            
        Returns:
            Quiz data formatted for candidate display
        """
        candidate_quiz = {
            'quiz_id': quiz_data.get('quiz_id'),
            'job_title': quiz_data.get('job_info', {}).get('job_title', 'Unknown Job'),
            'questions': []
        }
        
        # Format questions without including the correct answers
        for i, q in enumerate(quiz_data.get('questions', [])):
            candidate_question = {
                'question_id': i + 1,
                'question': q.get('question'),
                'options': []
            }
            
            # Add options without marking correct answer
            for option in q.get('options', []):
                candidate_question['options'].append({
                    'letter': option.get('letter'),
                    'text': option.get('text')
                })
            
            candidate_quiz['questions'].append(candidate_question)
        
        return candidate_quiz
    
    def score_quiz(self, quiz_id: str, candidate_answers: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Score a completed quiz.
        
        Args:
            quiz_id: The ID of the quiz
            candidate_answers: List of candidate answers
            
        Returns:
            Quiz result data
        """
        # FIRST GENERATE - Load the quiz data
        quiz_data = self.load_quiz(quiz_id)
        questions = quiz_data.get('questions', [])
        
        # THEN CHECK - Create a dictionary mapping question IDs to correct answers
        correct_answers = {}
        for i, q in enumerate(questions):
            correct_answers[i + 1] = q.get('correct_answer')
        
        # THEN CHECK - Score the answers
        total_questions = len(questions)
        correct_count = 0
        question_results = []
        
        for answer in candidate_answers:
            question_id = answer.get('question_id')
            candidate_answer = answer.get('answer')
            
            # CONDITION IF DISLIKED THEN REMOVED - Skip if question ID is invalid
            if question_id not in correct_answers:
                continue
            
            is_correct = candidate_answer == correct_answers[question_id]
            
            question_results.append({
                'question_id': question_id,
                'candidate_answer': candidate_answer,
                'correct_answer': correct_answers[question_id],
                'is_correct': is_correct
            })
            
            if is_correct:
                correct_count += 1
        
        # CONDITION TO FILL GAP - Calculate score
        score_percentage = (correct_count / total_questions) * 100 if total_questions > 0 else 0
        
        # FINALLY RECHECK - Create result object
        result = {
            'quiz_id': quiz_id,
            'total_questions': total_questions,
            'correct_answers': correct_count,
            'score_percentage': round(score_percentage, 2),
            'question_results': question_results
        }
        
        return result
    
    def run_quiz(self, quiz_id: str):
        """
        Run a quiz in the terminal.
        
        Args:
            quiz_id: The ID of the quiz to run
        """
        # FIRST GENERATE - Load the quiz data
        quiz_data = self.load_quiz(quiz_id)
        
        # THEN CHECK - Format for candidate
        candidate_quiz = self.format_quiz_for_candidate(quiz_data)
        
        print(f"\n===== QUIZ: {candidate_quiz.get('job_title')} =====\n")
        
        # THEN CHECK - Collect answers
        answers = []
        for q in candidate_quiz.get('questions', []):
            question_id = q.get('question_id')
            print(f"\nQ{question_id}: {q.get('question')}")
            
            for option in q.get('options', []):
                print(f"{option.get('letter')}. {option.get('text')}")
            
            # CONDITION IF DISLIKED THEN REMOVED - Get answer with validation
            while True:
                answer = input("\nYour answer (A/B/C/D): ").strip().upper()
                if answer in ['A', 'B', 'C', 'D']:
                    break
                print("Invalid input. Please enter A, B, C, or D.")
            
            answers.append({
                'question_id': question_id,
                'answer': answer
            })
        
        # CONDITION TO FILL GAP - Score quiz
        results = self.score_quiz(quiz_id, answers)
        
        # FINALLY RECHECK - Display results
        print("\n===== QUIZ RESULTS =====")
        print(f"Score: {results.get('correct_answers')}/{results.get('total_questions')} ({results.get('score_percentage')}%)")
        
        print("\nDetailed Results:")
        for result in results.get('question_results', []):
            status = "✓" if result.get('is_correct') else "✗"
            print(f"Q{result.get('question_id')}: {status} Your answer: {result.get('candidate_answer')}, Correct: {result.get('correct_answer')}")
    
    def list_quizzes(self):
        """List all available quizzes."""
        quizzes = []
        
        # FIRST GENERATE - Look through all quiz files
        for filename in os.listdir(QUIZ_DATA_DIR):
            if filename.endswith('.json'):
                file_path = os.path.join(QUIZ_DATA_DIR, filename)
                
                try:
                    # THEN CHECK - Load each quiz file
                    with open(file_path, 'r', encoding='utf-8') as f:
                        quiz_data = json.load(f)
                    
                    # CONDITION IF DISLIKED THEN REMOVED - Extract summary information
                    quiz_summary = {
                        'quiz_id': quiz_data.get('quiz_id'),
                        'job_title': quiz_data.get('job_info', {}).get('job_title', 'Unknown'),
                        'question_count': quiz_data.get('metadata', {}).get('question_count', 0)
                    }
                    
                    quizzes.append(quiz_summary)
                except Exception as e:
                    print(f"Error loading quiz {filename}: {e}")
        
        # CONDITION TO FILL GAP - Check if any quizzes were found
        if not quizzes:
            print("No quizzes available.")
            return
        
        # FINALLY RECHECK - Display all available quizzes
        print("\n===== AVAILABLE QUIZZES =====")
        for i, quiz in enumerate(quizzes):
            print(f"{i+1}. ID: {quiz.get('quiz_id')}")
            print(f"   Job: {quiz.get('job_title')}")
            print(f"   Questions: {quiz.get('question_count')}")
            print()
        
        return quizzes

def main():
    """Main function to run the quiz."""
    parser = argparse.ArgumentParser(description='Job Test Quiz Runner')
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # List command
    subparsers.add_parser('list', help='List available quizzes')
    
    # Run command
    run_parser = subparsers.add_parser('run', help='Run a quiz')
    run_parser.add_argument('quiz_id', help='ID of the quiz to run')
    
    args = parser.parse_args()
    
    runner = QuizRunner()
    
    # FIRST GENERATE - Determine which command to run
    if args.command == 'list':
        # THEN CHECK - List quizzes
        runner.list_quizzes()
    
    elif args.command == 'run':
        # FINALLY RECHECK - Run specific quiz
        runner.run_quiz(args.quiz_id)
    
    else:
        parser.print_help()

if __name__ == "__main__":
    main()