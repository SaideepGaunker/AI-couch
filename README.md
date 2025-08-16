# Interview Prep AI Coach

A comprehensive AI-powered interview preparation platform that helps job seekers, students, and career switchers master their interview skills through realistic simulations, personalized feedback, and progress tracking.

## Features

- **Realistic Interview Simulations**: Practice with AI-generated questions for HR and technical rounds
- **Body Language Analysis**: Real-time feedback on posture, eye contact, and facial expressions using computer vision
- **Tone & Confidence Scoring**: Voice analysis for improved vocal delivery and confidence
- **Role-Specific Questions**: Tailored question sets for different industries and roles
- **Progress Tracking**: Comprehensive analytics and improvement trends
- **Institutional Dashboard**: Administrative tools for placement cells and educational institutions
- **LinkedIn Integration**: Import profile data and practice for specific job applications

## Technology Stack

### Backend
- **Framework**: Python FastAPI
- **Database**: MySQL with SQLAlchemy ORM
- **Authentication**: JWT with bcrypt password hashing
- **AI Services**: 
  - Gemini API for question generation and answer evaluation
  - HuggingFace models for body language detection
  - pyAudioAnalysis for tone and confidence analysis

### Frontend
- **Framework**: AngularJS
- **UI**: Bootstrap 5 with responsive design
- **Real-time**: WebSocket communication for live feedback

## Project Structure

```
interview-prep-ai-coach/
├── backend/
│   ├── app/
│   │   ├── api/v1/endpoints/    # API endpoints
│   │   ├── core/                # Configuration
│   │   ├── db/                  # Database models
│   │   └── services/            # Business logic
│   ├── main.py                  # FastAPI application
│   └── requirements.txt         # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── js/                  # AngularJS controllers and services
│   │   ├── views/               # HTML templates
│   │   ├── styles/              # CSS files
│   │   └── index.html           # Main HTML file
│   └── package.json             # Node.js dependencies
└── README.md
```

## 🚀 Quick Start

#### Prerequisites
- Python 3.8+
- Node.js 14+
- MySQL 8.0+
- Git

#### Backend Setup

1. **Start Backend Server**
   ```bash
   cd backend
   uvicorn main:app --reload --host 0.0.0.0 --port 8000

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Database Setup**
   ```sql
   # Create MySQL database
   CREATE DATABASE interview_prep_db;
   ```

4. **Check the database connection**
   ```bash
   python setup_database.py
   ```

#### Frontend Setup

1. **Install Dependencies**
   ```bash
   cd frontend
   npm install
   ```

2. **Start Development Server**
   ```bash
   npm start
   ```

### 🌐 Access the Application

- **Frontend**: http://localhost:4200
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

### 🔑 Required API Keys

1. **Gemini API Key**: Get from [Google AI Studio](https://makersuite.google.com/app/apikey)

Add these to your `.env` file:
```env
GEMINI_API_KEY=your-gemini-api-key
```

## API Endpoints

### Authentication
- `POST /api/v1/auth/login` - User login
- `POST /api/v1/auth/register` - User registration
- `POST /api/v1/auth/logout` - User logout
- `POST /api/v1/auth/refresh` - Refresh access token

### Interview Management
- `POST /api/v1/interviews/start` - Start interview session
- `GET /api/v1/interviews/{session_id}` - Get session details
- `PUT /api/v1/interviews/{session_id}/pause` - Pause session
- `PUT /api/v1/interviews/{session_id}/complete` - Complete session

### Questions & Feedback
- `POST /api/v1/questions/generate` - Generate AI questions
- `POST /api/v1/feedback/analyze` - Analyze user answers
- `GET /api/v1/analytics/progress` - Get user progress

## Development

### Running Tests
```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
npm test
```

### Database Migrations
```bash
# Create new migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head
```

## Configuration

### Required Environment Variables

- `DATABASE_URL`: MySQL connection string
- `SECRET_KEY`: JWT secret key
- `GEMINI_API_KEY`: Google Gemini API key
- `MAIL_USERNAME`: Email service username
- `MAIL_PASSWORD`: Email service password

