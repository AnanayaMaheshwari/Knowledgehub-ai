
"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import AuthGuard from "../../components/auth-guard";
import { supabase } from "../../lib/supabase";

type KnowledgeDocument = {
  id: string;
  filename: string;
  file_type: string;
  file_size: number;
  status: "pending" | "processing" | "completed" | "failed";
  created_at: string;
  chunk_count: number;
};

function formatFileSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

function formatDate(date: string) {
  return new Date(date).toLocaleDateString(undefined, {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

function StatusBadge({
  status,
}: {
  status: KnowledgeDocument["status"];
}) {
  const styles = {
    pending: "bg-yellow-500/10 text-yellow-500",
    processing: "bg-blue-500/10 text-blue-400",
    completed: "bg-green-500/10 text-green-500",
    failed: "bg-red-500/10 text-red-400",
  };

  return (
    <span
      className={`rounded-full px-3 py-1 text-xs font-medium capitalize ${styles[status]}`}
    >
      {status}
    </span>
  );
}

function DocumentsContent() {
  const router = useRouter();

  const [documents, setDocuments] = useState<KnowledgeDocument[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [retryingId, setRetryingId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [summarizingId, setSummarizingId] = useState<string | null>(null);
  const [summaryResult, setSummaryResult] = useState<{
    filename: string;
    summary: string;
    total_chunks: number;
    pages: number[];
  } | null>(null);

  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const API_URL = process.env.NEXT_PUBLIC_API_URL;

  // Fetch documents belonging to the authenticated user.
  const fetchDocuments = useCallback(async () => {
    try {
      setLoading(true);
      setError("");

      const {
        data: { session },
      } = await supabase.auth.getSession();

      if (!session) {
        router.replace("/login");
        return;
      }

      const response = await fetch(`${API_URL}/documents/`, {
        headers: {
          Authorization: `Bearer ${session.access_token}`,
        },
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Unable to load documents.");
      }

      const documentList = Array.isArray(data)
        ? data
        : data.documents;

      if (!Array.isArray(documentList)) {
        throw new Error("Unexpected response from the documents API.");
      }

      setDocuments(
        documentList.map((document: KnowledgeDocument) => ({
          ...document,
          chunk_count: document.chunk_count ?? 0,
        }))
      );
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Something went wrong while loading documents."
      );
    } finally {
      setLoading(false);
    }
  }, [API_URL, router]);

  useEffect(() => {
    fetchDocuments();
  }, [fetchDocuments]);

  // Upload a new document.
  async function handleUpload(
    event: React.ChangeEvent<HTMLInputElement>
  ) {
    const file = event.target.files?.[0];

    if (!file) return;

    setError("");
    setSuccess("");

    const extension = file.name.split(".").pop()?.toLowerCase();

    if (!["pdf", "docx"].includes(extension || "")) {
      setError("Only PDF and DOCX files are supported.");
      event.target.value = "";
      return;
    }

    if (file.size > 10 * 1024 * 1024) {
      setError("File size cannot exceed 10 MB.");
      event.target.value = "";
      return;
    }

    try {
      setUploading(true);

      const {
        data: { session },
      } = await supabase.auth.getSession();

      if (!session) {
        router.replace("/login");
        return;
      }

      const formData = new FormData();
      formData.append("file", file);

      const response = await fetch(`${API_URL}/documents/upload`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${session.access_token}`,
        },
        body: formData,
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Document upload failed.");
      }

      setSuccess(
        "Document uploaded successfully. Processing will begin shortly."
      );

      await fetchDocuments();
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Document upload failed."
      );
    } finally {
      setUploading(false);
      event.target.value = "";
    }
  }

  // Retry failed document processing.
  async function handleRetry(documentId: string) {
    try {
      setRetryingId(documentId);
      setError("");
      setSuccess("");

      const {
        data: { session },
      } = await supabase.auth.getSession();

      if (!session) {
        router.replace("/login");
        return;
      }

      const response = await fetch(
        `${API_URL}/documents/${documentId}/retry`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${session.access_token}`,
          },
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Document retry failed.");
      }

      setSuccess("Document processing has been queued for retry.");

      await fetchDocuments();
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Could not retry document."
      );
    } finally {
      setRetryingId(null);
    }
  }

  // Generate a summary using all processed chunks of a document.
  async function handleSummarize(document: KnowledgeDocument) {
    try {
      setSummarizingId(document.id);
      setError("");
      setSuccess("");
      setSummaryResult(null);

      const {
        data: { session },
      } = await supabase.auth.getSession();

      if (!session) {
        router.replace("/login");
        return;
      }

      const response = await fetch(
        `${API_URL}/documents/${document.id}/summarize`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${session.access_token}`,
          },
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Unable to summarize this document.");
      }

      setSummaryResult({
        filename: data.filename,
        summary: data.summary,
        total_chunks: data.total_chunks,
        pages: data.pages ?? [],
      });
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Something went wrong while summarizing the document."
      );
    } finally {
      setSummarizingId(null);
    }
  }

  // Delete a document.
  async function handleDelete(document: KnowledgeDocument) {
    const confirmed = window.confirm(
      `Are you sure you want to permanently delete "${document.filename}"?\n\nThis will also delete all its associated knowledge chunks. This action cannot be undone.`
    );

    if (!confirmed) return;

    try {
      setDeletingId(document.id);
      setError("");
      setSuccess("");

      const {
        data: { session },
      } = await supabase.auth.getSession();

      if (!session) {
        router.replace("/login");
        return;
      }

      const response = await fetch(
        `${API_URL}/documents/${document.id}`,
        {
          method: "DELETE",
          headers: {
            Authorization: `Bearer ${session.access_token}`,
          },
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail || "Unable to delete this document."
        );
      }

      // Remove the document from the UI after backend success.
      setDocuments((previousDocuments) =>
        previousDocuments.filter(
          (item) => item.id !== document.id
        )
      );

      if (data.storage_cleanup === false) {
        setSuccess(
          "Document and knowledge chunks deleted, but the original Storage file could not be removed. Administrator cleanup may be required."
        );
      } else {
        setSuccess(
          `"${document.filename}" and its knowledge chunks were deleted successfully.`
        );
      }
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Something went wrong while deleting the document."
      );
    } finally {
      setDeletingId(null);
    }
  }

  // Dashboard statistics.
  const completedCount = documents.filter(
    (doc) => doc.status === "completed"
  ).length;

  const processingCount = documents.filter(
    (doc) =>
      doc.status === "processing" || doc.status === "pending"
  ).length;

  const failedCount = documents.filter(
    (doc) => doc.status === "failed"
  ).length;

  const totalChunks = documents.reduce(
    (total, document) => total + document.chunk_count,
    0
  );

  return (
    <main className="min-h-screen bg-[#101019] px-5 py-8 text-white md:px-10">
      <div className="mx-auto max-w-6xl">

        {/* Page header */}
        <div className="mb-8 flex flex-wrap items-center justify-between gap-4">
          <div>
            <button
              onClick={() => router.push("/")}
              className="mb-4 text-sm text-purple-400 hover:text-purple-300"
            >
              ← Back to dashboard
            </button>

            <h1 className="text-3xl font-semibold">
              Document Management
            </h1>

            <p className="mt-2 text-sm text-gray-400">
              Upload, organize, and manage your knowledge sources.
            </p>
          </div>

          <label
            className={`cursor-pointer rounded-lg bg-purple-600 px-5 py-3 text-sm font-medium transition hover:bg-purple-500 ${
              uploading ? "pointer-events-none opacity-60" : ""
            }`}
          >
            {uploading ? "Uploading..." : "+ Upload document"}

            <input
              type="file"
              accept=".pdf,.docx"
              className="hidden"
              onChange={handleUpload}
              disabled={uploading}
            />
          </label>
        </div>

        {/* Statistics */}
        <div className="mb-8 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">

          <div className="rounded-xl border border-white/10 bg-white/[0.03] p-5">
            <p className="text-sm text-gray-400">
              Total documents
            </p>

            <p className="mt-2 text-3xl font-semibold">
              {documents.length}
            </p>
          </div>

          <div className="rounded-xl border border-white/10 bg-white/[0.03] p-5">
            <p className="text-sm text-gray-400">
              Successfully processed
            </p>

            <p className="mt-2 text-3xl font-semibold text-green-400">
              {completedCount}
            </p>
          </div>

          <div className="rounded-xl border border-white/10 bg-white/[0.03] p-5">
            <p className="text-sm text-gray-400">
              Pending / Failed
            </p>

            <p className="mt-2 text-3xl font-semibold">
              {processingCount + failedCount}
            </p>

            <p className="mt-1 text-xs text-gray-500">
              {processingCount} pending or processing · {failedCount} failed
            </p>
          </div>

          <div className="rounded-xl border border-white/10 bg-white/[0.03] p-5">
            <p className="text-sm text-gray-400">
              Total knowledge chunks
            </p>

            <p className="mt-2 text-3xl font-semibold text-purple-400">
              {totalChunks}
            </p>

            <p className="mt-1 text-xs text-gray-500">
              Across all your documents
            </p>
          </div>
        </div>

        {/* Notifications */}
        {error && (
          <div className="mb-5 rounded-lg border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-300">
            {error}
          </div>
        )}

        {success && (
          <div className="mb-5 rounded-lg border border-green-500/30 bg-green-500/10 p-4 text-sm text-green-300">
            {success}
          </div>
        )}

        {/* Document list */}
        <section className="overflow-hidden rounded-xl border border-white/10 bg-white/[0.03]">

          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/10 p-5">
            <div>
              <h2 className="font-semibold">
                Your documents
              </h2>

              <p className="mt-1 text-xs text-gray-400">
                Your uploaded PDF and DOCX files
              </p>
            </div>

            <button
              onClick={fetchDocuments}
              disabled={loading || deletingId !== null}
              className="rounded-lg border border-white/10 px-4 py-2 text-sm text-gray-300 hover:bg-white/5 disabled:opacity-50"
            >
              {loading ? "Refreshing..." : "↻ Refresh"}
            </button>
          </div>

          {loading ? (
            <div className="p-10 text-center text-sm text-gray-400">
              Loading your documents...
            </div>
          ) : documents.length === 0 ? (
            <div className="p-12 text-center">
              <div className="mb-3 text-4xl">▤</div>

              <h3 className="font-medium">
                No documents yet
              </h3>

              <p className="mt-2 text-sm text-gray-400">
                Upload a PDF or DOCX file to build your knowledge base.
              </p>
            </div>
          ) : (
            <div className="divide-y divide-white/10">
              {documents.map((document) => (
                <div
                  key={document.id}
                  className="flex flex-col gap-4 p-5 transition hover:bg-white/[0.02] md:flex-row md:items-center md:justify-between"
                >
                  <div className="flex min-w-0 items-center gap-4">

                    <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg bg-purple-500/10 text-sm font-semibold text-purple-300">
                      {document.file_type.toUpperCase()}
                    </div>

                    <div className="min-w-0">
                      <h3 className="truncate font-medium">
                        {document.filename}
                      </h3>

                      <p className="mt-1 text-xs text-gray-400">
                        {formatFileSize(document.file_size)} ·{" "}
                        {formatDate(document.created_at)}
                      </p>

                      <p className="mt-1 text-xs font-medium text-purple-300">
                        {document.chunk_count} knowledge chunks
                      </p>
                    </div>
                  </div>

                  <div className="flex flex-wrap items-center gap-3">
                    <StatusBadge status={document.status} />

                    {document.status === "completed" && (
                      <button
                        onClick={() => handleSummarize(document)}
                        disabled={
                          summarizingId !== null ||
                          deletingId !== null ||
                          retryingId !== null
                        }
                        className="rounded-lg border border-purple-500/30 px-3 py-2 text-xs font-medium text-purple-300 transition hover:bg-purple-500/10 disabled:cursor-not-allowed disabled:opacity-40"
                      >
                        {summarizingId === document.id
                          ? "Summarizing..."
                          : "Summarize"}
                      </button>
                    )}

                    {document.status === "failed" && (
                      <button
                        onClick={() => handleRetry(document.id)}
                        disabled={
                          retryingId === document.id ||
                          deletingId !== null
                        }
                        className="rounded-lg border border-purple-500/30 px-3 py-2 text-xs text-purple-300 hover:bg-purple-500/10 disabled:opacity-50"
                      >
                        {retryingId === document.id
                          ? "Retrying..."
                          : "Retry processing"}
                      </button>
                    )}

                    <button
                      onClick={() => handleDelete(document)}
                      disabled={
                        deletingId !== null ||
                        document.status === "processing" ||
                        retryingId === document.id
                      }
                      title={
                        document.status === "processing"
                          ? "Wait until processing is complete before deleting."
                          : "Delete document"
                      }
                      className="rounded-lg border border-red-500/30 px-3 py-2 text-xs font-medium text-red-400 transition hover:bg-red-500/10 disabled:cursor-not-allowed disabled:opacity-40"
                    >
                      {deletingId === document.id
                        ? "Deleting..."
                        : "Delete"}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* Full-document summary */}
        {summaryResult && (
          <section className="mt-6 overflow-hidden rounded-xl border border-purple-500/30 bg-purple-500/[0.04]">
            <div className="flex flex-wrap items-start justify-between gap-4 border-b border-white/10 p-5">
              <div>
                <p className="text-xs font-medium uppercase tracking-wide text-purple-300">
                  Document summary
                </p>
                <h2 className="mt-1 text-lg font-semibold">
                  {summaryResult.filename}
                </h2>
                <p className="mt-2 text-xs text-gray-400">
                  Generated from {summaryResult.total_chunks} knowledge chunks
                  {summaryResult.pages.length > 0
                    ? ` · ${summaryResult.pages.length} pages`
                    : ""}
                </p>
              </div>

              <button
                onClick={() => setSummaryResult(null)}
                className="rounded-lg border border-white/10 px-3 py-2 text-xs text-gray-300 transition hover:bg-white/5"
              >
                Close
              </button>
            </div>

            <div className="max-h-[700px] overflow-y-auto p-5">
              <div className="whitespace-pre-wrap text-sm leading-7 text-gray-200">
                {summaryResult.summary}
              </div>

              {summaryResult.pages.length > 0 && (
                <p className="mt-6 border-t border-white/10 pt-4 text-xs text-gray-500">
                  Pages included: {summaryResult.pages.join(", ")}
                </p>
              )}
            </div>
          </section>
        )}

        {/* Upload information */}
        <p className="mt-5 text-xs text-gray-500">
          Supported formats: PDF and DOCX. Maximum file size: 10 MB.
          Uploaded files are stored in your private Supabase Storage bucket.
        </p>
      </div>
    </main>
  );
}

export default function DocumentsPage() {
  return (
    <AuthGuard>
      <DocumentsContent />
    </AuthGuard>
  );
}
