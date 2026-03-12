# README — University AI Agent Platform

## 🚀 Quick Start

### Prerequisites
- Python 3.12+
- Node.js 18+

### 1. Backend (Django)

```bash
cd Hackathon/backend
../venv/Scripts/python.exe manage.py runserver 8000
```

The API will be available at **http://localhost:8000/api/**

### 2. Frontend (React + Vite)

```bash
cd Hackathon/frontend
npm run dev
```

The UI will be available at **http://localhost:5174**

---

## 🔑 Demo Login Credentials

| Role   | Email                  | Password   |
|--------|------------------------|------------|
| Admin  | admin@college.edu      | admin123   |
| Mentor | mentor@college.edu     | mentor123  |

---

## 🏗️ Project Structure

```
Hackathon/
├── backend/              # Django REST API
│   ├── core/             # Django project settings & URLs
│   ├── users/            # Custom user model + auth
│   ├── students/         # Student CRUD
│   ├── faculty/          # Faculty + assignments
│   ├── courses/          # Course catalog
│   ├── attendance/       # Attendance tracking
│   ├── exams/            # Exam scheduling + results
│   ├── analytics/        # Reports & trends (read-only)
│   ├── student_warnings/ # Risk calculation + alert triggers
│   ├── scholarships/     # Scheme eligibility
│   ├── letters/          # PDF letter generation
│   └── agents/           # Agent factory, router, seed_demo cmd
└── frontend/             # React + Vite + TailwindCSS
    └── src/
        ├── context/      # AuthContext
        ├── services/     # Axios API client
        ├── layout/       # Sidebar & main layout
        └── pages/        # Login, Dashboard, AgentFactory, Chat
```

---

## 🤖 8 Pre-built Agents (seeded)

| # | Agent                   | Domain        |
|---|-------------------------|---------------|
| 1 | Student Management Agent | student       |
| 2 | Attendance Warning Agent | attendance    |
| 3 | Exam Scheduler Agent    | exam          |
| 4 | Scholarship Agent       | scholarship   |
| 5 | Letter Generation Agent | letter        |
| 6 | Analytics Agent         | analytics     |

---

## 📡 Key API Endpoints

| Method | Endpoint                              | Description                    |
|--------|---------------------------------------|--------------------------------|
| POST   | `/api/auth/login/`                    | Email/password login           |
| GET    | `/api/students/`                      | List students (`?dept=CS`)     |
| POST   | `/api/attendance/mark/`               | Mark attendance                |
| GET    | `/api/attendance/low/?threshold=75`   | Low attendance students        |
| GET    | `/api/warnings/student/{roll}/`       | Risk level + days needed       |
| GET    | `/api/scholarships/eligible/{roll}/`  | Eligible scholarship schemes   |
| POST   | `/api/letters/generate/`              | Generate PDF letter            |
| GET    | `/api/analytics/pass-rate/?dept=CS`   | Pass/fail stats                |
| POST   | `/api/agents/{id}/chat/`              | Chat with an agent             |

---

## 🌱 Seeding Demo Data

```bash
cd backend
set PYTHONIOENCODING=utf-8
../venv/Scripts/python.exe manage.py seed_demo
```

This creates: 2 users, 3 students, 3 courses, 2 faculty, attendance records, 3 scholarship schemes, 6 agents.

---

## 🔑 Environment Variables

Create a `.env` in `backend/`:

```
DJANGO_SECRET_KEY=your-secret-key
TWILIO_ACCOUNT_SID=your-sid
TWILIO_AUTH_TOKEN=your-token
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886
RESEND_API_KEY=your-resend-key
```
