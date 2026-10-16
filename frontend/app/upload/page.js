"use client";

import { useState, useRef } from "react";
import { useRouter } from "next/navigation";
import AppShell from "../components/AppShell";
import { useToast } from "../context/ToastContext";
import { uploadZip, uploadFiles, analyzeSingleFile } from "../lib/api";

const SUPPORTED_EXTS = [
  ".py", ".js", ".jsx", ".ts", ".tsx",
  ".java", ".cpp", ".c", ".h", ".html",
  ".css", ".json", ".md", ".sql"
];

function formatBytes(bytes) {
  if (bytes === 0) return "0 Bytes";
  const k = 1024;
  const sizes = ["Bytes", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
}

export default function UploadPage() {
  const router = useRouter();
  const { showToast } = useToast();

  const [mode, setMode] = useState("zip"); // "zip" | "files" | "single"
  const [dragActive, setDragActive] = useState(false);

  // Files staged
  const [zipFile, setZipFile] = useState(null);
  const [stagedFiles, setStagedFiles] = useState([]);
  const [codebaseName, setCodebaseName] = useState("");
  const [singleFile, setSingleFile] = useState(null);

  // Progress & State
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [singleResult, setSingleResult] = useState(null);
  const [analyzingSingle, setAnalyzingSingle] = useState(false);

  const fileInputRef = useRef(null);
  const folderInputRef = useRef(null);
  const singleInputRef = useRef(null);

  // Drag and drop handlers
  function handleDrag(e) {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  }

  function handleDrop(e) {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    const files = Array.from(e.dataTransfer.files || []);
    if (!files.length) return;

    if (mode === "zip") {
      const zf = files.find((f) => f.name.toLowerCase().endsWith(".zip"));
      if (zf) {
        setZipFile(zf);
        setCodebaseName(zf.name.replace(/\.zip$/i, ""));
      } else {
        showToast("Please drop a valid .zip archive file in this mode", "warning");
      }
    } else if (mode === "single") {
      setSingleFile(files[0]);
      setSingleResult(null);
    } else {
      // multi-files
      setStagedFiles((prev) => [...prev, ...files]);
    }
  }

  function handleZipSelect(e) {
    const file = e.target.files?.[0];
    if (file) {
      if (!file.name.toLowerCase().endsWith(".zip")) {
        showToast("Only .zip files are supported in ZIP mode", "warning");
        return;
      }
      setZipFile(file);
      setCodebaseName(file.name.replace(/\.zip$/i, ""));
    }
  }

  function handleFilesSelect(e) {
    const files = Array.from(e.target.files || []);
    if (files.length) {
      setStagedFiles((prev) => [...prev, ...files]);
    }
  }

  function handleSingleSelect(e) {
    const file = e.target.files?.[0];
    if (file) {
      setSingleFile(file);
      setSingleResult(null);
    }
  }

  function removeStagedFile(index) {
    setStagedFiles((prev) => prev.filter((_, i) => i !== index));
  }

  async function handleZipSubmit(e) {
    e.preventDefault();
    if (!zipFile) {
      showToast("Please select a ZIP archive first", "warning");
      return;
    }

    setUploading(true);
    setProgress(0);

    try {
      const res = await uploadZip(zipFile, (p) => setProgress(p));
      showToast("Codebase processed and indexed successfully!", "success");
      router.push(`/codebase/${res.codebase_id}`);
    } catch (err) {
      showToast(err.message || "Upload failed", "error");
    } finally {
      setUploading(false);
    }
  }

  async function handleFilesSubmit(e) {
    e.preventDefault();
    if (!stagedFiles.length) {
      showToast("Please add at least one source file", "warning");
      return;
    }

    setUploading(true);
    setProgress(0);

    try {
      const res = await uploadFiles(stagedFiles, codebaseName, (p) => setProgress(p));
      showToast("Files indexed and codebase created successfully!", "success");
      router.push(`/codebase/${res.codebase_id}`);
    } catch (err) {
      showToast(err.message || "Upload failed", "error");
    } finally {
      setUploading(false);
    }
  }

  async function handleSingleAnalyze(e) {
    e.preventDefault();
    if (!singleFile) {
      showToast("Please choose a file to analyze", "warning");
      return;
    }

    setAnalyzingSingle(true);
    setSingleResult(null);

    try {
      const res = await analyzeSingleFile(singleFile);
      setSingleResult(res);
      showToast("Instant analysis complete!", "success");
    } catch (err) {
      showToast(err.message || "Analysis failed", "error");
    } finally {
      setAnalyzingSingle(false);
    }
  }

  return (
    <AppShell title="Upload & Analyze">
      <div className="max-w-5xl mx-auto space-y-8">
        {/* Header */}
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white">
            Upload & Analyze Workspace
          </h2>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            Import complete repositories, multi-file modules, or run instant AST code inspection on single files.
          </p>
        </div>

        {/* Mode Selector Tabs */}
        <div className="flex border-b border-slate-200 dark:border-slate-800 gap-6">
          <button
            onClick={() => setMode("zip")}
            className={`pb-3 text-sm font-semibold transition border-b-2 flex items-center gap-2 ${
              mode === "zip"
                ? "border-indigo-600 text-indigo-600 dark:text-indigo-400"
                : "border-transparent text-slate-500 hover:text-slate-900 dark:hover:text-white"
            }`}
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
            </svg>
            ZIP Project Upload
          </button>

          <button
            onClick={() => setMode("files")}
            className={`pb-3 text-sm font-semibold transition border-b-2 flex items-center gap-2 ${
              mode === "files"
                ? "border-indigo-600 text-indigo-600 dark:text-indigo-400"
                : "border-transparent text-slate-500 hover:text-slate-900 dark:hover:text-white"
            }`}
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            Multiple Files / Folder
          </button>

          <button
            onClick={() => setMode("single")}
            className={`pb-3 text-sm font-semibold transition border-b-2 flex items-center gap-2 ${
              mode === "single"
                ? "border-indigo-600 text-indigo-600 dark:text-indigo-400"
                : "border-transparent text-slate-500 hover:text-slate-900 dark:hover:text-white"
            }`}
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
            Instant Single-File Inspector
          </button>
        </div>

        {/* Tab 1: ZIP Upload */}
        {mode === "zip" && (
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl p-8 shadow-sm space-y-6">
            <div
              onDragEnter={handleDrag}
              onDragLeave={handleDrag}
              onDragOver={handleDrag}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              className={`border-2 border-dashed rounded-3xl p-10 text-center cursor-pointer transition ${
                dragActive
                  ? "border-indigo-600 bg-indigo-50/50 dark:bg-indigo-950/20"
                  : "border-slate-300 dark:border-slate-700 hover:border-indigo-500 bg-slate-50/50 dark:bg-slate-800/40"
              }`}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".zip"
                className="hidden"
                onChange={handleZipSelect}
              />
              <div className="w-14 h-14 rounded-2xl bg-indigo-50 dark:bg-indigo-950/50 border border-indigo-200 dark:border-indigo-800 flex items-center justify-center mx-auto mb-4 text-indigo-600 dark:text-indigo-400">
                <svg className="w-7 h-7" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
                </svg>
              </div>
              <p className="text-base font-semibold text-slate-900 dark:text-white">
                {zipFile ? zipFile.name : "Drag & drop your repository ZIP here"}
              </p>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                {zipFile
                  ? `${formatBytes(zipFile.size)} · Click to change file`
                  : "or browse your local files (maximum 100 MB)"}
              </p>
            </div>

            {uploading && (
              <div className="space-y-2">
                <div className="flex justify-between text-xs font-semibold text-slate-600 dark:text-slate-400">
                  <span>Uploading and extracting repository...</span>
                  <span>{progress}%</span>
                </div>
                <div className="w-full bg-slate-200 dark:bg-slate-800 h-2 rounded-full overflow-hidden">
                  <div
                    className="bg-indigo-600 h-2 rounded-full transition-all duration-200"
                    style={{ width: `${progress}%` }}
                  />
                </div>
              </div>
            )}

            <div className="flex justify-end">
              <button
                type="button"
                onClick={handleZipSubmit}
                disabled={!zipFile || uploading}
                className="px-6 py-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-sm transition disabled:opacity-50 disabled:cursor-not-allowed shadow-md shadow-indigo-600/20 flex items-center gap-2"
              >
                {uploading && (
                  <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                  </svg>
                )}
                {uploading ? "Processing Codebase..." : "Upload & Analyze Codebase"}
              </button>
            </div>
          </div>
        )}

        {/* Tab 2: Multiple Files / Folder */}
        {mode === "files" && (
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl p-8 shadow-sm space-y-6">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                  Codebase / Project Name (optional)
                </label>
                <input
                  type="text"
                  placeholder="e.g. My Express API or Django Core"
                  value={codebaseName}
                  onChange={(e) => setCodebaseName(e.target.value)}
                  className="w-full px-3.5 py-2.5 bg-slate-50 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-xl text-slate-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              <div className="flex items-end gap-3">
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  className="px-4 py-2.5 rounded-xl border border-slate-300 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800 text-xs font-semibold text-slate-700 dark:text-slate-300 transition flex items-center gap-2"
                >
                  <svg className="w-4 h-4 text-indigo-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                  </svg>
                  Select Individual Files
                </button>
                <button
                  type="button"
                  onClick={() => folderInputRef.current?.click()}
                  className="px-4 py-2.5 rounded-xl border border-slate-300 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800 text-xs font-semibold text-slate-700 dark:text-slate-300 transition flex items-center gap-2"
                >
                  <svg className="w-4 h-4 text-indigo-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
                  </svg>
                  Select Entire Folder
                </button>
              </div>
            </div>

            <input
              ref={fileInputRef}
              type="file"
              multiple
              className="hidden"
              onChange={handleFilesSelect}
            />
            <input
              ref={folderInputRef}
              type="file"
              webkitdirectory=""
              directory=""
              className="hidden"
              onChange={handleFilesSelect}
            />

            {/* Drop Zone */}
            <div
              onDragEnter={handleDrag}
              onDragLeave={handleDrag}
              onDragOver={handleDrag}
              onDrop={handleDrop}
              className={`border-2 border-dashed rounded-3xl p-8 text-center transition ${
                dragActive
                  ? "border-indigo-600 bg-indigo-50/50 dark:bg-indigo-950/20"
                  : "border-slate-300 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-800/40"
              }`}
            >
              <p className="text-sm font-semibold text-slate-800 dark:text-slate-200">
                Drag & drop files or folder directly here
              </p>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                Supports .py, .js, .jsx, .ts, .tsx, .java, .cpp, .html, .css, .json, .md
              </p>
            </div>

            {/* Staged File List */}
            {stagedFiles.length > 0 && (
              <div className="space-y-3">
                <div className="flex items-center justify-between text-xs font-semibold text-slate-700 dark:text-slate-300">
                  <span>Staged Files ({stagedFiles.length})</span>
                  <button
                    onClick={() => setStagedFiles([])}
                    className="text-rose-500 hover:underline"
                  >
                    Clear all
                  </button>
                </div>
                <div className="max-h-60 overflow-y-auto space-y-1.5 pr-1">
                  {stagedFiles.map((file, idx) => (
                    <div
                      key={idx}
                      className="flex items-center justify-between p-2.5 rounded-xl bg-slate-50 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700/60 text-xs"
                    >
                      <div className="flex items-center gap-2.5 truncate pr-4">
                        <span className="px-1.5 py-0.5 rounded uppercase font-mono text-[10px] font-bold bg-indigo-100 dark:bg-indigo-950 text-indigo-600 dark:text-indigo-400">
                          {file.name.split(".").pop()}
                        </span>
                        <span className="font-medium text-slate-900 dark:text-white truncate">
                          {file.webkitRelativePath || file.name}
                        </span>
                        <span className="text-slate-400 shrink-0">({formatBytes(file.size)})</span>
                      </div>
                      <button
                        onClick={() => removeStagedFile(idx)}
                        className="text-slate-400 hover:text-rose-500 transition"
                      >
                        ✕
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {uploading && (
              <div className="space-y-2">
                <div className="flex justify-between text-xs font-semibold text-slate-600 dark:text-slate-400">
                  <span>Chunking and generating embeddings...</span>
                  <span>{progress}%</span>
                </div>
                <div className="w-full bg-slate-200 dark:bg-slate-800 h-2 rounded-full overflow-hidden">
                  <div
                    className="bg-indigo-600 h-2 rounded-full transition-all duration-200"
                    style={{ width: `${progress}%` }}
                  />
                </div>
              </div>
            )}

            <div className="flex justify-end">
              <button
                type="button"
                onClick={handleFilesSubmit}
                disabled={!stagedFiles.length || uploading}
                className="px-6 py-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-sm transition disabled:opacity-50 disabled:cursor-not-allowed shadow-md shadow-indigo-600/20 flex items-center gap-2"
              >
                {uploading && (
                  <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                  </svg>
                )}
                {uploading ? "Analyzing Files..." : `Process & Index ${stagedFiles.length} Files`}
              </button>
            </div>
          </div>
        )}

        {/* Tab 3: Instant Single-File Inspector */}
        {mode === "single" && (
          <div className="space-y-6">
            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl p-8 shadow-sm space-y-6">
              <div
                onDragEnter={handleDrag}
                onDragLeave={handleDrag}
                onDragOver={handleDrag}
                onDrop={handleDrop}
                onClick={() => singleInputRef.current?.click()}
                className={`border-2 border-dashed rounded-3xl p-8 text-center cursor-pointer transition ${
                  dragActive
                    ? "border-indigo-600 bg-indigo-50/50 dark:bg-indigo-950/20"
                    : "border-slate-300 dark:border-slate-700 hover:border-indigo-500 bg-slate-50/50 dark:bg-slate-800/40"
                }`}
              >
                <input
                  ref={singleInputRef}
                  type="file"
                  className="hidden"
                  onChange={handleSingleSelect}
                />
                <p className="text-sm font-semibold text-slate-800 dark:text-slate-200">
                  {singleFile ? singleFile.name : "Select or drop a single code file for instant AST inspection"}
                </p>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                  {singleFile ? `${formatBytes(singleFile.size)} · Click to change` : "Inspect functions, classes, API routes, and code quality issues without creating a project"}
                </p>
              </div>

              <div className="flex justify-end">
                <button
                  type="button"
                  onClick={handleSingleAnalyze}
                  disabled={!singleFile || analyzingSingle}
                  className="px-6 py-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-sm transition disabled:opacity-50 disabled:cursor-not-allowed shadow-md shadow-indigo-600/20 flex items-center gap-2"
                >
                  {analyzingSingle && (
                    <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                    </svg>
                  )}
                  {analyzingSingle ? "Inspecting AST..." : "Inspect Code File"}
                </button>
              </div>
            </div>

            {/* Instant Analysis Results */}
            {singleResult && (
              <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl p-8 shadow-sm space-y-6 animate-fade-in">
                <div className="flex items-center justify-between pb-4 border-b border-slate-200 dark:border-slate-800">
                  <div>
                    <h3 className="text-lg font-bold text-slate-900 dark:text-white">
                      Analysis Results: {singleResult.filename}
                    </h3>
                    <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                      Language: {singleResult.language} · {singleResult.line_count} lines · {formatBytes(singleResult.character_count)}
                    </p>
                  </div>
                  <div className="flex gap-2">
                    <span className="px-2.5 py-1 text-xs font-semibold rounded-lg bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 border border-indigo-500/20">
                      {singleResult.summary?.total_functions || 0} Functions
                    </span>
                    <span className="px-2.5 py-1 text-xs font-semibold rounded-lg bg-purple-500/10 text-purple-600 dark:text-purple-400 border border-purple-500/20">
                      {singleResult.summary?.total_classes || 0} Classes
                    </span>
                    <span className="px-2.5 py-1 text-xs font-semibold rounded-lg bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
                      {singleResult.summary?.total_routes || 0} Routes
                    </span>
                    <span className="px-2.5 py-1 text-xs font-semibold rounded-lg bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-500/20">
                      {singleResult.summary?.total_issues || 0} Issues
                    </span>
                  </div>
                </div>

                {/* Functions and Classes Grid */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {/* Functions */}
                  <div>
                    <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-3">
                      Functions & Methods ({singleResult.functions?.length || 0})
                    </h4>
                    {singleResult.functions?.length === 0 ? (
                      <p className="text-xs text-slate-400 italic">No functions detected</p>
                    ) : (
                      <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
                        {singleResult.functions.map((fn, idx) => (
                          <div
                            key={idx}
                            className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-800 text-xs"
                          >
                            <div className="flex items-center justify-between">
                              <span className="font-mono font-semibold text-slate-900 dark:text-white">
                                {fn.name}()
                              </span>
                              <span className="text-[11px] text-slate-400">
                                Line {fn.line_number}
                              </span>
                            </div>
                            {fn.parameters && fn.parameters.length > 0 && (
                              <p className="text-[11px] text-slate-500 mt-1 font-mono">
                                args: ({fn.parameters.join(", ")})
                              </p>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Classes */}
                  <div>
                    <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-3">
                      Classes ({singleResult.classes?.length || 0})
                    </h4>
                    {singleResult.classes?.length === 0 ? (
                      <p className="text-xs text-slate-400 italic">No classes detected</p>
                    ) : (
                      <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
                        {singleResult.classes.map((cls, idx) => (
                          <div
                            key={idx}
                            className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-800 text-xs"
                          >
                            <div className="flex items-center justify-between">
                              <span className="font-mono font-semibold text-slate-900 dark:text-white">
                                class {cls.name}
                              </span>
                              <span className="text-[11px] text-slate-400">
                                Line {cls.line_number}
                              </span>
                            </div>
                            {cls.methods && cls.methods.length > 0 && (
                              <p className="text-[11px] text-slate-500 mt-1">
                                Methods: {cls.methods.map((m) => m.name).join(", ")}
                              </p>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>

                {/* API Routes */}
                {singleResult.routes && singleResult.routes.length > 0 && (
                  <div>
                    <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-3">
                      API Endpoints ({singleResult.routes.length})
                    </h4>
                    <div className="space-y-2">
                      {singleResult.routes.map((rt, idx) => (
                        <div
                          key={idx}
                          className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-800 flex items-center justify-between text-xs"
                        >
                          <div className="flex items-center gap-2">
                            <span className="px-2 py-0.5 rounded font-bold uppercase font-mono text-[10px] bg-indigo-500 text-white">
                              {rt.methods ? rt.methods.join(", ") : "ROUTE"}
                            </span>
                            <span className="font-mono font-semibold text-slate-900 dark:text-white">
                              {rt.path}
                            </span>
                          </div>
                          <span className="text-[11px] text-slate-400">
                            handler: {rt.function_name} (L{rt.line_number})
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Code Issues */}
                <div>
                  <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-3">
                    Quality & Security Issues ({singleResult.issues?.length || 0})
                  </h4>
                  {singleResult.issues?.length === 0 ? (
                    <div className="p-4 rounded-xl bg-emerald-50 dark:bg-emerald-950/20 border border-emerald-200 dark:border-emerald-800/40 text-xs text-emerald-700 dark:text-emerald-300">
                      ✓ Clean code! No quality or syntax issues detected in this file.
                    </div>
                  ) : (
                    <div className="space-y-2">
                      {singleResult.issues.map((iss, idx) => (
                        <div
                          key={idx}
                          className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-800 flex items-start justify-between text-xs gap-3"
                        >
                          <div>
                            <div className="flex items-center gap-2 mb-1">
                              <span
                                className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                                  iss.severity === "high"
                                    ? "bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-500/20"
                                    : iss.severity === "medium"
                                    ? "bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20"
                                    : "bg-sky-500/10 text-sky-600 dark:text-sky-400 border border-sky-500/20"
                                }`}
                              >
                                {iss.severity}
                              </span>
                              <span className="font-mono text-slate-900 dark:text-white font-medium">
                                {iss.issue_type}
                              </span>
                            </div>
                            <p className="text-slate-600 dark:text-slate-400 text-xs">
                              {iss.message}
                            </p>
                          </div>
                          <span className="text-[11px] font-mono text-slate-400 shrink-0">
                            Line {iss.line_number}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Supported Formats Legend */}
        <div className="p-6 rounded-3xl bg-slate-100/70 dark:bg-slate-900/40 border border-slate-200 dark:border-slate-800">
          <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-2">
            Supported Source Formats
          </h4>
          <div className="flex flex-wrap gap-2">
            {SUPPORTED_EXTS.map((ext) => (
              <span
                key={ext}
                className="px-2.5 py-1 rounded-lg bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-xs font-mono text-slate-700 dark:text-slate-300"
              >
                {ext}
              </span>
            ))}
          </div>
          <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-3">
            Note: Secret files (.env, private keys, certificates) and build artifacts (node_modules, .git, venv) are automatically filtered for safety.
          </p>
        </div>
      </div>
    </AppShell>
  );
}
