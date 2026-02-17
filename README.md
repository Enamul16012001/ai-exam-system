# AI Exam System

An AI-powered examination platform built with FastAPI. Admins create exams with AI-generated questions (via Google Gemini), candidates take exams through a web interface, and answers are evaluated automatically.

## Prerequisites

- Python 3.10+
- A Google AI (Gemini) API key — get one at https://aistudio.google.com/apikey

## Setup

### 1. Clone and install

```bash
git clone -b v2 --single-branch https://github.com/Enamul16012001/ai-exam-system.git
cd ai-exam-system
```

Create a virtual environment:

```bash
# Linux/macOS
python3 -m venv .venv
source .venv/bin/activate

# Windows
python -m venv .venv
.venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

### 2. Configure environment

Copy the example file and fill in your values:

```bash
cp .env.example .env
```

Edit `.env`:

```env
API_KEY="your_gemini_api_key"
API_KEY_BACKUP="optional_backup_key"
ADMIN_SECRET_KEY="your_admin_password"
HOST=0.0.0.0
PORT=8000
```

`ADMIN_SECRET_KEY` is the password used to log into the admin panel.

### 3. Run

```bash
# Linux/macOS
python3 main.py

# Windows
python main.py
```

The server starts at `http://localhost:8000` (or whatever `PORT` you set).

## Usage

### Admin workflow

1. Go to `/admin` and log in with your `ADMIN_SECRET_KEY`
2. Create a new exam — set the topic, department, sections, and question counts
3. The system uses Gemini AI to generate questions (MCQ, short answer, essay)
4. Review and edit generated questions, optionally attach images
5. Finalize the exam to get a shareable candidate link
6. Monitor live candidates and view results from the dashboard

### Candidate workflow

1. Open the exam link shared by the admin
2. Enter name and candidate ID, then start the exam
3. Answer all questions within the time limit
4. Submit — answers are saved immediately and evaluated in the background
5. View results once evaluation completes (if enabled by admin)

## Docker

```bash
docker compose up --build -d
```

Default port in Docker is `7894`. Change it by setting `PORT` in your `.env` file.

View logs:

```bash
docker compose logs -f
```