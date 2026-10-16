"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "../../context/AuthContext";
import { useToast } from "../../context/ToastContext";
import {
  getCodebaseDetails,
  explainFile,
  getFileContent,
  getSummary,
  getTechnologies,
  getArchitecture,
  getIssues,
  getImprovements,
  getFix,
  searchCodebase,
  chatCodebase,
} from "../../lib/api";
import AppShell from "../../components/AppShell";

// ─── Reusable Theme-Aware UI Components ────────────────────────────────────

function Spinner({ size = 5 }) {
  return (
    <svg className={`animate-spin h-${size} w-${size} text-indigo-600 dark:text-indigo-400`} viewBox="0 0 24 24" fill="none">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
    </svg>
  );
}

function SeverityBadge({ severity }) {
  const classes = {
    high: "bg-rose-500/10 text-rose-600 dark:text-rose-400 border-rose-500/20",
    medium: "bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20",
    low: "bg-sky-500/10 text-sky-600 dark:text-sky-400 border-sky-500/20",
  };
  return (
    <span className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded-full border ${classes[severity] || "bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 border-slate-200 dark:border-slate-700"}`}>
      {severity}
    </span>
  );
}

function Tab({ id, label, active, onClick, icon }) {
  return (
    <button
      id={id}
      onClick={() => onClick()}
      className={`flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-semibold whitespace-nowrap transition ${
        active
          ? "bg-indigo-600 text-white shadow-sm"
          : "text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800/80"
      }`}
    >
      {icon}
      {label}
    </button>
  );
}

function Panel({ children, className = "" }) {
  return (
    <div className={`bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl p-6 shadow-sm transition-colors ${className}`}>
      {children}
    </div>
  );
}

function PanelHeader({ title, subtitle, rightElement = null }) {
  return (
    <div className="flex items-start justify-between mb-5 gap-4">
      <div>
        <h2 className="text-base font-bold text-slate-900 dark:text-white">{title}</h2>
        {subtitle && <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">{subtitle}</p>}
      </div>
      {rightElement}
    </div>
  );
}

function ErrorBox({ message, onRetry }) {
  return (
    <div className="bg-rose-50 dark:bg-rose-950/20 border border-rose-200 dark:border-rose-800/40 rounded-2xl p-4 text-xs text-rose-600 dark:text-rose-300">
      <p className="font-medium leading-relaxed">{message}</p>
      {onRetry && (
        <button onClick={onRetry} className="mt-2 text-indigo-600 dark:text-indigo-400 font-semibold hover:underline text-xs">
          Try again
        </button>
      )}
    </div>
  );
}

function LoadingState({ message = "Loading…" }) {
  return (
    <div className="flex flex-col items-center justify-center py-12 gap-3 text-slate-500 dark:text-slate-400">
      <Spinner size={6} />
      <p className="text-xs font-medium">{message}</p>
    </div>
  );
}

// ─── AI Chat Component (Used both as companion panel and dedicated tab) ────

const SUGGESTED_PROMPTS = [
  "Explain project architecture",
  "Where is authentication implemented?",
  "Trace upload request flow",
  "Find potential bugs in active file",
  "How are MongoDB and vector search used?",
  "Suggest improvements for this codebase",
];

function AIChatAssistant({ codebaseId, activeFile, onOpenFile, isCompact = false }) {
  const { showToast } = useToast();
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content: "Hello! I am your AI Codebase Assistant. Ask me anything about this repository's architecture, APIs, data flows, or file implementations.",
      sources: []
    }
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  async function handleSend(textToSend = null) {
    const text = (textToSend || input).trim();
    if (!text || loading) return;

    const userMsg = { role: "user", content: text };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      // Build bounded history
      const historyPayload = messages.slice(-8).map((m) => ({
        role: m.role,
        content: m.content
      }));

      const res = await chatCodebase(codebaseId, text, historyPayload, activeFile);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: res.reply,
          sources: res.sources || []
        }
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: `⚠️ Error communicating with AI assistant: ${err.message}`,
          sources: []
        }
      ]);
      showToast(err.message || "Failed to get AI response", "error");
    } finally {
      setLoading(false);
    }
  }

  function handleKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  function copyToClipboard(text) {
    navigator.clipboard.writeText(text);
    showToast("Copied to clipboard", "info");
  }

  return (
    <div className={`flex flex-col h-full bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl overflow-hidden shadow-sm ${isCompact ? "max-h-[750px]" : "min-h-[600px]"}`}>
      {/* Header */}
      <div className="p-4 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between bg-slate-50/50 dark:bg-slate-800/40">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-indigo-600 flex items-center justify-center text-white text-xs font-bold shadow-sm">
            AI
          </div>
          <div>
            <h3 className="text-xs font-bold text-slate-900 dark:text-white flex items-center gap-2">
              AI Codebase Assistant
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            </h3>
            {activeFile && (
              <p className="text-[10px] text-slate-500 dark:text-slate-400 font-mono truncate max-w-[200px]">
                Context: {activeFile.split("/").pop()}
              </p>
            )}
          </div>
        </div>

        <button
          onClick={() => {
            setMessages([{
              role: "assistant",
              content: "Chat context cleared. What would you like to explore next?",
              sources: []
            }]);
          }}
          className="text-[11px] text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 transition"
          title="Clear chat history"
        >
          Clear
        </button>
      </div>

      {/* Suggested Prompt Chips */}
      <div className="p-2.5 border-b border-slate-100 dark:border-slate-800/80 bg-slate-50/30 dark:bg-slate-900 flex gap-1.5 overflow-x-auto no-scrollbar">
        {SUGGESTED_PROMPTS.map((prompt) => (
          <button
            key={prompt}
            onClick={() => handleSend(prompt)}
            disabled={loading}
            className="px-2.5 py-1 rounded-lg text-[11px] font-medium bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700/80 text-slate-600 dark:text-slate-300 hover:border-indigo-500 hover:text-indigo-600 dark:hover:text-indigo-400 transition whitespace-nowrap shrink-0 shadow-2xs"
          >
            {prompt}
          </button>
        ))}
      </div>

      {/* Chat Messages */}
      <div className="flex-1 p-4 overflow-y-auto space-y-4">
        {messages.map((msg, i) => (
          <div
            key={i}
            className={`flex flex-col ${msg.role === "user" ? "items-end" : "items-start"}`}
          >
            <div
              className={`max-w-[88%] text-xs leading-relaxed rounded-2xl p-3.5 shadow-2xs ${
                msg.role === "user"
                  ? "bg-indigo-600 text-white rounded-br-none"
                  : "bg-slate-50 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700/60 text-slate-800 dark:text-slate-200 rounded-bl-none whitespace-pre-wrap font-sans"
              }`}
            >
              <div className="flex items-center justify-between mb-1 gap-4 opacity-75">
                <span className="text-[10px] font-bold uppercase tracking-wider">
                  {msg.role === "user" ? "You" : "Codebase AI"}
                </span>
                {msg.role === "assistant" && (
                  <button
                    onClick={() => copyToClipboard(msg.content)}
                    className="hover:text-indigo-500 text-[10px] transition"
                    title="Copy answer"
                  >
                    Copy
                  </button>
                )}
              </div>
              <div className="text-xs break-words">{msg.content}</div>

              {/* Source citations */}
              {msg.sources && msg.sources.length > 0 && (
                <div className="mt-3 pt-2.5 border-t border-slate-200 dark:border-slate-700/60">
                  <p className="text-[10px] font-semibold text-slate-400 mb-1.5 uppercase tracking-wider">
                    Referenced Sources:
                  </p>
                  <div className="flex flex-wrap gap-1.5">
                    {msg.sources.map((src, sIdx) => {
                      const fileName = src.file_path ? src.file_path.split("/").pop() : "file";
                      return (
                        <button
                          key={sIdx}
                          onClick={() => onOpenFile && onOpenFile(src.file_path)}
                          className="px-2 py-0.5 rounded-md bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 font-mono text-[10px] text-indigo-600 dark:text-indigo-400 hover:border-indigo-500 transition flex items-center gap-1"
                          title={`Click to open ${src.file_path} in code viewer`}
                        >
                          <span>📄 {fileName}</span>
                          {src.chunk_index != null && (
                            <span className="text-slate-400 text-[9px]">#{src.chunk_index}</span>
                          )}
                        </button>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex items-center gap-2 p-3.5 bg-slate-50 dark:bg-slate-800/60 rounded-2xl border border-slate-200 dark:border-slate-800 w-fit text-xs text-slate-500">
            <Spinner size={3} />
            <span>Analyzing codebase chunks & generating response...</span>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Box */}
      <div className="p-3 border-t border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/40">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSend();
          }}
          className="flex items-center gap-2"
        >
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={loading}
            placeholder={activeFile ? `Ask about ${activeFile.split("/").pop()} or anything...` : "Ask a question about this repository (Enter to send)..."}
            className="flex-1 px-3.5 py-2.5 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-xs text-slate-900 dark:text-white placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition"
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="px-4 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-semibold transition disabled:opacity-50 shadow-sm flex items-center gap-1.5 shrink-0"
          >
            {loading ? <Spinner size={3} /> : (
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
              </svg>
            )}
            Send
          </button>
        </form>
      </div>
    </div>
  );
}

// ─── IDE Workspace Tab (Explorer + Code Viewer + Companion Chat) ───────────

function IDEWorkspaceTab({ codebase, codebaseId, onOpenFileFromChat }) {
  const { showToast } = useToast();
  const [selectedFile, setSelectedFile] = useState(null);
  const [viewMode, setViewMode] = useState("code"); // "code" | "explanation"
  const [codeContent, setCodeContent] = useState("");
  const [loadingCode, setLoadingCode] = useState(false);
  const [codeError, setCodeError] = useState("");
  const [explanation, setExplanation] = useState("");
  const [explaining, setExplaining] = useState(false);
  const [filter, setFilter] = useState("");
  const [showCompanionChat, setShowCompanionChat] = useState(true);

  const files = codebase?.files || [];
  const filtered = filter
    ? files.filter((f) => f.relative_path.toLowerCase().includes(filter.toLowerCase()))
    : files;

  // Auto-select first file on mount
  useEffect(() => {
    if (files.length > 0 && !selectedFile) {
      loadFile(files[0]);
    }
  }, [files]);

  async function loadFile(file) {
    setSelectedFile(file);
    setCodeContent("");
    setCodeError("");
    setExplanation("");

    setLoadingCode(true);
    try {
      const data = await getFileContent(codebaseId, file.relative_path);
      setCodeContent(data.content || "");
    } catch (err) {
      setCodeError(err.message || "Failed to load file contents");
    } finally {
      setLoadingCode(false);
    }
  }

  async function loadExplanation(file) {
    setViewMode("explanation");
    if (explanation) return;
    setExplaining(true);
    try {
      const data = await explainFile(codebaseId, file.relative_path);
      setExplanation(data.explanation || "No explanation returned.");
    } catch (err) {
      showToast(err.message || "Failed to generate file explanation", "error");
    } finally {
      setExplaining(false);
    }
  }

  function handleSelectFromChat(relPath) {
    const match = files.find((f) => f.relative_path === relPath || f.relative_path.endsWith(relPath));
    if (match) {
      loadFile(match);
      setViewMode("code");
    }
  }

  return (
    <div className="space-y-4">
      {/* IDE Top Controls */}
      <div className="flex items-center justify-between pb-2 border-b border-slate-200 dark:border-slate-800">
        <div className="flex items-center gap-2">
          <span className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
            Interactive IDE Workspace
          </span>
          <span className="text-xs text-slate-400">·</span>
          <span className="text-xs font-mono text-indigo-600 dark:text-indigo-400 font-semibold">
            {selectedFile ? selectedFile.relative_path : "No file selected"}
          </span>
        </div>

        <button
          onClick={() => setShowCompanionChat(!showCompanionChat)}
          className={`px-3 py-1.5 rounded-xl border text-xs font-semibold transition flex items-center gap-1.5 ${
            showCompanionChat
              ? "bg-indigo-50 dark:bg-indigo-950/40 border-indigo-200 dark:border-indigo-800 text-indigo-600 dark:text-indigo-400"
              : "border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800"
          }`}
        >
          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
          </svg>
          {showCompanionChat ? "Hide AI Companion" : "Show AI Companion"}
        </button>
      </div>

      {/* 3-Column IDE Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
        {/* Left Column: File Explorer (3 cols) */}
        <div className="lg:col-span-3 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl p-4 shadow-sm space-y-3">
          <div className="flex items-center justify-between pb-2 border-b border-slate-100 dark:border-slate-800">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300">
              Explorer ({files.length})
            </span>
          </div>

          <input
            type="text"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            placeholder="Search files..."
            className="w-full px-3 py-1.5 text-xs bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-slate-900 dark:text-white placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />

          <div className="space-y-1 max-h-[600px] overflow-y-auto pr-1">
            {filtered.length === 0 ? (
              <p className="text-xs text-slate-400 text-center py-6">No matching files</p>
            ) : (
              filtered.map((file) => {
                const isSelected = selectedFile?.relative_path === file.relative_path;
                return (
                  <button
                    key={file.relative_path}
                    onClick={() => loadFile(file)}
                    className={`w-full text-left px-2.5 py-2 rounded-xl text-xs transition flex items-center gap-2 ${
                      isSelected
                        ? "bg-indigo-600 text-white shadow-2xs font-semibold"
                        : "text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800/80"
                    }`}
                  >
                    <span className={`text-[9px] font-mono uppercase px-1.5 py-0.5 rounded ${
                      isSelected
                        ? "bg-white/20 text-white"
                        : "bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400"
                    }`}>
                      {file.extension?.replace(".", "") || "txt"}
                    </span>
                    <span className="truncate">{file.relative_path}</span>
                  </button>
                );
              })
            )}
          </div>
        </div>

        {/* Center Column: Code Viewer / Syntax Inspector */}
        <div className={showCompanionChat ? "lg:col-span-5" : "lg:col-span-9"}>
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl p-5 shadow-sm space-y-4">
            {/* File Viewer Toolbar */}
            <div className="flex items-center justify-between pb-3 border-b border-slate-100 dark:border-slate-800">
              <div className="flex items-center gap-2 truncate pr-2">
                <span className="text-xs font-bold text-slate-900 dark:text-white truncate">
                  {selectedFile ? selectedFile.relative_path : "Select a file"}
                </span>
                {codeContent && (
                  <span className="text-[10px] text-slate-400 shrink-0">
                    ({codeContent.split("\n").length} lines)
                  </span>
                )}
              </div>

              <div className="flex items-center gap-2 shrink-0">
                <div className="flex bg-slate-100 dark:bg-slate-800 p-0.5 rounded-xl border border-slate-200 dark:border-slate-700">
                  <button
                    onClick={() => setViewMode("code")}
                    className={`px-2.5 py-1 text-xs font-semibold rounded-lg transition ${
                      viewMode === "code"
                        ? "bg-white dark:bg-slate-900 text-indigo-600 dark:text-indigo-400 shadow-2xs"
                        : "text-slate-500 hover:text-slate-900 dark:hover:text-white"
                    }`}
                  >
                    Code
                  </button>
                  <button
                    onClick={() => selectedFile && loadExplanation(selectedFile)}
                    className={`px-2.5 py-1 text-xs font-semibold rounded-lg transition ${
                      viewMode === "explanation"
                        ? "bg-white dark:bg-slate-900 text-indigo-600 dark:text-indigo-400 shadow-2xs"
                        : "text-slate-500 hover:text-slate-900 dark:hover:text-white"
                    }`}
                  >
                    AI Explain
                  </button>
                </div>

                {codeContent && (
                  <button
                    onClick={() => {
                      navigator.clipboard.writeText(codeContent);
                      showToast("Code copied to clipboard", "info");
                    }}
                    className="p-1.5 rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500 dark:text-slate-400 transition"
                    title="Copy code"
                  >
                    <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                    </svg>
                  </button>
                )}
              </div>
            </div>

            {/* View Mode: Code with Line Numbers */}
            {viewMode === "code" && (
              <>
                {loadingCode && <LoadingState message="Loading source code…" />}
                {codeError && <ErrorBox message={codeError} />}
                {!loadingCode && !codeError && codeContent && (
                  <div className="relative font-mono text-xs rounded-2xl overflow-hidden border border-slate-200 dark:border-slate-800 bg-slate-950 text-slate-100 shadow-inner max-h-[650px] overflow-y-auto">
                    <div className="flex">
                      {/* Line Numbers */}
                      <div className="select-none py-4 px-3 text-right text-slate-600 bg-slate-900/60 border-r border-slate-800 shrink-0">
                        {codeContent.split("\n").map((_, i) => (
                          <div key={i} className="leading-relaxed">{i + 1}</div>
                        ))}
                      </div>
                      {/* Code Content */}
                      <pre className="py-4 px-4 overflow-x-auto flex-1 leading-relaxed text-slate-200">
                        <code>{codeContent}</code>
                      </pre>
                    </div>
                  </div>
                )}
              </>
            )}

            {/* View Mode: AI Explanation */}
            {viewMode === "explanation" && (
              <>
                {explaining && <LoadingState message="Analyzing AST & generating explanation…" />}
                {!explaining && explanation && (
                  <div className="p-4 rounded-2xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-800 text-xs text-slate-800 dark:text-slate-200 whitespace-pre-wrap leading-relaxed max-h-[650px] overflow-y-auto font-sans">
                    {explanation}
                  </div>
                )}
              </>
            )}
          </div>
        </div>

        {/* Right Column: AI Companion Chat (4 cols when open) */}
        {showCompanionChat && (
          <div className="lg:col-span-4 h-[750px]">
            <AIChatAssistant
              codebaseId={codebaseId}
              activeFile={selectedFile?.relative_path}
              onOpenFile={handleSelectFromChat}
              isCompact={true}
            />
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Semantic Search Tab ───────────────────────────────────────────────────

function SearchTab({ codebaseId }) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [history, setHistory] = useState([]);

  async function handleSearch(e) {
    e.preventDefault();
    if (!query.trim()) return;
    setLoading(true);
    setError("");
    try {
      const data = await searchCodebase(codebaseId, query, history);
      setResults(data);
      setHistory((prev) => [
        ...prev,
        { role: "user", content: query },
        { role: "assistant", content: data.answer },
      ]);
      setQuery("");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <Panel>
      <PanelHeader title="Semantic Vector Search" subtitle="Natural language vector search powered by sentence-transformers & MongoDB Atlas" />

      {history.length > 0 && (
        <div className="space-y-3 mb-5 max-h-80 overflow-y-auto pr-1">
          {history.map((msg, i) => (
            <div
              key={i}
              className={`text-xs rounded-2xl p-4 leading-relaxed ${
                msg.role === "user"
                  ? "bg-indigo-600 text-white ml-8 shadow-sm"
                  : "bg-slate-50 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700/60 text-slate-800 dark:text-slate-200 mr-8 whitespace-pre-wrap"
              }`}
            >
              <p className="text-[10px] font-bold uppercase mb-1 opacity-70">
                {msg.role === "user" ? "You" : "Semantic Answer"}
              </p>
              {msg.content}
            </div>
          ))}
        </div>
      )}

      {results?.sources?.length > 0 && (
        <div className="mb-5 p-3 rounded-2xl bg-slate-50 dark:bg-slate-800/40 border border-slate-200 dark:border-slate-800">
          <p className="text-[11px] font-bold text-slate-500 dark:text-slate-400 mb-2 uppercase tracking-wider">
            Attributed Sources
          </p>
          <div className="flex flex-wrap gap-2">
            {results.sources.map((s, i) => (
              <span key={i} className="text-xs bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-indigo-600 dark:text-indigo-400 rounded-lg px-2.5 py-1 font-mono">
                {s.file_path ? s.file_path.replace(/\\/g, "/").split("/").pop() : "source"} {s.score != null ? `(${(s.score * 100).toFixed(0)}%)` : ""}
              </span>
            ))}
          </div>
        </div>
      )}

      {error && <ErrorBox message={error} />}

      <form onSubmit={handleSearch} className="flex gap-3 mt-3">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="e.g. How does user authentication work in this repository?"
          disabled={loading}
          className="flex-1 px-4 py-2.5 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-slate-900 dark:text-white placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 text-xs"
        />
        <button
          type="submit"
          disabled={loading || !query.trim()}
          className="px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs transition disabled:opacity-50"
        >
          {loading ? <Spinner size={4} /> : "Search"}
        </button>
      </form>
    </Panel>
  );
}

// ─── Architecture Tab ──────────────────────────────────────────────────────

function ArchitectureTab({ codebaseId }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function run() {
    setLoading(true);
    setError("");
    try {
      const result = await getArchitecture(codebaseId);
      setData(result);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <Panel>
      <PanelHeader
        title="AST Architecture Analysis"
        subtitle="Automated architectural mapping of modules, API routes, and dependency relationships"
        rightElement={
          data && (
            <button onClick={run} className="text-xs font-semibold text-indigo-600 dark:text-indigo-400 hover:underline">
              Re-analyze
            </button>
          )
        }
      />

      {!data && !loading && !error && (
        <div className="text-center py-10">
          <button
            onClick={run}
            className="px-6 py-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs transition shadow-md shadow-indigo-600/20"
          >
            Analyze Repository Architecture
          </button>
        </div>
      )}

      {loading && <LoadingState message="Extracting AST classes, functions, and relationships…" />}
      {error && <ErrorBox message={error} onRetry={run} />}

      {data && (
        <div className="space-y-6">
          <div className="grid grid-cols-3 gap-4">
            <div className="p-4 rounded-2xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-800 text-center">
              <p className="text-2xl font-bold text-slate-900 dark:text-white">{data.total_files}</p>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">Source Files</p>
            </div>
            <div className="p-4 rounded-2xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-800 text-center">
              <p className="text-2xl font-bold text-indigo-600 dark:text-indigo-400">{data.total_routes}</p>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">API Endpoints</p>
            </div>
            <div className="p-4 rounded-2xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-800 text-center">
              <p className="text-2xl font-bold text-emerald-600 dark:text-emerald-400">{data.total_relationships}</p>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">Module Links</p>
            </div>
          </div>

          <div className="p-5 rounded-2xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-800 text-xs text-slate-800 dark:text-slate-200 whitespace-pre-wrap leading-relaxed max-h-[500px] overflow-y-auto font-sans">
            {data.architecture_explanation}
          </div>
        </div>
      )}
    </Panel>
  );
}

// ─── Issues & Fixes Tab ───────────────────────────────────────────────────

function IssuesTab({ codebaseId }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [fixTarget, setFixTarget] = useState(null);
  const [fixData, setFixData] = useState(null);
  const [fixing, setFixing] = useState(false);
  const [fixError, setFixError] = useState("");

  async function run() {
    setLoading(true);
    setError("");
    setData(null);
    try {
      const result = await getIssues(codebaseId);
      setData(result);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleFix(issue) {
    setFixTarget(issue);
    setFixData(null);
    setFixError("");
    setFixing(true);
    try {
      const result = await getFix(codebaseId, issue.file_path, issue.line_number);
      setFixData(result);
    } catch (err) {
      setFixError(err.message);
    } finally {
      setFixing(false);
    }
  }

  return (
    <div className="space-y-6">
      <Panel>
        <PanelHeader
          title="Code Quality & Security Inspection"
          subtitle="AST scanner checking for bare exceptions, unused imports, anti-patterns, and vulnerabilities"
          rightElement={
            data && (
              <button onClick={run} className="text-xs font-semibold text-indigo-600 dark:text-indigo-400 hover:underline">
                Re-scan
              </button>
            )
          }
        />

        {!data && !loading && !error && (
          <div className="text-center py-10">
            <button
              onClick={run}
              className="px-6 py-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs transition shadow-md shadow-indigo-600/20"
            >
              Scan Repository for Issues
            </button>
          </div>
        )}

        {loading && <LoadingState message="Scanning repository AST for quality issues…" />}
        {error && <ErrorBox message={error} onRetry={run} />}

        {data && (
          <div className="space-y-5">
            <div className="flex gap-3 flex-wrap">
              {Object.entries(data.severity_counts || {}).map(([sev, count]) => (
                <div key={sev} className="p-3.5 rounded-2xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-800 text-center min-w-[90px]">
                  <p className="text-xl font-bold text-slate-900 dark:text-white">{count}</p>
                  <p className="text-[11px] text-slate-500 dark:text-slate-400 capitalize">{sev} severity</p>
                </div>
              ))}
              <div className="p-3.5 rounded-2xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-800 text-center min-w-[90px]">
                <p className="text-xl font-bold text-slate-900 dark:text-white">{data.scanned_files}</p>
                <p className="text-[11px] text-slate-500 dark:text-slate-400">Scanned</p>
              </div>
            </div>

            {data.issues.length === 0 ? (
              <div className="p-6 rounded-2xl bg-emerald-50 dark:bg-emerald-950/20 border border-emerald-200 dark:border-emerald-800/40 text-xs text-emerald-700 dark:text-emerald-300">
                🎉 No issues detected! Code adheres to scanned best practices.
              </div>
            ) : (
              <div className="space-y-2.5 max-h-96 overflow-y-auto pr-1">
                {data.issues.map((issue, i) => (
                  <div
                    key={i}
                    className="p-3.5 rounded-2xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-800 flex items-start justify-between gap-4 text-xs"
                  >
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <SeverityBadge severity={issue.severity} />
                        <span className="font-mono font-semibold text-slate-900 dark:text-white">
                          {issue.issue_type}
                        </span>
                      </div>
                      <p className="text-slate-600 dark:text-slate-400">{issue.message}</p>
                      <p className="text-slate-400 font-mono text-[11px] mt-1">
                        {issue.file_path}:{issue.line_number}
                      </p>
                    </div>

                    <button
                      onClick={() => handleFix(issue)}
                      className="px-3 py-1.5 rounded-xl bg-indigo-600/10 hover:bg-indigo-600 text-indigo-600 hover:text-white dark:text-indigo-400 border border-indigo-500/20 text-xs font-semibold transition shrink-0"
                    >
                      AI Fix
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </Panel>

      {/* Suggested Fix Panel */}
      {fixTarget && (
        <Panel>
          <PanelHeader
            title="AI Code Fix Generator"
            subtitle={`Proposed fix for issue in ${fixTarget.file_path}:${fixTarget.line_number}`}
          />
          {fixing && <LoadingState message="Generating line-level AI replacement fix…" />}
          {fixError && <ErrorBox message={fixError} />}
          {fixData && (
            <div className="p-4 rounded-2xl bg-slate-950 text-slate-200 font-mono text-xs whitespace-pre-wrap leading-relaxed max-h-80 overflow-y-auto border border-slate-800">
              {fixData.suggested_fix}
            </div>
          )}
        </Panel>
      )}
    </div>
  );
}

// ─── Improvements Tab ──────────────────────────────────────────────────────

function ImprovementsTab({ codebaseId }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function run() {
    setLoading(true);
    setError("");
    try {
      const result = await getImprovements(codebaseId);
      setData(result);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <Panel>
      <PanelHeader
        title="AI Architectural Improvements"
        subtitle="Targeted refactoring and quality recommendations generated for this repository"
        rightElement={
          data && (
            <button onClick={run} className="text-xs font-semibold text-indigo-600 dark:text-indigo-400 hover:underline">
              Re-generate
            </button>
          )
        }
      />

      {!data && !loading && !error && (
        <div className="text-center py-10">
          <button
            onClick={run}
            className="px-6 py-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs transition shadow-md shadow-indigo-600/20"
          >
            Generate Improvement Recommendations
          </button>
        </div>
      )}

      {loading && <LoadingState message="Analyzing project patterns and formulating improvement strategies…" />}
      {error && <ErrorBox message={error} onRetry={run} />}

      {data && (
        <div className="p-5 rounded-2xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-800 text-xs text-slate-800 dark:text-slate-200 whitespace-pre-wrap leading-relaxed max-h-[500px] overflow-y-auto font-sans">
          {typeof data.improvements === "string"
            ? data.improvements
            : JSON.stringify(data.improvements, null, 2)}
        </div>
      )}
    </Panel>
  );
}

// ─── Overview Tab ──────────────────────────────────────────────────────────

function OverviewTab({ codebaseId }) {
  const [summary, setSummary] = useState(null);
  const [tech, setTech] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([
      getSummary(codebaseId),
      getTechnologies(codebaseId)
    ])
      .then(([sData, tData]) => {
        setSummary(sData);
        setTech(tData);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [codebaseId]);

  if (loading) return <LoadingState message="Loading repository summary…" />;
  if (error) return <ErrorBox message={error} />;

  return (
    <div className="space-y-6">
      <Panel>
        <PanelHeader title="Detected Technologies" subtitle="Languages and frameworks identified across repository files" />
        {tech?.technologies?.length > 0 ? (
          <div className="flex flex-wrap gap-3">
            {tech.technologies.map((t) => (
              <div key={t.name} className="p-3.5 rounded-2xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-800 flex items-center gap-3">
                <span className="font-bold text-xs text-indigo-600 dark:text-indigo-400">{t.name}</span>
                <span className="text-[10px] text-slate-500 dark:text-slate-400 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 px-2 py-0.5 rounded-md font-mono">
                  {t.evidence?.join(", ")}
                </span>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-xs text-slate-500">No standard technologies detected.</p>
        )}
      </Panel>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        <Panel>
          <PanelHeader title="File Types Distribution" subtitle="Count of files by extension" />
          <div className="space-y-2 max-h-60 overflow-y-auto">
            {summary?.file_types?.map((ft) => (
              <div key={ft.extension} className="flex items-center justify-between py-2 px-3 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200/60 dark:border-slate-800 text-xs">
                <span className="font-mono text-slate-700 dark:text-slate-300">{ft.extension}</span>
                <span className="font-bold text-indigo-600 dark:text-indigo-400">{ft.count} files</span>
              </div>
            ))}
          </div>
        </Panel>

        <Panel>
          <PanelHeader title="Top-Level Directories" subtitle="Folder structure overview" />
          <div className="space-y-2 max-h-60 overflow-y-auto">
            {summary?.top_level_directories?.length > 0 ? (
              summary.top_level_directories.map((dir) => (
                <div key={dir.directory} className="flex items-center justify-between py-2 px-3 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200/60 dark:border-slate-800 text-xs">
                  <span className="font-mono text-slate-700 dark:text-slate-300">📁 {dir.directory}</span>
                  <span className="font-bold text-indigo-600 dark:text-indigo-400">{dir.file_count} files</span>
                </div>
              ))
            ) : (
              <p className="text-xs text-slate-400">Single root directory repository</p>
            )}
          </div>
        </Panel>
      </div>
    </div>
  );
}

// ─── Main Codebase Page ───────────────────────────────────────────────────

const TABS = [
  { id: "tab-ide",          key: "ide",          label: "IDE Workspace",  icon: <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" /></svg> },
  { id: "tab-chat",         key: "chat",         label: "AI Chat",        icon: <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" /></svg> },
  { id: "tab-overview",     key: "overview",     label: "Overview",       icon: <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" /></svg> },
  { id: "tab-search",       key: "search",       label: "Vector Search",  icon: <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" /></svg> },
  { id: "tab-architecture", key: "architecture", label: "Architecture",   icon: <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM4 13a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zM16 13a1 1 0 011-1h2a1 1 0 011 1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-6z" /></svg> },
  { id: "tab-issues",       key: "issues",       label: "Issues & Fixes", icon: <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" /></svg> },
  { id: "tab-improvements", key: "improvements", label: "Improvements",   icon: <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" /></svg> },
];

export default function CodebasePage() {
  const { codebaseId } = useParams();
  const router = useRouter();
  const { user, loading: authLoading } = useAuth();

  const [codebase, setCodebase] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [activeTab, setActiveTab] = useState("ide");

  useEffect(() => {
    if (authLoading) return;
    if (!user) { router.replace("/login"); return; }
    fetchCodebase();
  }, [user, authLoading, codebaseId]);

  async function fetchCodebase() {
    setLoading(true);
    setError("");
    try {
      const data = await getCodebaseDetails(codebaseId);
      setCodebase(data);
    } catch (err) {
      setError(err.message || "Failed to load codebase details");
    } finally {
      setLoading(false);
    }
  }

  if (authLoading || loading) {
    return (
      <AppShell title="Loading Workspace...">
        <div className="flex items-center justify-center py-24">
          <Spinner size={8} />
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell
      title={codebase?.codebase_name || "Codebase Workspace"}
      breadcrumbs={[
        { label: "Dashboard", href: "/dashboard" },
        { label: codebase?.codebase_name || "Workspace" },
      ]}
    >
      <div className="space-y-6">
        {error ? (
          <div className="bg-rose-50 dark:bg-rose-950/20 border border-rose-200 dark:border-rose-800 rounded-3xl p-8 text-sm text-rose-600 dark:text-rose-300">
            {error}
          </div>
        ) : (
          <>
            {/* Codebase Meta Header */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-200 dark:border-slate-800">
              <div>
                <h1 className="text-2xl font-bold text-slate-900 dark:text-white tracking-tight flex items-center gap-3">
                  {codebase?.codebase_name}
                  <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400 border border-indigo-200 dark:border-indigo-800">
                    {codebase?.total_files} files
                  </span>
                </h1>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                  Repository ID: <span className="font-mono">{codebaseId}</span> · uploaded{" "}
                  {codebase?.created_at
                    ? new Date(codebase.created_at).toLocaleDateString("en-GB", {
                        day: "numeric", month: "short", year: "numeric",
                      })
                    : "—"}
                </p>
              </div>

              <div className="flex items-center gap-2">
                <Link
                  href="/upload"
                  className="px-3.5 py-2 rounded-xl border border-slate-200 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800 text-xs font-semibold text-slate-700 dark:text-slate-300 transition"
                >
                  Upload Another Project
                </Link>
              </div>
            </div>

            {/* Tab Bar */}
            <div className="flex gap-1.5 flex-wrap pb-2 border-b border-slate-200 dark:border-slate-800 overflow-x-auto no-scrollbar">
              {TABS.map((tab) => (
                <Tab
                  key={tab.key}
                  id={tab.id}
                  label={tab.label}
                  icon={tab.icon}
                  active={activeTab === tab.key}
                  onClick={() => setActiveTab(tab.key)}
                />
              ))}
            </div>

            {/* Tab Content */}
            <div className="mt-4">
              {activeTab === "ide"          && <IDEWorkspaceTab codebase={codebase} codebaseId={codebaseId} />}
              {activeTab === "chat"         && (
                <div className="h-[750px]">
                  <AIChatAssistant codebaseId={codebaseId} isCompact={false} />
                </div>
              )}
              {activeTab === "overview"     && <OverviewTab codebaseId={codebaseId} />}
              {activeTab === "search"       && <SearchTab codebaseId={codebaseId} />}
              {activeTab === "architecture" && <ArchitectureTab codebaseId={codebaseId} />}
              {activeTab === "issues"       && <IssuesTab codebaseId={codebaseId} />}
              {activeTab === "improvements" && <ImprovementsTab codebaseId={codebaseId} />}
            </div>
          </>
        )}
      </div>
    </AppShell>
  );
}
