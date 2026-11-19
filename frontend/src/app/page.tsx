
"use client";

import { useCallback, useEffect, useState, type KeyboardEvent } from "react";
import { useRouter } from "next/navigation";
import AuthGuard from "../components/auth-guard";
import { supabase } from "../lib/supabase";

// Document data returned by FastAPI.
type KnowledgeDocument = {
  id: string;
  filename: string;
  file_type: string;
  file_size: number;
  status: "pending" | "processing" | "completed" | "failed";
  created_at: string;
  chunk_count: number;
};

// Source data returned by the RAG API.
type ChatSource = {
  source_label: string;
  document_id: string;
  filename: string;
  page_number: number | null;
  chunk_index: number;
  similarity: number;
};

// Conversation data returned by FastAPI.
type Conversation = {
  id: string;
  title: string | null;
  created_at: string;
  updated_at: string;
};

// Message data returned by FastAPI.
type ChatMessage = {
  id: string;
  conversation_id: string;
  role: "user" | "assistant";
  content: string;
  sources: ChatSource[];
  created_at: string;
};

export default function Home() {
  const router = useRouter();

  // Theme state.
  const [theme, setTheme] = useState<"dark" | "light">("dark");

  // Document states.
  const [documents, setDocuments] = useState<KnowledgeDocument[]>([]);
  const [documentsLoading, setDocumentsLoading] = useState(true);
  const [documentsError, setDocumentsError] = useState("");
  const [selectedDocumentId, setSelectedDocumentId] = useState<string | null>(null);

  // Chat states.
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [sources, setSources] = useState<ChatSource[]>([]);
  const [chatLoading, setChatLoading] = useState(false);
  const [chatError, setChatError] = useState("");

  // Conversation history states.
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [selectedConversationId, setSelectedConversationId] =
    useState<string | null>(null);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyError, setHistoryError] = useState("");
  const [deletingConversationId, setDeletingConversationId] =
    useState<string | null>(null);

  const isDark = theme === "dark";

  // Calculate total chunks directly from document data.
  const chunkCount = documents.reduce(
    (total, document) => total + document.chunk_count,
    0
  );

  // Fetch documents belonging to the authenticated user.
  useEffect(() => {
    let cancelled = false;

    async function fetchDocuments() {
      try {
        setDocumentsLoading(true);
        setDocumentsError("");

        const {
          data: { session },
        } = await supabase.auth.getSession();

        if (!session) {
          router.replace("/login");
          return;
        }

        const response = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL}/documents/`,
          {
            headers: {
              Authorization: `Bearer ${session.access_token}`,
            },
          }
        );

        if (!response.ok) {
          throw new Error(
            `Unable to load documents. Server returned ${response.status}.`
          );
        }

        const data = await response.json();

        const documentList = Array.isArray(data)
          ? data
          : Array.isArray(data.documents)
            ? data.documents
            : Array.isArray(data.data)
              ? data.data
              : null;

        if (!documentList) {
          throw new Error("Unexpected documents API response format.");
        }

        if (!cancelled) {
          const normalizedDocuments: KnowledgeDocument[] =
            documentList.map((document: KnowledgeDocument) => ({
              ...document,
              chunk_count: Number(document.chunk_count) || 0,
            }));

          setDocuments(normalizedDocuments);
        }
      } catch (error) {
        if (!cancelled) {
          setDocumentsError(
            error instanceof Error
              ? error.message
              : "Something went wrong while loading documents."
          );
        }
      } finally {
        if (!cancelled) {
          setDocumentsLoading(false);
        }
      }
    }

    fetchDocuments();

    return () => {
      cancelled = true;
    };
  }, [router]);

  // Fetch all conversations belonging to the logged-in user.
  const fetchConversations = useCallback(async () => {
    try {
      const {
        data: { session },
      } = await supabase.auth.getSession();

      if (!session) {
        router.replace("/login");
        return;
      }

      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/chat/conversations`,
        {
          headers: {
            Authorization: `Bearer ${session.access_token}`,
          },
        }
      );

      if (!response.ok) {
        throw new Error("Unable to load conversation history.");
      }

      const data = await response.json();

      setConversations(
        Array.isArray(data.conversations) ? data.conversations : []
      );
    } catch (error) {
      console.error("Conversation history error:", error);
      setHistoryError(
        error instanceof Error
          ? error.message
          : "Unable to load conversation history."
      );
    }
  }, [router]);

  // Load conversation history when the dashboard opens.
  useEffect(() => {
    fetchConversations();
  }, [fetchConversations]);

  // Fetch messages belonging to a selected conversation.
  async function openConversation(conversationId: string) {
    if (chatLoading || deletingConversationId) return;

    try {
      setHistoryLoading(true);
      setHistoryError("");
      setChatError("");
      setQuestion("");
      setAnswer("");
      setSources([]);
      setChatMessages([]);
      setSelectedDocumentId(null);

      const {
        data: { session },
      } = await supabase.auth.getSession();

      if (!session) {
        router.replace("/login");
        return;
      }

      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/chat/conversations/${conversationId}/messages`,
        {
          headers: {
            Authorization: `Bearer ${session.access_token}`,
          },
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail || "Unable to load this conversation."
        );
      }

      const messages: ChatMessage[] = Array.isArray(data.messages)
        ? data.messages.map((message: ChatMessage) => ({
            ...message,
            sources: Array.isArray(message.sources)
              ? message.sources
              : [],
          }))
        : [];

      setSelectedConversationId(conversationId);
      setChatMessages(messages);

      // Display the latest assistant response in the existing answer area.
      const assistantMessages = messages.filter(
        (message) => message.role === "assistant"
      );

      if (assistantMessages.length > 0) {
        const latestMessage =
          assistantMessages[assistantMessages.length - 1];

        setAnswer(latestMessage.content);
        setSources(latestMessage.sources);
      }
    } catch (error) {
      setHistoryError(
        error instanceof Error
          ? error.message
          : "Unable to load conversation."
      );
    } finally {
      setHistoryLoading(false);
    }
  }

  // Start a new conversation.
  function handleNewChat() {
    if (chatLoading || deletingConversationId) return;

    setSelectedConversationId(null);
    setChatMessages([]);
    setSelectedDocumentId(null);
    setQuestion("");
    setAnswer("");
    setSources([]);
    setChatError("");
    setHistoryError("");

    document.getElementById("ask")?.scrollIntoView({
      behavior: "smooth",
      block: "start",
    });
  }

  // Delete a conversation.
  async function handleDeleteConversation(conversationId: string) {
    if (chatLoading || deletingConversationId) return;

    const confirmed = window.confirm(
      "Are you sure you want to delete this conversation? All its messages will also be deleted. This action cannot be undone."
    );

    if (!confirmed) return;

    try {
      setDeletingConversationId(conversationId);
      setHistoryError("");

      const {
        data: { session },
      } = await supabase.auth.getSession();

      if (!session) {
        router.replace("/login");
        return;
      }

      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/chat/conversations/${conversationId}`,
        {
          method: "DELETE",
          headers: {
            Authorization: `Bearer ${session.access_token}`,
          },
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Unable to delete conversation.");
      }

      // Remove the deleted conversation from the sidebar.
      setConversations((previous) =>
        previous.filter((conversation) => conversation.id !== conversationId)
      );

      // Reset the chat if the deleted conversation was currently open.
      if (selectedConversationId === conversationId) {
        setSelectedConversationId(null);
        setChatMessages([]);
        setQuestion("");
        setAnswer("");
        setSources([]);
        setChatError("");
      }
    } catch (error) {
      alert(
        error instanceof Error
          ? error.message
          : "Something went wrong while deleting the conversation."
      );
    } finally {
      setDeletingConversationId(null);
    }
  }

  // Log out the current user.
  async function handleLogout() {
    const { error } = await supabase.auth.signOut();

    if (error) {
      alert("Logout failed. Please try again.");
      return;
    }

    router.replace("/login");
  }

  // Send a question to the FastAPI RAG endpoint.
  async function handleAskQuestion() {
    if (!question.trim() || chatLoading) return;

    const currentQuestion = question.trim();

    try {
      setChatLoading(true);
      setChatError("");
      setAnswer("");
      setSources([]);

      const {
        data: { session },
      } = await supabase.auth.getSession();

      if (!session) {
        router.replace("/login");
        return;
      }

      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/chat/ask`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${session.access_token}`,
          },
          body: JSON.stringify({
            question: currentQuestion,
            match_count: 5,
            document_id: selectedDocumentId,
            conversation_id: selectedConversationId,
          }),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail || "Failed to get an answer from AI."
        );
      }

      const newConversationId = data.conversation_id;

      if (!newConversationId) {
        throw new Error("The server did not return a conversation ID.");
      }

      setSelectedConversationId(newConversationId);
      setAnswer(data.answer);
      setSources(Array.isArray(data.sources) ? data.sources : []);
      setQuestion("");

      // Refresh the conversation list.
      await fetchConversations();

      // Load the saved messages from the backend.
      const messagesResponse = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/chat/conversations/${newConversationId}/messages`,
        {
          headers: {
            Authorization: `Bearer ${session.access_token}`,
          },
        }
      );

      if (messagesResponse.ok) {
        const messagesData = await messagesResponse.json();

        const messages: ChatMessage[] = Array.isArray(messagesData.messages)
          ? messagesData.messages.map((message: ChatMessage) => ({
              ...message,
              sources: Array.isArray(message.sources)
                ? message.sources
                : [],
            }))
          : [];

        setChatMessages(messages);
      }
    } catch (error) {
      setChatError(
        error instanceof Error
          ? error.message
          : "Something went wrong. Please try again."
      );
    } finally {
      setChatLoading(false);
    }
  }

  // Allow Enter to submit and Shift+Enter to add a new line.
  function handleQuestionKeyDown(
    event: KeyboardEvent<HTMLTextAreaElement>
  ) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      handleAskQuestion();
    }
  }

  // Dashboard statistics.
  const processedDocuments = documents.filter(
    (document) => document.status === "completed"
  ).length;

  return (
    <AuthGuard>
      <main className={`app-shell ${isDark ? "dark-theme" : "light-theme"}`}>
        {/* Sidebar */}
        <aside className="sidebar">
          <div className="brand">
            <div className="brand-icon">K</div>
            <span>
              KnowledgeHub <strong>AI</strong>
            </span>
          </div>

          <div className="sidebar-section-label">WORKSPACE</div>

          <nav className="sidebar-nav">
            <a className="nav-item active" href="#">
              <span>▦</span> Overview
            </a>

            <a className="nav-item" href="/documents">
              <span>▤</span> Documents
            </a>

            <a className="nav-item" href="#ask">
              <span>✧</span> AI Assistant
            </a>
          </nav>

          {/* Conversation history */}
          <div className="sidebar-section-label">
            CONVERSATIONS
          </div>

          <button
            className="nav-item"
            onClick={handleNewChat}
            disabled={chatLoading || !!deletingConversationId}
            style={{
              width: "100%",
              border: "1px solid var(--border-color, #555)",
              marginBottom: "12px",
              cursor: "pointer",
            }}
          >
            <span>＋</span> New Chat
          </button>

          <div
            style={{
              maxHeight: "300px",
              overflowY: "auto",
              paddingRight: "4px",
            }}
          >
            {conversations.length === 0 ? (
              <small style={{ padding: "8px", display: "block" }}>
                No previous conversations.
              </small>
            ) : (
              conversations.map((conversation) => (
                <div
                  key={conversation.id}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "4px",
                    marginBottom: "4px",
                  }}
                >
                  {/* Open conversation button */}
                  <button
                    onClick={() => openConversation(conversation.id)}
                    disabled={
                      chatLoading ||
                      historyLoading ||
                      !!deletingConversationId
                    }
                    className="nav-item"
                    style={{
                      flex: 1,
                      minWidth: 0,
                      textAlign: "left",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      whiteSpace: "nowrap",
                      background:
                        selectedConversationId === conversation.id
                          ? "var(--border-color, rgba(128,128,128,0.2))"
                          : "transparent",
                      cursor: "pointer",
                    }}
                    title={conversation.title || "New Conversation"}
                  >
                    <span>◷</span>
                    {conversation.title || "New Conversation"}
                  </button>

                  {/* Delete conversation button */}
                  <button
                    onClick={() =>
                      handleDeleteConversation(conversation.id)
                    }
                    disabled={
                      chatLoading ||
                      historyLoading ||
                      !!deletingConversationId
                    }
                    title="Delete conversation"
                    aria-label={`Delete ${conversation.title || "conversation"}`}
                    style={{
                      border: "none",
                      background: "transparent",
                      color: "#ef4444",
                      cursor: "pointer",
                      padding: "8px",
                      borderRadius: "6px",
                      fontSize: "16px",
                      flexShrink: 0,
                      opacity:
                        deletingConversationId === conversation.id
                          ? 0.5
                          : 1,
                    }}
                  >
                    {deletingConversationId === conversation.id ? "…" : "🗑"}
                  </button>
                </div>
              ))
            )}
          </div>

          {historyError && (
            <small style={{ color: "#ef4444", padding: "8px" }}>
              {historyError}
            </small>
          )}

          <div className="sidebar-bottom">
            <div className="sidebar-section-label">PREFERENCES</div>

            <button
              className="nav-item theme-button"
              onClick={() => setTheme(isDark ? "light" : "dark")}
            >
              <span>{isDark ? "☀" : "☾"}</span>
              {isDark ? "Light mode" : "Dark mode"}
            </button>

            <div className="profile-card">
              <div className="avatar">U</div>
              <div>
                <strong>Your workspace</strong>
                <small>Personal account</small>
              </div>
            </div>
          </div>
        </aside>

        {/* Main content */}
        <section className="main-content">
          <header className="topbar">
            <div>
              <span className="breadcrumb">Workspace / </span>
              <strong>Overview</strong>
            </div>

            <div className="topbar-actions">
              <button
                className="top-theme-button"
                onClick={() => setTheme(isDark ? "light" : "dark")}
                aria-label="Toggle color theme"
              >
                {isDark ? "☀ Light mode" : "☾ Dark mode"}
              </button>

              <button
                className="top-theme-button"
                onClick={handleLogout}
              >
                Logout ↗
              </button>
            </div>
          </header>

          <div className="dashboard">
            {/* Welcome section */}
            <section className="welcome-section">
              <div>
                <div className="eyebrow">
                  YOUR AI KNOWLEDGE WORKSPACE
                </div>

                <h1>Good to see you again.</h1>

                <p>
                  Your knowledge, organized and ready to answer.
                  Ask questions across your documents with AI.
                </p>
              </div>

              <div className="welcome-decoration">✧</div>
            </section>

            {/* Statistics */}
            <section className="stats-grid">
              <div className="stat-card">
                <div className="stat-top">
                  <span>Total documents</span>
                  <span className="stat-icon">▤</span>
                </div>

                <strong>
                  {documentsLoading ? "—" : documents.length}
                </strong>

                <small>Your uploaded documents</small>
              </div>

              <div className="stat-card">
                <div className="stat-top">
                  <span>Processed documents</span>
                  <span className="stat-icon">✓</span>
                </div>

                <strong>
                  {documentsLoading ? "—" : processedDocuments}
                </strong>

                <small>Successfully processed</small>
              </div>

              <div className="stat-card">
                <div className="stat-top">
                  <span>Knowledge chunks</span>
                  <span className="stat-icon">▦</span>
                </div>

                <strong>
                  {documentsLoading ? "—" : chunkCount}
                </strong>

                <small>
                  {documentsLoading
                    ? "Loading chunk count..."
                    : "Stored document chunks"}
                </small>
              </div>
            </section>

            {/* AI Assistant */}
            <section className="assistant-card" id="ask">
              <div className="assistant-heading">
                <div className="assistant-icon">✧</div>

                <div>
                  <span className="eyebrow">AI ASSISTANT</span>
                  <h2>
                    {selectedConversationId
                      ? "Continue your conversation"
                      : "Ask your knowledge base"}
                  </h2>
                  <p>
                    Get answers grounded in your uploaded documents.
                  </p>
                </div>
              </div>

              {/* Choose whether to search all documents or one document. */}
              <div
                style={{
                  margin: "20px 0",
                  padding: "14px",
                  border: "1px solid var(--border-color, #555)",
                  borderRadius: "10px",
                }}
              >
                <label
                  htmlFor="document-scope"
                  style={{
                    display: "block",
                    marginBottom: "8px",
                    fontSize: "13px",
                    fontWeight: 600,
                  }}
                >
                  Search scope
                </label>

                <select
                  id="document-scope"
                  value={selectedDocumentId ?? ""}
                  onChange={(event) =>
                    setSelectedDocumentId(event.target.value || null)
                  }
                  disabled={chatLoading || historyLoading || documentsLoading}
                  style={{
                    width: "100%",
                    maxWidth: "460px",
                    padding: "10px 12px",
                    borderRadius: "8px",
                    border: "1px solid var(--border-color, #777)",
                    background: "var(--card-bg, transparent)",
                    color: "inherit",
                  }}
                >
                  <option value="">All completed documents</option>
                  {documents
                    .filter((document) => document.status === "completed")
                    .map((document) => (
                      <option key={document.id} value={document.id}>
                        {document.filename}
                      </option>
                    ))}
                </select>

                <p style={{ marginTop: "7px", fontSize: "12px", opacity: 0.7 }}>
                  {selectedDocumentId
                    ? "Your next question will search only the selected document."
                    : "Your next question will search across all your completed documents."}
                </p>

                {documentsError && (
                  <p style={{ marginTop: "6px", fontSize: "12px", color: "#ef4444" }}>
                    {documentsError}
                  </p>
                )}
              </div>

              {/* Current conversation messages */}
              {historyLoading && (
                <div className="chat-response">
                  <p>Loading conversation...</p>
                </div>
              )}

              {chatMessages.length > 0 && (
                <div style={{ marginBottom: "20px" }}>
                  {chatMessages.map((message) => (
                    <div
                      key={message.id}
                      className="chat-response"
                      style={{ marginBottom: "14px" }}
                    >
                      <h3>
                        {message.role === "user"
                          ? "You"
                          : "KnowledgeHub AI"}
                      </h3>

                      <p
                        style={{
                          whiteSpace: "pre-wrap",
                          lineHeight: "1.7",
                        }}
                      >
                        {message.content}
                      </p>

                      {message.role === "assistant" &&
                        message.sources.length > 0 && (
                          <div style={{ marginTop: "16px" }}>
                            <h3>Sources</h3>

                            {message.sources.map((source, index) => (
                              <div
                                key={`${source.document_id}-${source.chunk_index}-${index}`}
                                style={{
                                  padding: "12px",
                                  marginTop: "10px",
                                  borderRadius: "8px",
                                  border:
                                    "1px solid var(--border-color, #555)",
                                }}
                              >
                                <strong>
                                  [{source.source_label}] {source.filename}
                                </strong>

                                <p>
                                  Page:{" "}
                                  {source.page_number ?? "Not available"}
                                </p>

                                <small>
                                  Relevance:{" "}
                                  {(source.similarity * 100).toFixed(1)}%
                                </small>
                              </div>
                            ))}
                          </div>
                        )}
                    </div>
                  ))}
                </div>
              )}

              {/* Question input */}
              <div className="question-box">
                <textarea
                  value={question}
                  onChange={(event) => setQuestion(event.target.value)}
                  onKeyDown={handleQuestionKeyDown}
                  placeholder="Ask a question about your documents..."
                  rows={2}
                  disabled={chatLoading || historyLoading}
                />

                <button
                  className="ask-button"
                  onClick={handleAskQuestion}
                  disabled={
                    !question.trim() || chatLoading || historyLoading
                  }
                >
                  {chatLoading ? "Thinking..." : "Ask AI"}
                  {!chatLoading && <span>↗</span>}
                </button>
              </div>

              {/* Suggested questions */}
              <div className="suggestions">
                <span>Try asking:</span>

                <button
                  onClick={() =>
                    setQuestion(
                      "What are the loan eligibility requirements?"
                    )
                  }
                  disabled={chatLoading}
                >
                  Loan eligibility requirements
                </button>

                <button
                  onClick={() =>
                    setQuestion("Summarize my uploaded documents.")
                  }
                  disabled={chatLoading}
                >
                  Summarize my documents
                </button>
              </div>

              {/* Loading state */}
              {chatLoading && (
                <div className="chat-response">
                  <p>
                    Searching your documents and generating an answer...
                  </p>
                </div>
              )}

              {/* Error state */}
              {chatError && (
                <div className="chat-response">
                  <h3>Something went wrong</h3>
                  <p style={{ color: "#ef4444" }}>{chatError}</p>
                </div>
              )}

              {/* Fallback for latest answer if messages have not loaded */}
              {answer && chatMessages.length === 0 && (
                <div className="chat-response">
                  <h3>AI Answer</h3>

                  <p
                    style={{
                      whiteSpace: "pre-wrap",
                      lineHeight: "1.7",
                    }}
                  >
                    {answer}
                  </p>

                  {sources.length > 0 && (
                    <div style={{ marginTop: "20px" }}>
                      <h3>Sources</h3>

                      {sources.map((source, index) => (
                        <div
                          key={`${source.document_id}-${source.chunk_index}-${index}`}
                          style={{
                            padding: "12px",
                            marginTop: "10px",
                            borderRadius: "8px",
                            border: "1px solid var(--border-color, #555)",
                          }}
                        >
                          <strong>
                            [{source.source_label}] {source.filename}
                          </strong>

                          <p>
                            Page: {source.page_number ?? "Not available"}
                          </p>

                          <small>
                            Relevance:{" "}
                            {(source.similarity * 100).toFixed(1)}%
                          </small>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </section>

            {/* Recent documents */}
            <section className="documents-section" id="documents">
              <div className="section-heading">
                <div>
                  <h2>Recent documents</h2>
                  <p>Your recently uploaded knowledge sources</p>
                </div>

                <button
                  className="text-button"
                  onClick={() => router.push("/documents")}
                >
                  View all →
                </button>
              </div>

              <div className="document-list">
                {documentsLoading ? (
                  <p>Loading your documents...</p>
                ) : documentsError ? (
                  <p>{documentsError}</p>
                ) : documents.length === 0 ? (
                  <p>No documents uploaded yet.</p>
                ) : (
                  documents.map((document) => (
                    <div
                      className="document-row"
                      key={document.id}
                    >
                      <div className="file-icon">
                        {document.file_type.toUpperCase()}
                      </div>

                      <div className="document-info">
                        <strong>{document.filename}</strong>

                        <small>
                          {new Date(
                            document.created_at
                          ).toLocaleDateString()}
                        </small>
                      </div>

                      <span className="status-pill">
                        <span className="status-dot" />
                        {document.status}
                      </span>
                    </div>
                  ))
                )}
              </div>
            </section>
          </div>
        </section>
      </main>
    </AuthGuard>
  );
}
