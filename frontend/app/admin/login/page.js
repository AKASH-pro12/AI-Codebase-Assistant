"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { adminLogin, getMe } from "../../lib/api";
import { useAuth } from "../../context/AuthContext";
import { useToast } from "../../context/ToastContext";
import PasswordInput from "../../components/PasswordInput";

export default function AdminLoginPage() {
  const router = useRouter();
  const { setAuth } = useAuth();
  const { showToast } = useToast();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      // Calls dedicated backend endpoint POST /auth/admin-login
      const tokenData = await adminLogin(email.trim().toLowerCase(), password);
      const token = tokenData.access_token;

      localStorage.setItem("access_token", token);
      const profile = await getMe();

      // Double verify role from trusted database
      if (profile.role !== "admin") {
        localStorage.removeItem("access_token");
        throw new Error("Access denied: Administrator privileges required.");
      }

      setAuth(token, profile);
      showToast(`Welcome to the Admin Center, ${profile.name}!`, "success");
      router.push("/admin");
    } catch (err) {
      setError(err.message || "Admin authentication failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-slate-900 flex items-center justify-center px-4 py-12 transition-colors">
      <div className="w-full max-w-md">
        {/* Shield / Admin Brand Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-amber-500/10 border border-amber-500/30 mb-4 shadow-xl shadow-amber-500/10">
            <svg className="w-8 h-8 text-amber-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"
              />
            </svg>
          </div>
          <div className="inline-block px-3 py-1 rounded-full bg-amber-500/10 border border-amber-500/20 text-amber-400 text-xs font-semibold tracking-wider uppercase mb-2">
            Restricted Portal
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Admin Sign In</h1>
          <p className="text-slate-400 mt-1 text-sm">
            Sign in with administrative credentials to access the Admin Center
          </p>
        </div>

        {/* Card */}
        <div className="bg-slate-800/90 border border-slate-700/80 rounded-3xl p-8 shadow-2xl backdrop-blur-sm">
          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1.5">
                Admin Email Address
              </label>
              <input
                id="admin-email"
                type="email"
                required
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-4 py-2.5 bg-slate-900 border border-slate-700 rounded-xl text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-amber-500 focus:border-transparent transition text-sm"
                placeholder="admin@gmail.com"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1.5">
                Administrator Password
              </label>
              <PasswordInput
                id="admin-password"
                required
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="bg-slate-900 border-slate-700 text-white placeholder-slate-500 focus:ring-amber-500"
              />
            </div>

            {error && (
              <div className="bg-rose-950/50 border border-rose-800/80 rounded-xl px-4 py-3 text-sm text-rose-300 flex items-start gap-2.5">
                <svg className="w-5 h-5 shrink-0 mt-0.5 text-rose-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <div className="leading-relaxed">{error}</div>
              </div>
            )}

            <button
              id="admin-login-submit"
              type="submit"
              disabled={loading}
              className="w-full py-3 rounded-xl bg-amber-600 hover:bg-amber-500 text-slate-950 font-bold transition disabled:opacity-60 disabled:cursor-not-allowed shadow-lg shadow-amber-600/20 text-sm flex items-center justify-center gap-2"
            >
              {loading && (
                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                </svg>
              )}
              {loading ? "Authenticating Admin..." : "Sign in to Admin Center"}
            </button>
          </form>

          {/* Navigation Links */}
          <div className="mt-6 pt-5 border-t border-slate-700/60 flex flex-col items-center gap-3 text-sm">
            <Link
              href="/login"
              className="text-slate-400 hover:text-white transition flex items-center gap-1.5 font-medium"
            >
              <span>← Back to User Login</span>
            </Link>
            <Link href="/" className="text-xs text-slate-500 hover:text-slate-400 transition">
              Return to Homepage
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
