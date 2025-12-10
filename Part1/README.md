# Resume and Job Description Parser

This application extracts information from PDF resumes and text job descriptions, transforming them into structured JSON formats using LLM processing.

## Features

- Resume Parsing:
  - Extracts text from PDF resumes using PyMuPDF (fitz)
  - Infers additional relevant skills from the resume content and job description
  - Outputs a structured JSON file with the resume information

- Job Description Parsing:
  - Reads job descriptions from text files
  - Structures the job description into a clean JSON format
  - Organizes job requirements, responsibilities, and skill requirements

## Installation

1. Clone this repository
2. Install the required dependencies:

```bash
pip install -r requirements.txt
```

3. Set your Groq API key in the `config.py` file:

```python
# In config.py
GROQ_API_KEY = "your_groq_api_key_here"  # Replace with your actual API key
```

## Usage

The application provides two command styles: subcommand style and legacy style.

### Subcommand Style

#### Resume Parsing

```bash
python main.py resume -r path/to/resume.pdf -j path/to/job_description.txt
```

#### Job Description Parsing

```bash
python main.py job -j path/to/job_description.txt
```

#### Process Both Resume and Job Description

```bash
python main.py both -r path/to/resume.pdf -j path/to/job_description.txt
```

### Legacy Style (Backward Compatible)

```bash
# Resume parsing (default mode)
python main.py -r path/to/resume.pdf -j path/to/job_description.txt

# Job description parsing
python main.py -m job -j path/to/job_description.txt

# Process both resume and job description
python main.py -m both -r path/to/resume.pdf -j path/to/job_description.txt
```

If no command or mode is specified, the application defaults to resume parsing.

Command line arguments:
- `-r`, `--resume`: Path to the resume PDF file (default: defined in config.py)
- `-j`, `--job`: Path to the job description text file (default: defined in config.py)
- `-o`, `--output`: Custom output path for the JSON file
- `-d`, `--output-dir`: Output directory for JSON files (default: output)
- `-m`, `--mode`: Processing mode in legacy style: resume, job, or both (default: resume)

## Configuration

The application uses a configuration file (`config.py`) to store settings:

```python
# Groq API key
GROQ_API_KEY = "your_groq_api_key_here"

# Model settings
MODEL_NAME = "llama3-70b-8192"
TEMPERATURE = 0.2

# File paths
DEFAULT_RESUME_PATH = "data/Asad.pdf"
DEFAULT_JOB_DESCRIPTION_PATH = "data/JobDescription.txt"
```

You can modify these settings to change the default behavior of the application.

## Output Formats

### Resume JSON Format

```json
{
  "Name": "",
  "Contact": {
    "Email": "",
    "Number": ""
  },
  "Experience": {
    "Total Years": 0,
    "Experiences": []
  },
  "Education": [],
  "Skills": [],
  "Languages": [],
  "Projects": [],
  "Certifications": [],
  "Awards": []
}
```

### Job Description JSON Format

```json
{
  "job_title": "The title of the job",
  "role_description": "Summary of tasks and responsibilities",
  "experience_required": {
    "years_of_experience": "Number of years of experience required"
  },
  "skills_required": {
    "technical_skills": [
      "List of programming languages, tools, or frameworks required"
    ],
    "soft_skills": [
      "List of soft skills required"
    ]
  },
  "preferred_skills": [
    "List of optional skills that can enhance your chances"
  ],
  "job_responsibilities": [
    "Task 1",
    "Task 2",
    "Task 3"
  ]
}
```

## Technical Details

The application uses:
- **PyMuPDF (fitz)**: For efficient PDF text extraction
- **Groq API**: To access the Llama3-70b-8192 model
- **Requests**: To communicate with the Groq API

## Skills Inference

One of the key features is the ability to infer skills that are implied but not explicitly mentioned in the resume. The application will:

- Add skills that are reasonably suggested by the resume's experiences, projects, or overall focus
- Only include inferred skills that are related to the content
- Avoid adding completely unrelated or hallucinated skills
- Highlight skills that are particularly relevant to the provided job description 