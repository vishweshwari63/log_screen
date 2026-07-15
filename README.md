# 💊 CopilotCRM – Enterprise Pharmaceutical CRM

An AI-powered Pharmaceutical Customer Relationship Management (CRM) application designed to streamline physician interactions, automate call reporting, and provide intelligent insights using AI agents and workflow orchestration.

---

## 🚀 Features

- 👨‍⚕️ HCP (Healthcare Professional) Directory
- 📋 Physician Interaction Logging
- 🤖 AI Chat Detailing Assistant
- 📊 AI-Generated Meeting Insights
- ❤️ Sentiment Analysis
- 🔄 CRM Synchronization
- 📜 LangGraph Execution Trace Visualization
- ✅ HIPAA Consent Tracking
- 📝 Automated Call Summary Generation
- 🔍 Search & Filter Physicians
- 📈 CRM Timeline Tracking

---

## 🏗️ Architecture

```
Frontend (React + Vite)
        │
 REST API / WebSocket
        │
Backend (FastAPI)
        │
 LangGraph AI Agent
        │
 SQLite / PostgreSQL
```

---

## 🛠️ Tech Stack

### Frontend

- React.js
- Vite
- Tailwind CSS
- Redux Toolkit

### Backend

- FastAPI
- Python
- SQLAlchemy
- Alembic

### AI

- LangGraph
- LangChain
- OpenAI Compatible LLM
- Custom AI Tools

### Database

- SQLite (Development)
- PostgreSQL (Production Ready)

---

## 🤖 AI Workflow

The application uses LangGraph to execute AI-assisted CRM operations.

Workflow:

1. Understand Request
2. Execution Planner
3. Tool Dispatcher
4. Execute Tool Node
5. CRM Synchronization
6. Context Summary
7. Audit Trail Persistence
8. Complete Phase

---

## 📁 Project Structure

```
CopilotCRM
│
├── frontend
│   ├── src
│   ├── public
│   └── package.json
│
├── backend
│   ├── app
│   │   ├── agent
│   │   ├── models
│   │   ├── database.py
│   │   └── main.py
│   │
│   ├── alembic
│   └── requirements.txt
│
└── docker-compose.yml
```

---

## ⚙️ Installation

### Clone Repository

```bash
git clone https://github.com/vishweshwari63/log_screen.git
cd log_screen
```

### Backend

```bash
cd backend

python -m venv venv

venv\Scripts\activate

pip install -r requirements.txt

alembic upgrade head

python app/seed.py

uvicorn app.main:app --reload
```

Backend runs on

```
http://localhost:8000
```

---

### Frontend

```bash
cd frontend

npm install

npm run dev
```

Frontend runs on

```
http://localhost:5173
```

---

## 📸 Screenshots

Add screenshots of:

- Dashboard
- HCP Directory
- AI Chat Detailing
- CRM Timeline
- AI Insights
- LangGraph Execution Trace

---

## 🧪 Demo Workflow

1. Select a physician.
2. Enter discussion details.
3. Record products discussed.
4. Capture objections and call outcome.
5. Acquire physician consent.
6. Synchronize CRM.
7. View AI-generated insights.
8. Review LangGraph execution trace.

---

## 🌟 Key Highlights

- Enterprise-style Pharmaceutical CRM
- AI-assisted physician detailing
- Automated interaction summaries
- Real-time workflow visualization
- HIPAA compliance tracking
- Modular FastAPI architecture
- Responsive React interface

---

## 📌 Future Enhancements

- Role-Based Access Control (RBAC)
- Multi-user authentication
- Voice-to-Text call logging
- PDF report generation
- Email follow-up automation
- Analytics dashboard
- Docker deployment
- CI/CD pipeline
- Cloud deployment (AWS/Azure)

---

## 👩‍💻 Author

**Vishweshwari R**

B.E. Computer Science and Engineering

Full Stack Developer | AI Enthusiast

GitHub: https://github.com/vishweshwari63

LinkedIn: https://www.linkedin.com/

---

## 📄 License

This project is intended for educational and portfolio purposes.
