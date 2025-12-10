# Resume and Job Matching System

This system provides a comprehensive solution for parsing resumes and job descriptions, matching candidates with job requirements, and generating technical quizzes based on job descriptions.

## Features

### Part 1: Resume and Job Description Processing
- Parse PDF resumes and extract structured information
- Parse job description text files and extract structured information
- Match resumes with job descriptions based on skills and experience
- Fraud detection for resumes

### Part 2: Quiz Generation
- Generate technical quizzes based on job descriptions
- Support for different difficulty levels (Internship, Associate, Junior, Senior, Expert)
- Agent-based question generation and validation
- CLI for running and scoring quizzes

### API and Integration
- FastAPI server with RESTful endpoints
- Modular testing framework
- Command-line interface for all functions

## Directory Structure

```
.
├── Part1/                  # Resume parsing and matching
│   ├── data/               # Sample resumes and job descriptions
│   ├── temp/               # Cache and temporary files
│   ├── resume.py           # Resume parsing functionality
│   ├── job_parser.py       # Job description parsing functionality
│   ├── resume_match.py     # Resume-job matching functionality
│   └── ...
├── Part2/                  # Quiz generation
│   ├── QuizData/           # Generated quizzes
│   ├── data/               # Sample job data
│   ├── agent_generator.py  # Agent-based quiz generation
│   ├── test_generator.py   # Quiz generation orchestrator
│   ├── quiz.py             # Quiz running and scoring
│   └── ...
├── api.py                  # FastAPI server implementation
├── main.py                 # Main CLI interface
├── test.py                 # Modular test script
├── test_integration.py     # Integration test script
├── config.py               # Configuration settings
├── requirements.txt        # Python dependencies
├── API_DOCUMENTATION.md    # API usage documentation
├── IMPLEMENTATION_SUMMARY.md # Implementation details
└── ...
```

## Installation

1. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

   Or use the utility script:
   ```bash
   python install_dependencies.py
   ```

## Usage

### Command Line Interface

Parse a resume:
```bash
python main.py parse-resume --resume path/to/resume.pdf [--job path/to/job.txt] [--output output.json]
```

Parse a job description:
```bash
python main.py parse-job --job path/to/job.txt [--output output.json]
```

Match a resume with a job:
```bash
python main.py match --resume-json resume.json --job-json job.json [--output output.json]
```

Generate a quiz:
```bash
python main.py generate-quiz --job-json job.json [--questions 5] [--output quiz.json]
```

Start the API server:
```bash
python main.py api [--host 0.0.0.0] [--port 8000]
```

### API Endpoints

Start the API server and access the interactive documentation at `http://localhost:8000/docs`:

- `POST /parse-resume/` - Parse a PDF resume
- `POST /parse-job/` - Parse job description text
- `POST /match/` - Match resume and job data
- `POST /generate-quiz/` - Generate a quiz based on job data

### Testing

Run modular tests:
```bash
python test.py
```

Run integration tests:
```bash
python test_integration.py
```

## Difficulty Levels

The system supports five difficulty levels for job descriptions and quizzes:
- **Internship**: Entry-level positions for beginners
- **Associate**: Assistant positions for early career professionals
- **Junior**: Roles requiring 1-3 years of experience
- **Senior**: Roles requiring 5+ years of experience
- **Expert**: Principal/staff roles requiring 10+ years of experience

Questions and content are generated appropriately for each level to ensure proper assessment.

## Configuration

API keys and other settings can be configured in `config.py`. The system supports multiple API keys to handle rate limiting.