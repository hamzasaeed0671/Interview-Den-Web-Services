# Job Test Generator

A simple system to generate technical quiz questions for job interviews based on structured job data.

## 🧠 Overview

The Job Test Generator takes structured job information (in JSON format), generates relevant multiple-choice questions using an LLM, and saves them as JSON quiz files. It includes a separate quiz runner for taking the generated quizzes via the command line.

---

## ✨ Features

- **Structured Job Input**: Reads job information from a JSON file, including title, skills, responsibilities, and experience level  
- **Quiz Generation**: Creates multiple-choice questions (MCQs) relevant to job requirements using an LLM  
- **Agent-Based Generation**: Uses two LangChain agents - one to generate questions, another to score and validate them
- **Quiz Storage**: Saves quizzes as JSON files in a `QuizData` directory  
- **Quiz Runner**: CLI tool to run the quizzes and score candidate answers  

---

## 📁 Files

- `config.py`: Configuration settings including API keys, model info, and file paths  
- `test_generator.py`: Generates and saves quizzes based on structured job JSON data  
- `agent_generator.py`: Implements the two LangChain agents for question generation and scoring
- `quiz.py`: Runs the quizzes and shows results to candidates  

---

## 📦 Requirements

- Python 3.6+  
- Required packages listed in the root `requirements.txt`  
- Groq API key (set in `config.py`)  

---

## 🚀 Usage

### 🔧 Generating a Quiz

Use `test_generator.py` to generate a quiz from structured job data:

```bash
python test_generator.py --json ./data/latest_job.json --questions 10
```

This will:

1. Read the job data from the specified JSON file  
2. Generate multiple-choice questions using two LangChain agents  
3. Save the quiz to a JSON file in the `QuizData` directory  

---

### 🧪 Running a Quiz

Use `quiz.py` to list available quizzes or run a specific quiz:

```bash
# List all available quizzes
python quiz.py list

# Run a specific quiz (replace QUIZ_ID with an actual quiz ID)
python quiz.py run QUIZ_ID
```

---

## ⚙️ Configuration

You can customize the following settings in the root `config.py`:

- `QUIZ_DATA_DIR`: Directory to store quiz JSON files  
- `GROQ_API_KEY`: Your Groq API key for LLM calls  
- `MODEL_NAME`: LLM model to use (e.g., `moonshotai/kimi-k2-instruct-0905`)  
- `TEMPERATURE`: Temperature setting for LLM (e.g., 0.2)  
- `DEFAULT_NUM_QUESTIONS`: Default number of questions per quiz  

---

## 🧾 Example

1. Create a structured job JSON file like `data/latest_job.json` with fields like:
    - `job_title`
    - `skills_required`
    - `job_responsibilities`
    - `experience_required`
2. Run:

```bash
python test_generator.py --json ./data/latest_job.json
```

3. Run:

```bash
python quiz.py list
```

4. Run:

```bash
python quiz.py run QUIZ_ID
```

---

## 🤖 How It Works

1. The system reads job data from a structured JSON file  
2. It uses two LangChain agents with the Kimi model:
   - Agent 1 generates questions focused on commonly known technologies
   - Agent 2 scores and validates questions for quality and relevance
3. The questions are saved in JSON format  
4. The quiz runner loads the JSON and presents it to the candidate  
5. After completion, it scores the answers and shows results  

---