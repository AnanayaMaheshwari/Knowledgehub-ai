# 🚀 KnowledgeHub AI

### Your Documents. Your Knowledge. One AI Assistant.

KnowledgeHub AI is an AI-powered document intelligence platform that lets users upload documents, ask questions in natural language, and receive context-aware answers using **Retrieval-Augmented Generation (RAG)**.

Turn lengthy documents into an interactive knowledge base and find the information you need through simple conversations.

## ✨ Features

- 📄 **Document Management** – Upload, view, process, retry, and delete PDF and DOCX documents.
- 🧠 **AI-Powered RAG** – Retrieve relevant document content and generate context-aware answers.
- 🔍 **Semantic Search** – Find relevant information using vector embeddings and similarity search.
- 💬 **Smart Conversations** – Supports general chat, document-based questions, and contextual follow-ups.
- 📝 **Document Summarization** – Generate comprehensive summaries using a Map-Reduce approach.
- 📚 **Source References** – Trace answers back to their original documents and page numbers.
- ⚙️ **Background Processing** – Extract, chunk, and embed documents asynchronously.
- 🔐 **Secure Authentication** – JWT authentication, Supabase Auth, Row Level Security, and private file storage.

## 🛠️ Tech Stack

| Category | Technologies |
|---|---|
| Frontend | Next.js, React, TypeScript, Tailwind CSS |
| Backend | Python, FastAPI |
| Database | Supabase PostgreSQL, pgvector |
| Authentication | Supabase Auth |
| AI / LLM | Google Gemini |
| Embeddings | Sentence Transformers (`all-MiniLM-L6-v2`) |
| Document Processing | PyMuPDF, python-docx |
| Storage | Supabase Storage |

## 🔄 How It Works

**Document Ingestion**

```text
📤 Upload Document
       ↓
📄 Extract Text
       ↓
✂️ Split into Chunks
       ↓
🧠 Generate Embeddings
       ↓
💾 Store in Supabase + pgvector
```

**Question Answering (RAG)**

```text
💬 User Question
       ↓
🔍 Semantic Search
       ↓
📚 Retrieve Relevant Chunks
       ↓
🤖 Gemini Generates Answer
       ↓
📌 Answer with Source References
```

## 🏗️ Project Structure

```text
knowledgehub-ai/
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── models/
│   │   ├── services/
│   │   └── main.py
│   ├── requirements.txt
│   └── .env.example
│
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── app/
│   │   ├── components/
│   │   └── lib/
│   └── package.json
│
├── .gitignore
└── README.md
```

## ⚡ Getting Started

### Prerequisites

- Python 3.12+
- Node.js and npm
- Supabase project
- Google Gemini API key

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/knowledgehub-ai.git
cd knowledgehub-ai
```

### 2. Backend Setup

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1

cd backend
pip install -r requirements.txt
```

Create `backend/.env` using `.env.example` and configure your Supabase and Gemini credentials.

### 3. Frontend Setup

Open another terminal:

```bash
cd frontend
npm install
```

Configure the required Supabase environment variables in `frontend/.env.local`.

### 4. Run the Application

Start the backend:

```bash
cd backend
uvicorn app.main:app --reload
```

Start the frontend in another terminal:

```bash
cd frontend
npm run dev
```

Open **http://localhost:3000** to access the application.

The background document-processing worker must also be running. Configure Supabase with the required database schema, RLS policies, private Storage bucket, and RPC functions before using the application.

## 🔐 Security

- JWT-based authentication.
- Supabase Row Level Security (RLS).
- Private document storage.
- User-specific document access.
- Privileged database operations isolated to background processing.
- Environment variables used for sensitive credentials.

**Never expose API keys or Supabase secret keys in the frontend or public repository.**

## 🚧 Future Improvements

- [ ] Hybrid Search (BM25 + Vector Search)
- [ ] Cross-Encoder Reranking
- [ ] GraphRAG for document relationship understanding
- [ ] OCR support for scanned documents
- [ ] Local LLM integration using Ollama
- [ ] Streaming AI responses
- [ ] Advanced document analytics

## 🤝 Contributing

Contributions, suggestions, and feature requests are welcome!

Feel free to fork the repository, create a feature branch, and submit a pull request.

## 📄 License

Distributed under the MIT License, if selected for this repository. See `LICENSE` for details.

---

⭐ **If you find KnowledgeHub AI interesting, consider giving it a star!**

**KnowledgeHub AI — Turning documents into knowledge, one question at a time.**
