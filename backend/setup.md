# 🛠️ Local Setup Guide — KnowledgeHub AI

Follow these instructions to run KnowledgeHub AI on your local machine.

## 1. Prerequisites

Install the following:

- Python 3.10+
- Node.js 18+
- npm
- Git
- A Supabase project
- A Google Gemini API key

## 2. Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/knowledgehub-ai.git
cd knowledgehub-ai
```

Replace `YOUR_USERNAME` with your GitHub username.

## 3. Backend Setup

Navigate to the backend:

```bash
cd backend
```

Create and activate a virtual environment.

**Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**Linux / macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

### Configure Environment Variables

Create a `.env` file inside the `backend/` directory using `.env.example` as a reference.

Add your own credentials:

```env
SUPABASE_URL=your_supabase_project_url
SUPABASE_KEY=your_supabase_publishable_key
SUPABASE_SECRET_KEY=your_supabase_secret_key
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=your_gemini_model
```

Never commit your actual `.env` file or expose your API keys.

### Start the Backend

From the `backend/` directory, run:

```bash
uvicorn app.main:app --reload
```

The background document-processing worker starts automatically with the backend.

Backend API: `http://127.0.0.1:8000`

API documentation: `http://127.0.0.1:8000/docs`

## 4. Frontend Setup

Open a new terminal and navigate to the frontend:

```bash
cd frontend
```

Install dependencies:

```bash
npm install
```

Create a `.env.local` file inside `frontend/`:

```env
NEXT_PUBLIC_SUPABASE_URL=your_supabase_project_url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_publishable_key
```

Use your own Supabase project credentials.

Start the development server:

```bash
npm run dev
```

Frontend: `http://localhost:3000`

## 5. Supabase Configuration

Before using the application:

- Configure your Supabase project.
- Set up the required database tables, functions and pgvector extension.
- Configure Row Level Security (RLS) policies.
- Create the required private document storage bucket.

The application depends on the database schema, RPC functions, storage configuration and security policies expected by the backend.

## 6. You're Ready! 🎉

Open `http://localhost:3000` to access KnowledgeHub AI.

Register an account, upload a PDF or DOCX document, and start asking questions about your documents.

**Note:** Keep your API keys and Supabase credentials private. Never disable security policies or commit secrets to GitHub.
