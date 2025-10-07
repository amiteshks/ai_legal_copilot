# ⚖️ AI Legal Copilot

AI Legal Copilot is an intelligent system designed to help law firms and legal teams extract **deadlines, obligations, and events** from legal documents.  
It automates docketing, calendaring, and notifications while maintaining **trust, compliance, and human-in-the-loop validation**.

---

## Features
- Upload and process legal documents in PDF format.
- Extract **dates, deadlines, obligations, and events** using LLMs.
- Add events directly to **calendars** via API integration.
- Receive **notifications** via multiple channels (email, Slack, etc.).
- Store structured results in a **Legal Copilot Database** for future reference.
- Confidence scoring + human-in-the-loop validation for edge cases.

---

## Technical Architecture
**Layers:**
- **Frontend (React)** – File upload, results review, interactive UI.
- **Backend (FastAPI, Python)** – Microservices providing REST APIs:
  - `/api/extract` → Extracts legal information from uploaded documents.
  - `/api/calendar` → Adds extracted deadlines as calendar events.
  - `/api/notifications` → Sends reminders and alerts.
- **LLM Layer** – Supports **OpenAI models** (current demo) and **local LLMs (Llama 3.2)**.
- **Legal Copilot Database** – Persists extracted structured data.

---

## Data Pipeline
1. **Document Ingestion** → Upload PDF.  
2. **Preprocessing** → Text extraction.  
3. **LLM Processing** → Extract obligations, dates, events (JSON output).  
4. **Validation Layer** → Apply rule-based calendaring logic.  
5. **Confidence Scoring** → Assign reliability; escalate uncertain cases to humans.  
6. **Storage & Integration** → Save in DB, push to calendars & notification systems.

---

## Confidence Scoring
- Combines:
  - LLM certainty signals
  - Multiple prompt consistency
  - Rule-based validation
  - Cross-document checks  
- Thresholds determine auto-commit vs human review.

---

## Getting Started

### 1. Clone the repo
```bash
git clone https://github.com/your-org/ai-legal-copilot.git
cd ai-legal-copilot
```

### 2. Start the Backend with Docker
Make sure you have **Docker** and **Docker Compose** installed.

```bash
cd backend
docker-compose up --build
```

Backend will be available at: [http://localhost:8000](http://localhost:8000)

### 3. Start the Frontend
In another terminal:

```bash
cd frontend
npm install
npm start
```

Frontend will be available at: [http://localhost:3000](http://localhost:3000)

---

## Useful Commands
- Stop containers:  
  ```bash
  docker-compose down
  ```
- Rebuild after code changes:  
  ```bash
  docker-compose up --build
  ```
- View logs:  
  ```bash
  docker-compose logs -f
  ```

---

## Project Structure
```
ai-legal-copilot/
│── backend/             # FastAPI microservices
│   ├── app/
│   ├── tests/
│   └── requirements.txt
│── frontend/            # React frontend
│── docs/                # Documentation & diagrams
│── README.md
```
