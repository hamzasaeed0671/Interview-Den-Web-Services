# API Documentation

This document describes the FastAPI endpoints available for the Resume and Job Matching System.

## Starting the API Server

To start the API server, run:

```bash
python main.py api
```

By default, the server will start on `http://localhost:8000`. You can access the interactive API documentation at `http://localhost:8000/docs`.

## API Endpoints

### 1. Parse Resume PDF

**Endpoint**: `POST /parse-resume/`

**Description**: Parses a PDF resume and returns structured JSON data.

**Request**:
- Form data with a file upload named `file`

**Response**:
- Structured resume data in JSON format

**Example**:
```bash
curl -X POST "http://localhost:8000/parse-resume/" -H "accept: application/json" -H "Content-Type: multipart/form-data" -F "file=@resume.pdf"
```

### 2. Parse Job Description

**Endpoint**: `POST /parse-job/`

**Description**: Parses job description text and returns structured JSON data.

**Request**:
- JSON body with `job_text` field containing the job description text

**Response**:
- Structured job description data in JSON format

**Example**:
```bash
curl -X POST "http://localhost:8000/parse-job/" -H "accept: application/json" -H "Content-Type: application/json" -d "{\"job_text\": \"Software Engineer with 5 years experience...\"}"
```

### 3. Match Resume and Job

**Endpoint**: `POST /match/`

**Description**: Matches resume and job description data and returns evaluation results.

**Request**:
- JSON body with:
  - `resume_data`: Structured resume data
  - `job_data`: Structured job description data
  - Optional thresholds:
    - `overall_threshold` (default: 70)
    - `skill_threshold` (default: 65)
    - `experience_threshold` (default: 60)

**Response**:
- Match evaluation results in JSON format

**Example**:
```bash
curl -X POST "http://localhost:8000/match/" -H "accept: application/json" -H "Content-Type: application/json" -d "{\"resume_data\": {...}, \"job_data\": {...}}"
```

### 4. Generate Quiz

**Endpoint**: `POST /generate-quiz/`

**Description**: Generates a quiz based on job description data.

**Request**:
- JSON body with:
  - `job_data`: Structured job description data
  - `num_questions`: Number of questions to generate (default: 5)

**Response**:
- Generated quiz data in JSON format

**Example**:
```bash
curl -X POST "http://localhost:8000/generate-quiz/" -H "accept: application/json" -H "Content-Type: application/json" -d "{\"job_data\": {...}, \"num_questions\": 10}"
```

## Command Line Interface

The system also provides a command-line interface with the following commands:

1. **Parse Resume**:
   ```bash
   python main.py parse-resume --resume path/to/resume.pdf [--job path/to/job.txt] [--output path/to/output.json]
   ```

2. **Parse Job**:
   ```bash
   python main.py parse-job --job path/to/job.txt [--output path/to/output.json]
   ```

3. **Match Resume and Job**:
   ```bash
   python main.py match --resume-json path/to/resume.json --job-json path/to/job.json [--output path/to/output.json]
   ```

4. **Generate Quiz**:
   ```bash
   python main.py generate-quiz --job-json path/to/job.json [--questions 5] [--output path/to/output.json]
   ```

5. **Start API Server**:
   ```bash
   python main.py api [--host 0.0.0.0] [--port 8000]
   ```