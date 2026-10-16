// Central API client for all backend requests
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

export function getToken() {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("access_token");
}

export async function apiFetch(path, options = {}) {
  const token = getToken();
  const headers = {
    ...(options.headers || {}),
  };

  // Only set Content-Type to JSON when we're not sending FormData
  if (!(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });

  if (res.status === 401) {
    // Token expired or invalid — clear storage and redirect to login
    if (typeof window !== "undefined") {
      localStorage.removeItem("access_token");
      localStorage.removeItem("user");
      window.location.href = "/login";
    }
    throw new Error("Session expired. Please log in again.");
  }

  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const json = await res.json();
      detail = json.detail || detail;
    } catch (_) {}
    throw new Error(detail);
  }

  const contentType = res.headers.get("content-type") || "";
  if (contentType.includes("application/json")) {
    return res.json();
  }
  return res.text();
}

// ---- Auth ----------------------------------------------------------------

export async function login(email, password) {
  const form = new URLSearchParams();
  form.append("username", email);
  form.append("password", password);

  const res = await fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: form.toString(),
  });

  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const json = await res.json();
      detail = json.detail || detail;
    } catch (_) {}
    throw new Error(detail);
  }

  return res.json();
}

export async function adminLogin(email, password) {
  const form = new URLSearchParams();
  form.append("username", email);
  form.append("password", password);

  const res = await fetch(`${API_BASE}/auth/admin-login`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: form.toString(),
  });

  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const json = await res.json();
      detail = json.detail || detail;
    } catch (_) {}
    throw new Error(detail);
  }

  return res.json();
}

export async function signup(name, email, password) {
  return apiFetch("/auth/signup", {
    method: "POST",
    body: JSON.stringify({ name, email, password }),
  });
}

export async function getMe() {
  return apiFetch("/auth/me");
}

export async function updateProfile(name) {
  return apiFetch("/auth/profile", {
    method: "PUT",
    body: JSON.stringify({ name }),
  });
}

export async function changePassword(oldPassword, newPassword) {
  return apiFetch("/auth/change-password", {
    method: "POST",
    body: JSON.stringify({ old_password: oldPassword, new_password: newPassword }),
  });
}

export async function forgotPassword(email) {
  return apiFetch("/auth/forgot-password", {
    method: "POST",
    body: JSON.stringify({ email }),
  });
}

export async function resetPassword(token, newPassword) {
  return apiFetch("/auth/reset-password", {
    method: "POST",
    body: JSON.stringify({ token, new_password: newPassword }),
  });
}

export async function sendVerification() {
  return apiFetch("/auth/send-verification", {
    method: "POST",
  });
}

export async function verifyEmail(otp) {
  return apiFetch("/auth/verify-email", {
    method: "POST",
    body: JSON.stringify({ otp }),
  });
}

// ---- Codebase ------------------------------------------------------------

export async function listCodebases() {
  return apiFetch("/codebase/list");
}

export async function getUserStats() {
  return apiFetch("/codebase/stats");
}

export async function getCodebaseDetails(codebaseId) {
  return apiFetch(`/codebase/details/${codebaseId}`);
}

export async function deleteCodebase(codebaseId) {
  return apiFetch(`/codebase/delete/${codebaseId}`, { method: "DELETE" });
}

export async function getFiles(codebaseId) {
  return apiFetch(`/codebase/files?codebase_id=${encodeURIComponent(codebaseId)}`);
}

export async function getFileContent(codebaseId, filePath) {
  return apiFetch(
    `/codebase/file?codebase_id=${encodeURIComponent(codebaseId)}&file_path=${encodeURIComponent(filePath)}`
  );
}

export async function getSummary(codebaseId) {
  return apiFetch(`/codebase/summary?codebase_id=${encodeURIComponent(codebaseId)}`);
}

export async function getTechnologies(codebaseId) {
  return apiFetch(`/codebase/technologies?codebase_id=${encodeURIComponent(codebaseId)}`);
}

export async function uploadZip(file, onProgress) {
  const token = getToken();
  const formData = new FormData();
  formData.append("file", file);

  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();

    xhr.upload.addEventListener("progress", (e) => {
      if (e.lengthComputable && onProgress) {
        onProgress(Math.round((e.loaded / e.total) * 100));
      }
    });

    xhr.addEventListener("load", () => {
      if (xhr.status === 401) {
        localStorage.removeItem("access_token");
        localStorage.removeItem("user");
        window.location.href = "/login";
        reject(new Error("Session expired"));
        return;
      }
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          resolve(JSON.parse(xhr.responseText));
        } catch {
          resolve(xhr.responseText);
        }
      } else {
        let detail = `Upload failed (${xhr.status})`;
        try {
          const json = JSON.parse(xhr.responseText);
          detail = json.detail || detail;
        } catch (_) {}
        reject(new Error(detail));
      }
    });

    xhr.addEventListener("error", () => reject(new Error("Network error during upload")));
    xhr.addEventListener("abort", () => reject(new Error("Upload aborted")));

    xhr.open("POST", `${API_BASE}/codebase/upload`);
    if (token) xhr.setRequestHeader("Authorization", `Bearer ${token}`);
    xhr.send(formData);
  });
}

export async function uploadFiles(fileList, codebaseName, onProgress) {
  const token = getToken();
  const formData = new FormData();
  if (codebaseName) {
    formData.append("codebase_name", codebaseName);
  }
  for (let i = 0; i < fileList.length; i++) {
    // Preserve webkitRelativePath when present
    const f = fileList[i];
    const path = f.webkitRelativePath || f.name;
    formData.append("files", f, path);
  }

  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();

    xhr.upload.addEventListener("progress", (e) => {
      if (e.lengthComputable && onProgress) {
        onProgress(Math.round((e.loaded / e.total) * 100));
      }
    });

    xhr.addEventListener("load", () => {
      if (xhr.status === 401) {
        localStorage.removeItem("access_token");
        localStorage.removeItem("user");
        window.location.href = "/login";
        reject(new Error("Session expired"));
        return;
      }
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          resolve(JSON.parse(xhr.responseText));
        } catch {
          resolve(xhr.responseText);
        }
      } else {
        let detail = `Upload failed (${xhr.status})`;
        try {
          const json = JSON.parse(xhr.responseText);
          detail = json.detail || detail;
        } catch (_) {}
        reject(new Error(detail));
      }
    });

    xhr.addEventListener("error", () => reject(new Error("Network error during upload")));
    xhr.addEventListener("abort", () => reject(new Error("Upload aborted")));

    xhr.open("POST", `${API_BASE}/codebase/upload-files`);
    if (token) xhr.setRequestHeader("Authorization", `Bearer ${token}`);
    xhr.send(formData);
  });
}

export async function analyzeSingleFile(file) {
  const formData = new FormData();
  formData.append("file", file);

  return apiFetch("/codebase/analyze-single-file", {
    method: "POST",
    body: formData,
  });
}

// ---- Analysis ------------------------------------------------------------

export async function explainFile(codebaseId, filePath) {
  return apiFetch(
    `/codebase/explain-file?codebase_id=${encodeURIComponent(codebaseId)}&file_path=${encodeURIComponent(filePath)}`
  );
}

export async function getArchitecture(codebaseId) {
  return apiFetch(`/codebase/architecture?codebase_id=${encodeURIComponent(codebaseId)}`);
}

export async function getIssues(codebaseId) {
  return apiFetch(`/codebase/issues?codebase_id=${encodeURIComponent(codebaseId)}`);
}

export async function getImprovements(codebaseId) {
  return apiFetch(`/codebase/improvements?codebase_id=${encodeURIComponent(codebaseId)}`);
}

export async function getFix(codebaseId, filePath, lineNumber) {
  return apiFetch(
    `/codebase/fix?codebase_id=${encodeURIComponent(codebaseId)}&file_path=${encodeURIComponent(filePath)}&line_number=${lineNumber}`
  );
}

export async function searchCodebase(codebaseId, query, chatHistory = [], limit = 5) {
  return apiFetch("/codebase/search", {
    method: "POST",
    body: JSON.stringify({
      query,
      codebase_id: codebaseId,
      limit,
      chat_history: chatHistory,
    }),
  });
}

// ---- AI Codebase Chat ----------------------------------------------------

export async function chatCodebase(codebaseId, message, chatHistory = [], fileFocus = null, limit = 6) {
  return apiFetch(`/codebase/${encodeURIComponent(codebaseId)}/chat`, {
    method: "POST",
    body: JSON.stringify({
      message,
      chat_history: chatHistory,
      file_focus: fileFocus,
      limit,
    }),
  });
}

// ---- Admin ---------------------------------------------------------------

export async function getAdminStats() {
  return apiFetch("/admin/stats");
}

export async function getAdminUsers() {
  return apiFetch("/admin/users");
}

export async function updateUserStatus(userId, isActive) {
  return apiFetch(`/admin/users/${userId}/status`, {
    method: "PUT",
    body: JSON.stringify({ is_active: isActive }),
  });
}

export async function updateUserRole(userId, role) {
  return apiFetch(`/admin/users/${userId}/role`, {
    method: "PUT",
    body: JSON.stringify({ role }),
  });
}

export async function getAdminAuditLogs() {
  return apiFetch("/admin/audit-logs");
}

export async function getAdminCodebases() {
  return apiFetch("/admin/codebases");
}

export async function adminDeleteCodebase(codebaseId) {
  return apiFetch(`/admin/codebases/${codebaseId}`, {
    method: "DELETE",
  });
}
