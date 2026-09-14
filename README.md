# HireReady

HireReady is an AI-powered interview preparation web application for Computer Science students. It helps students practice core CS subjects, ask doubts to subject-specific AI agents, take mock interviews, and track their weak topics over time.

## Overview

HireReady is built as a Flask web app with a SQLite database. The platform focuses on placement preparation for four major CS interview subjects:

- Data Structures and Algorithms
- Database Management Systems
- Operating Systems
- Computer Networks

Students can chat with dedicated AI tutor agents, generate mock interviews, receive answer scores and feedback, and view a progress dashboard based on their recent doubts and interview performance.

## Features

- User signup and login
- Secure password hashing using Flask-Bcrypt
- Forgot password and reset password flow
- Guest demo login with sample dashboard data
- Subject-specific AI tutor agents
- AI chat for DSA, DBMS, OS, and CN
- Off-topic detection for subject agents
- Doubt tracking with topic tagging
- AI-generated mock interview questions
- AI evaluation of interview answers
- Score, feedback, and model answer for each response
- Weak-topic-based interview mode
- Dashboard with weekly learning stats
- Progress report with activity, scores, weak topics, and topic strengths
- Local SQLite database using SQLAlchemy

## Tech Stack

- Python
- Flask
- Flask-SQLAlchemy
- SQLite
- Flask-Bcrypt
- Groq API
- HTML
- CSS
- JavaScript
- Jinja2 templates

## Project Structure

```text
HireReady/
├── app.py
├── agents.py
├── interview_api.py
├── README.md
├── backend/
│   ├── __init__.py
│   ├── auth.py
│   ├── controller.py
│   └── routes.py
├── database/
│   ├── __init__.py
│   ├── extensions.py
│   ├── models.py
│   ├── queries.py
│   └── hireready.db
├── static/
│   ├── css/
│   ├── images/
│   └── js/
└── templates/
    ├── Index.html
    ├── login.html
    ├── dashboard.html
    ├── dsa.html
    ├── dbms.html
    ├── os.html
    ├── cn.html
    ├── interview.html
    ├── progress.html
    ├── forgot_password.html
    └── reset_password.html
```

## Installation

1. Clone or download the project.

2. Move into the project directory.

```bash
cd HireReady
```

3. Create a virtual environment.

```bash
python -m venv venv
```

4. Activate the virtual environment.

On Windows:

```bash
venv\Scripts\activate
```

On macOS/Linux:

```bash
source venv/bin/activate
```

5. Install dependencies.

```bash
pip install -r requirements.txt
```

## Environment Variables

Create a `.env` file in the project root.

## Running The Project

Start the Flask development server:

```bash
python app.py
```

Open the app in your browser:

```text
http://localhost:5000
```

## Main Pages

| Route        | Description                |
| ---          | ---                        |
| `/`          | Landing page               |
| `/login`     | Login and signup page      |
| `/dashboard` | Student dashboard          |
| `/dsa`       | DSA AI tutor               |
| `/dbms`      | DBMS AI tutor              |
| `/os`        | Operating Systems AI tutor |
| `/cn`        | Computer Networks AI tutor |
| `/interview` | Mock interview page        |
| `/progress`  | Progress report page       |

## API Endpoints

| Method | Endpoint                  | Description                            |
| ---    | ---                       | ---                                    |
| `POST` | `/auth/login`             | Log in a user                          |
| `POST` | `/auth/signup`            | Register a new user                    |
| `POST` | `/auth/guest`             | Start a guest demo session             |
| `GET`  | `/logout`                 | Log out the current user               |
| `POST` | `/api/chat`               | Send a message to a subject AI agent   |
| `POST` | `/api/interview/start`    | Create a mock interview session        |
| `POST` | `/api/interview/generate` | Generate interview questions           |
| `POST` | `/api/interview/evaluate` | Evaluate an interview answer           |
| `POST` | `/api/interview/complete` | Complete and save an interview session |
| `GET`  | `/api/progress`           | Fetch progress report data             |

## Database Models

The application uses SQLAlchemy models stored in `database/models.py`.

- `User`: stores user account details
- `Doubt`: stores student questions and AI answers
- `TopicStrength`: tracks topic-level learning strength
- `InterviewSession`: stores mock interview sessions
- `Question`: stores interview questions, answers, scores, and feedback

## How It Works

1. The student signs up, logs in, or uses guest mode.
2. The student asks doubts to one of the subject AI agents.
3. The app stores each doubt and updates the related topic strength.
4. The student can start a mock interview based on selected subjects, difficulty, and interview type.
5. The AI generates questions and evaluates the student's answers.
6. Scores and feedback are saved to the database.
7. The dashboard and progress page show weak topics, recent doubts, interview performance, and study activity.

## AI Integration

HireReady uses the Groq API for AI-powered features:

- Subject tutor responses
- Interview question generation
- Interview answer evaluation
- Constructive feedback and model answers

If AI question generation fails, the app uses built-in fallback questions so the mock interview flow can still continue.

## Security Notes

- User passwords are stored as bcrypt hashes.
- Flask sessions are used for authentication.
- Password reset tokens are generated securely.
- In the current development version, reset tokens are stored in memory.
- For production, password reset tokens should be moved to a database table.
- API keys and secret keys should be stored in `.env` and never committed to version control.

## Future Improvements

- Add email sending through Flask-Mail or SendGrid
- Improve AI usage limits and error handling
- Add admin analytics
- Deploy the app on a production server
- Improve accessibility and responsive design

## Author
- Riya Gupta
- Ritesh Agrawal
