"use client";

import { useState, useEffect, useRef } from "react";
import AppShell from "../components/AppShell";
import { useAuth } from "../context/AuthContext";
import { useTheme } from "../context/ThemeContext";
import { useToast } from "../context/ToastContext";
import {
  updateProfile,
  changePassword,
  sendVerification,
  verifyEmail,
  getMe,
} from "../lib/api";
import PasswordInput from "../components/PasswordInput";

export default function SettingsPage() {
  const { user, setAuth } = useAuth();
  const { theme, setTheme } = useTheme();
  const { showToast } = useToast();

  const [activeTab, setActiveTab] = useState("profile"); // "profile" | "security" | "verification" | "appearance"

  // Profile form
  const [name, setName] = useState("");
  const [savingProfile, setSavingProfile] = useState(false);

  // Password form
  const [oldPassword, setOldPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [savingPassword, setSavingPassword] = useState(false);

  // Email verification state
  const [otp, setOtp] = useState("");
  const [verifyState, setVerifyState] = useState("idle"); // "idle" | "sending" | "sent" | "verifying" | "verified" | "error"
  const [verifyError, setVerifyError] = useState("");
  const [cooldown, setCooldown] = useState(0);
  const timerRef = useRef(null);

  useEffect(() => {
    if (user?.name) {
      setName(user.name);
    }
    if (user?.is_verified) {
      setVerifyState("verified");
    }
  }, [user]);

  useEffect(() => {
    if (cooldown > 0) {
      timerRef.current = setInterval(() => {
        setCooldown((prev) => {
          if (prev <= 1) {
            clearInterval(timerRef.current);
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
    }
    return () => clearInterval(timerRef.current);
  }, [cooldown]);

  async function handleProfileSave(e) {
    e.preventDefault();
    if (!name.trim()) return;
    setSavingProfile(true);
    try {
      await updateProfile(name.trim());
      const updatedProfile = await getMe();
      const token = localStorage.getItem("access_token");
      setAuth(token, updatedProfile);
      showToast("Profile name updated successfully", "success");
    } catch (err) {
      showToast(err.message || "Failed to update profile", "error");
    } finally {
      setSavingProfile(false);
    }
  }

  async function handlePasswordSave(e) {
    e.preventDefault();
    if (newPassword.length < 8) {
      showToast("New password must be at least 8 characters", "warning");
      return;
    }
    if (newPassword !== confirmPassword) {
      showToast("New passwords do not match", "warning");
      return;
    }

    setSavingPassword(true);
    try {
      await changePassword(oldPassword, newPassword);
      showToast("Password changed successfully", "success");
      setOldPassword("");
      setNewPassword("");
      setConfirmPassword("");
    } catch (err) {
      showToast(err.message || "Failed to change password", "error");
    } finally {
      setSavingPassword(false);
    }
  }

  async function handleSendOtp() {
    if (cooldown > 0) return;
    setVerifyState("sending");
    setVerifyError("");
    try {
      const res = await sendVerification();
      setVerifyState("sent");
      setCooldown(res.cooldown_seconds || 60);
      showToast(res.message || "Verification code sent to your registered email.", "success");
    } catch (err) {
      setVerifyState("error");
      setVerifyError(err.message || "Failed to send verification code. Please check email service configuration.");
      showToast(err.message || "Delivery failed", "error");
    }
  }

  async function handleVerifyOtp(e) {
    e.preventDefault();
    if (otp.trim().length !== 6) {
      showToast("Please enter a valid 6-digit code", "warning");
      return;
    }

    setVerifyState("verifying");
    setVerifyError("");
    try {
      await verifyEmail(otp.trim());
      const updatedProfile = await getMe();
      const token = localStorage.getItem("access_token");
      setAuth(token, updatedProfile);
      setVerifyState("verified");
      setOtp("");
      showToast("Email address successfully verified!", "success");
    } catch (err) {
      setVerifyState("sent");
      setVerifyError(err.message || "Invalid or expired verification code.");
      showToast(err.message || "Verification failed", "error");
    }
  }

  return (
    <AppShell title="Settings">
      <div className="max-w-4xl mx-auto space-y-8">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white">
            Account & Preferences
          </h2>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
            Manage your personal profile, credentials, verification, and workspace appearance.
          </p>
        </div>

        {/* Tab Navigation */}
        <div className="flex border-b border-slate-200 dark:border-slate-800 gap-6">
          <button
            onClick={() => setActiveTab("profile")}
            className={`pb-3 text-sm font-semibold transition border-b-2 ${
              activeTab === "profile"
                ? "border-indigo-600 text-indigo-600 dark:text-indigo-400"
                : "border-transparent text-slate-500 hover:text-slate-900 dark:hover:text-white"
            }`}
          >
            Profile
          </button>
          <button
            onClick={() => setActiveTab("security")}
            className={`pb-3 text-sm font-semibold transition border-b-2 ${
              activeTab === "security"
                ? "border-indigo-600 text-indigo-600 dark:text-indigo-400"
                : "border-transparent text-slate-500 hover:text-slate-900 dark:hover:text-white"
            }`}
          >
            Security & Password
          </button>
          <button
            onClick={() => setActiveTab("verification")}
            className={`pb-3 text-sm font-semibold transition border-b-2 ${
              activeTab === "verification"
                ? "border-indigo-600 text-indigo-600 dark:text-indigo-400"
                : "border-transparent text-slate-500 hover:text-slate-900 dark:hover:text-white"
            }`}
          >
            Email Verification
          </button>
          <button
            onClick={() => setActiveTab("appearance")}
            className={`pb-3 text-sm font-semibold transition border-b-2 ${
              activeTab === "appearance"
                ? "border-indigo-600 text-indigo-600 dark:text-indigo-400"
                : "border-transparent text-slate-500 hover:text-slate-900 dark:hover:text-white"
            }`}
          >
            Appearance
          </button>
        </div>

        {/* Tab 1: Profile */}
        {activeTab === "profile" && (
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl p-8 shadow-sm space-y-6">
            <h3 className="text-base font-bold text-slate-900 dark:text-white">
              Profile Information
            </h3>
            <form onSubmit={handleProfileSave} className="space-y-4 max-w-lg">
              <div>
                <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                  Full Name
                </label>
                <input
                  type="text"
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full px-3.5 py-2.5 bg-slate-50 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-xl text-slate-900 dark:text-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                  Email Address
                </label>
                <input
                  type="email"
                  disabled
                  value={user?.email || ""}
                  className="w-full px-3.5 py-2.5 bg-slate-100 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-800 rounded-xl text-slate-500 text-sm cursor-not-allowed"
                />
                <p className="text-[11px] text-slate-400 mt-1">
                  Email address cannot be changed as it identifies your repositories.
                </p>
              </div>

              <div className="pt-2">
                <button
                  type="submit"
                  disabled={savingProfile}
                  className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-semibold transition disabled:opacity-50 flex items-center gap-2"
                >
                  {savingProfile && (
                    <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                    </svg>
                  )}
                  {savingProfile ? "Saving..." : "Save Changes"}
                </button>
              </div>
            </form>
          </div>
        )}

        {/* Tab 2: Security & Password */}
        {activeTab === "security" && (
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl p-8 shadow-sm space-y-6">
            <h3 className="text-base font-bold text-slate-900 dark:text-white">
              Change Account Password
            </h3>
            <form onSubmit={handlePasswordSave} className="space-y-4 max-w-lg">
              <div>
                <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                  Current Password
                </label>
                <PasswordInput
                  id="settings-old-password"
                  required
                  autoComplete="current-password"
                  value={oldPassword}
                  onChange={(e) => setOldPassword(e.target.value)}
                  placeholder="••••••••"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                  New Password (min 8 characters)
                </label>
                <PasswordInput
                  id="settings-new-password"
                  required
                  minLength={8}
                  autoComplete="new-password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  placeholder="••••••••"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                  Confirm New Password
                </label>
                <PasswordInput
                  id="settings-confirm-password"
                  required
                  minLength={8}
                  autoComplete="new-password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="••••••••"
                />
              </div>

              <div className="pt-2">
                <button
                  type="submit"
                  disabled={savingPassword}
                  className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-semibold transition disabled:opacity-50 flex items-center gap-2"
                >
                  {savingPassword && (
                    <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                    </svg>
                  )}
                  {savingPassword ? "Updating Password..." : "Update Password"}
                </button>
              </div>
            </form>
          </div>
        )}

        {/* Tab 3: Real Email Verification */}
        {activeTab === "verification" && (
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl p-8 shadow-sm space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-base font-bold text-slate-900 dark:text-white">
                  Email Verification Status
                </h3>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                  Verified accounts receive repository alerts and security recovery notices.
                </p>
              </div>
              <div>
                {user?.is_verified ? (
                  <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                    Verified Account
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20">
                    Pending Verification
                  </span>
                )}
              </div>
            </div>

            {user?.is_verified ? (
              <div className="p-4 rounded-2xl bg-emerald-50/50 dark:bg-emerald-950/20 border border-emerald-200 dark:border-emerald-800/40 text-xs text-emerald-700 dark:text-emerald-300 flex items-center gap-3">
                <svg className="w-5 h-5 shrink-0 text-emerald-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <span>
                  Your email address <strong>{user?.email}</strong> is verified. No further action is required.
                </span>
              </div>
            ) : (
              <div className="space-y-5 max-w-lg pt-2 border-t border-slate-200 dark:border-slate-800">
                <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
                  We will send a single-use 6-digit confirmation code directly to <strong>{user?.email}</strong> via our email delivery provider. The code expires in 10 minutes.
                </p>

                {/* Error Banner if provider is not configured or fails */}
                {verifyError && (
                  <div className="p-4 rounded-2xl bg-rose-50 dark:bg-rose-950/30 border border-rose-200 dark:border-rose-900/50 text-xs text-rose-700 dark:text-rose-300 space-y-1">
                    <div className="flex items-center gap-2 font-semibold">
                      <svg className="w-4 h-4 text-rose-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                      </svg>
                      <span>Delivery / Configuration Notice</span>
                    </div>
                    <p className="pl-6">{verifyError}</p>
                  </div>
                )}

                {/* Success Banner when code is sent */}
                {verifyState === "sent" && !verifyError && (
                  <div className="p-4 rounded-2xl bg-indigo-50 dark:bg-indigo-950/30 border border-indigo-200 dark:border-indigo-800 text-xs text-indigo-700 dark:text-indigo-300">
                    ✓ A 6-digit verification code has been dispatched to <strong>{user?.email}</strong>. Check your inbox (or spam folder).
                  </div>
                )}

                <div className="flex items-center gap-3">
                  <button
                    type="button"
                    onClick={handleSendOtp}
                    disabled={verifyState === "sending" || cooldown > 0}
                    className="px-4 py-2.5 rounded-xl border border-slate-300 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800 text-xs font-semibold text-slate-700 dark:text-slate-300 transition disabled:opacity-50 flex items-center gap-2"
                  >
                    {verifyState === "sending" ? (
                      <>
                        <svg className="animate-spin h-3.5 w-3.5" viewBox="0 0 24 24" fill="none">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                        </svg>
                        <span>Sending to email...</span>
                      </>
                    ) : cooldown > 0 ? (
                      <span>Resend code in {cooldown}s</span>
                    ) : verifyState === "sent" ? (
                      <span>Resend Verification Code</span>
                    ) : (
                      <span>Send Verification Code</span>
                    )}
                  </button>
                </div>

                {/* Code Submission Form */}
                <form onSubmit={handleVerifyOtp} className="space-y-3 pt-3">
                  <div>
                    <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1.5">
                      Enter 6-Digit Code
                    </label>
                    <input
                      type="text"
                      maxLength={6}
                      required
                      value={otp}
                      onChange={(e) => setOtp(e.target.value.replace(/\D/g, ""))}
                      className="w-48 px-4 py-2.5 bg-slate-50 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-xl text-slate-900 dark:text-white text-lg tracking-[0.4em] font-mono text-center focus:outline-none focus:ring-2 focus:ring-indigo-500 shadow-sm"
                      placeholder="••••••"
                    />
                  </div>
                  <button
                    type="submit"
                    disabled={verifyState === "verifying" || otp.length !== 6}
                    className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-semibold transition disabled:opacity-50 shadow-sm flex items-center gap-2"
                  >
                    {verifyState === "verifying" && (
                      <svg className="animate-spin h-3.5 w-3.5" viewBox="0 0 24 24" fill="none">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                      </svg>
                    )}
                    <span>{verifyState === "verifying" ? "Verifying..." : "Verify Code"}</span>
                  </button>
                </form>
              </div>
            )}
          </div>
        )}

        {/* Tab 4: Appearance */}
        {activeTab === "appearance" && (
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl p-8 shadow-sm space-y-6">
            <h3 className="text-base font-bold text-slate-900 dark:text-white">
              Workspace Theme
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Select your preferred appearance mode. Themes apply instantly across all pages and workspaces.
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 max-w-xl">
              {[
                {
                  id: "light",
                  title: "Light",
                  desc: "Clean crisp light surfaces",
                  icon: (
                    <svg className="w-5 h-5 text-amber-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
                    </svg>
                  ),
                },
                {
                  id: "dark",
                  title: "Dark",
                  desc: "High contrast dark mode",
                  icon: (
                    <svg className="w-5 h-5 text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
                    </svg>
                  ),
                },
                {
                  id: "system",
                  title: "System",
                  desc: "Sync with OS theme",
                  icon: (
                    <svg className="w-5 h-5 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                    </svg>
                  ),
                },
              ].map((opt) => (
                <button
                  key={opt.id}
                  onClick={() => setTheme(opt.id)}
                  className={`p-5 rounded-2xl border text-left transition flex flex-col justify-between ${
                    theme === opt.id
                      ? "border-indigo-600 bg-indigo-50/40 dark:bg-indigo-950/20 ring-2 ring-indigo-500/20"
                      : "border-slate-200 dark:border-slate-800 hover:border-slate-400"
                  }`}
                >
                  <div className="flex items-center justify-between mb-3">
                    {opt.icon}
                    {theme === opt.id && (
                      <span className="w-2 h-2 rounded-full bg-indigo-600" />
                    )}
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-slate-900 dark:text-white">
                      {opt.title}
                    </p>
                    <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5">
                      {opt.desc}
                    </p>
                  </div>
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
}
