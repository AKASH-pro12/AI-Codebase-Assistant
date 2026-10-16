"use client";

import Link from "next/link";
import { useAuth } from "./context/AuthContext";

const FEATURES = [
  {
    title: "Repository Analysis",
    description: "Understand file structure, dependencies, functions, classes and API routes powered by AI.",
    icon: (
      <svg className="w-6 h-6 text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
          d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
      </svg>
    ),
  },
  {
    title: "AI Code Search",
    description: "Ask questions in plain English and get contextual, source-backed answers from your codebase.",
    icon: (
      <svg className="w-6 h-6 text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
          d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
      </svg>
    ),
  },
  {
    title: "Issue Detection",
    description: "Automatically detect code quality issues, bugs and anti-patterns across your Python files.",
    icon: (
      <svg className="w-6 h-6 text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
          d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
      </svg>
    ),
  },
  {
    title: "AI Code Fixes",
    description: "Get AI-generated fix suggestions for every detected issue, with precise line-level context.",
    icon: (
      <svg className="w-6 h-6 text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
          d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
      </svg>
    ),
  },
  {
    title: "Architecture Overview",
    description: "Visualize how your files relate to each other, which routes exist and how the app is structured.",
    icon: (
      <svg className="w-6 h-6 text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
          d="M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM4 13a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zM16 13a1 1 0 011-1h2a1 1 0 011 1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-6z" />
      </svg>
    ),
  },
  {
    title: "Improvement Suggestions",
    description: "Receive AI-powered improvement recommendations tailored to your project's detected issues.",
    icon: (
      <svg className="w-6 h-6 text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
      </svg>
    ),
  },
];

export default function Home() {
  const { user, loading } = useAuth();

  return (
    <main className="min-h-screen bg-slate-950 text-white">

      {/* Navbar */}
      <nav className="flex items-center justify-between px-8 py-5 border-b border-slate-800/60">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center">
            <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
            </svg>
          </div>
          <span className="font-semibold text-sm text-white">AI Codebase Assistant</span>
        </div>

        <div className="flex items-center gap-3">
          {!loading && (
            user ? (
              <div className="flex items-center gap-2">
                {user.role === "admin" && (
                  <Link
                    href="/admin"
                    className="px-4 py-2 rounded-xl bg-amber-500/10 border border-amber-500/30 hover:bg-amber-500/20 text-amber-400 font-semibold text-xs transition flex items-center gap-1.5"
                  >
                    <span>🛡️</span>
                    <span>Admin Center</span>
                  </Link>
                )}
                <Link
                  href="/dashboard"
                  className="px-5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-sm transition"
                >
                  Dashboard
                </Link>
              </div>
            ) : (
              <>
                <Link
                  href="/login"
                  className="px-4 py-2 rounded-xl border border-slate-700 hover:bg-slate-800 text-slate-200 text-xs sm:text-sm transition font-medium"
                >
                  User Sign In
                </Link>
                <Link
                  href="/admin/login"
                  className="px-3.5 py-2 rounded-xl border border-amber-500/30 bg-amber-500/10 hover:bg-amber-500/20 text-amber-400 text-xs sm:text-sm transition font-medium flex items-center gap-1.5"
                >
                  <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
                  Admin Sign In
                </Link>
                <Link
                  href="/signup"
                  className="px-5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs sm:text-sm transition shadow-md shadow-indigo-600/20"
                >
                  Get started
                </Link>
              </>
            )
          )}
        </div>
      </nav>

      {/* Hero */}
      <section className="flex flex-col items-center text-center px-6 py-28">
        <div className="inline-flex items-center gap-2 bg-indigo-600/10 border border-indigo-500/20 rounded-full px-4 py-1.5 text-xs text-indigo-400 font-medium mb-6">
          <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-pulse" />
          AI-Powered Developer Assistant
        </div>

        <h2 className="text-5xl md:text-6xl font-bold max-w-4xl leading-tight">
          Understand Your
          <span className="block bg-gradient-to-r from-indigo-400 to-purple-400 bg-clip-text text-transparent">
            Codebase with AI
          </span>
        </h2>

        <p className="mt-6 max-w-2xl text-lg text-slate-400 leading-relaxed">
          Upload any repository ZIP. Get AI-powered analysis, semantic search, architecture maps,
          issue detection and code fixes — instantly.
        </p>

        <div className="flex flex-wrap items-center justify-center gap-4 mt-10">
          <Link
            href="/signup"
            id="hero-get-started"
            className="px-7 py-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold transition text-sm shadow-lg shadow-indigo-600/25"
          >
            Get started free
          </Link>
          <Link
            href="/login"
            className="px-7 py-3 rounded-xl border border-slate-700 hover:bg-slate-800 text-white transition text-sm font-medium"
          >
            User Sign In
          </Link>
          <Link
            href="/admin/login"
            className="px-5 py-3 rounded-xl border border-amber-500/20 bg-amber-500/5 hover:bg-amber-500/10 text-amber-400 transition text-sm font-medium flex items-center gap-1.5"
          >
            <span>🛡️</span>
            <span>Admin Portal</span>
          </Link>
        </div>
      </section>

      {/* Features */}
      <section className="px-8 py-16 border-t border-slate-800/60">
        <h2 className="text-3xl font-bold text-center mb-3">Everything you need</h2>
        <p className="text-slate-400 text-center mb-12 text-sm max-w-lg mx-auto">
          A complete AI toolkit for understanding, searching and improving any codebase.
        </p>

        <div className="grid md:grid-cols-3 gap-5 max-w-5xl mx-auto">
          {FEATURES.map((feature) => (
            <div
              key={feature.title}
              className="p-6 rounded-2xl bg-slate-900 border border-slate-800 hover:border-indigo-500/40 hover:bg-slate-800/60 transition-all duration-200 group"
            >
              <div className="w-10 h-10 rounded-xl bg-indigo-600/10 flex items-center justify-center mb-4 group-hover:bg-indigo-600/20 transition">
                {feature.icon}
              </div>
              <h3 className="text-base font-semibold mb-2">{feature.title}</h3>
              <p className="text-slate-400 text-sm leading-relaxed">{feature.description}</p>
            </div>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section className="px-8 py-20 text-center">
        <h2 className="text-3xl font-bold mb-4">Ready to explore your code?</h2>
        <p className="text-slate-400 mb-8 text-sm">Upload a ZIP and start analysing in under a minute.</p>
        <Link
          href="/signup"
          className="inline-block px-8 py-3.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-sm transition"
        >
          Create your free account
        </Link>
      </section>

      {/* Footer */}
      <footer className="border-t border-slate-800/80 py-8 px-8 text-slate-500 text-xs">
        <div className="max-w-5xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
          <div>© 2026 AI-Powered Codebase Assistant. All rights reserved.</div>
          <div className="flex items-center gap-6">
            <Link href="/login" className="hover:text-slate-300 transition">
              User Sign In
            </Link>
            <Link href="/signup" className="hover:text-slate-300 transition">
              Create Account
            </Link>
            <Link href="/admin/login" className="text-amber-500/80 hover:text-amber-400 transition font-medium flex items-center gap-1">
              <span>🛡️</span>
              <span>Admin Center</span>
            </Link>
          </div>
        </div>
      </footer>
    </main>
  );
}