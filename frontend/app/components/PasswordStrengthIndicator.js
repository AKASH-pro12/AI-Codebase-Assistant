"use client";

import { useMemo } from "react";

const COMMON_WEAK_PASSWORDS = [
  "password",
  "password123",
  "12345678",
  "123456789",
  "qwerty123",
  "admin123",
  "letmein123",
  "welcome123",
  "test1234",
  "11111111",
  "changeme",
  "iloveyou123",
  "abcdefgh",
];

export function evaluatePassword(password) {
  if (!password) {
    return {
      score: 0,
      label: "None",
      color: "slate",
      isLengthValid: false,
      hasUpper: false,
      hasLower: false,
      hasNumber: false,
      hasSymbol: false,
      isPassphrase: false,
      isCommon: false,
      isValid: false,
      suggestions: ["Enter a password of at least 8 characters."],
    };
  }

  const length = password.length;
  const isLengthValid = length >= 8;
  const isPassphrase = length >= 14;
  const hasUpper = /[A-Z]/.test(password);
  const hasLower = /[a-z]/.test(password);
  const hasNumber = /[0-9]/.test(password);
  const hasSymbol = /[^A-Za-z0-9]/.test(password);

  const cleanLower = password.toLowerCase().trim();
  const isCommon =
    COMMON_WEAK_PASSWORDS.includes(cleanLower) ||
    new Set(cleanLower).size <= 2;

  const varietyCount = [hasUpper, hasLower, hasNumber, hasSymbol].filter(Boolean).length;

  let score = 0;
  const suggestions = [];

  if (!isLengthValid) {
    suggestions.push("Use at least 8 characters.");
  } else if (isCommon) {
    suggestions.push("Avoid common or easily guessed passwords.");
  }

  if (isLengthValid && !isCommon) {
    if (isPassphrase) {
      // Long passphrases are naturally strong
      score = varietyCount >= 2 ? 4 : 3;
    } else if (length >= 12) {
      if (varietyCount >= 3) score = 4;
      else if (varietyCount >= 2) score = 3;
      else score = 2;
    } else {
      // 8-11 characters
      if (varietyCount >= 4) score = 3;
      else if (varietyCount >= 2) score = 2;
      else score = 1;
    }
  }

  if (!hasUpper) suggestions.push("Add uppercase letters (A-Z).");
  if (!hasLower) suggestions.push("Add lowercase letters (a-z).");
  if (!hasNumber) suggestions.push("Add numbers (0-9).");
  if (!hasSymbol) suggestions.push("Add symbols or punctuation (!@#$).");

  if (length >= 8 && length < 14) {
    suggestions.push("Consider using a longer passphrase for maximum security.");
  }

  let label = "Weak";
  let color = "rose";

  if (score === 4) {
    label = "Strong";
    color = "emerald";
  } else if (score === 3) {
    label = "Good";
    color = "blue";
  } else if (score === 2) {
    label = "Fair";
    color = "amber";
  } else {
    label = "Weak";
    color = "rose";
  }

  // Minimum application requirement: at least 8 chars, not common, score >= 2
  const isValid = isLengthValid && !isCommon && (score >= 2 || isPassphrase);

  return {
    score,
    label,
    color,
    isLengthValid,
    hasUpper,
    hasLower,
    hasNumber,
    hasSymbol,
    isPassphrase,
    isCommon,
    isValid,
    suggestions,
  };
}

export default function PasswordStrengthIndicator({ password, confirmPassword }) {
  const result = useMemo(() => evaluatePassword(password), [password]);

  if (!password) {
    return (
      <div className="mt-2 text-[12px] text-slate-500 dark:text-slate-400">
        Password requirements: Minimum 8 characters. Mix letters, numbers, and symbols, or use a passphrase.
      </div>
    );
  }

  const colorStyles = {
    rose: {
      bar: "bg-rose-500",
      text: "text-rose-600 dark:text-rose-400",
      badge: "bg-rose-50 dark:bg-rose-950/40 text-rose-700 dark:text-rose-300 border-rose-200 dark:border-rose-800",
    },
    amber: {
      bar: "bg-amber-500",
      text: "text-amber-600 dark:text-amber-400",
      badge: "bg-amber-50 dark:bg-amber-950/40 text-amber-700 dark:text-amber-300 border-amber-200 dark:border-amber-800",
    },
    blue: {
      bar: "bg-blue-500",
      text: "text-blue-600 dark:text-blue-400",
      badge: "bg-blue-50 dark:bg-blue-950/40 text-blue-700 dark:text-blue-300 border-blue-200 dark:border-blue-800",
    },
    emerald: {
      bar: "bg-emerald-500",
      text: "text-emerald-600 dark:text-emerald-400",
      badge: "bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-300 border-emerald-200 dark:border-emerald-800",
    },
  }[result.color];

  const matchesConfirm = confirmPassword && confirmPassword.length > 0;
  const passwordsMatch = matchesConfirm && password === confirmPassword;

  return (
    <div className="mt-2.5 space-y-2.5">
      {/* Strength Bar & Text Label */}
      <div>
        <div className="flex items-center justify-between text-xs mb-1.5">
          <span className="text-slate-600 dark:text-slate-400 font-medium">
            Password Strength:
          </span>
          <span className={`font-semibold tracking-wide ${colorStyles.text}`}>
            {result.label}
          </span>
        </div>

        {/* 4-segment visual bar */}
        <div className="grid grid-cols-4 gap-1.5 h-1.5">
          {[1, 2, 3, 4].map((step) => {
            const isFilled = result.score >= step;
            return (
              <div
                key={step}
                className={`h-full rounded-full transition-all duration-300 ${
                  isFilled ? colorStyles.bar : "bg-slate-200 dark:bg-slate-700"
                }`}
              />
            );
          })}
        </div>
      </div>

      {/* Real-time Requirement Chips */}
      <div className="grid grid-cols-2 gap-1.5 text-[11px] text-slate-600 dark:text-slate-400 pt-1">
        <div className="flex items-center gap-1.5">
          <span className={result.isLengthValid ? "text-emerald-500 font-bold" : "text-slate-400"}>
            {result.isLengthValid ? "✓" : "○"}
          </span>
          <span>8+ characters</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className={result.hasUpper && result.hasLower ? "text-emerald-500 font-bold" : "text-slate-400"}>
            {result.hasUpper && result.hasLower ? "✓" : "○"}
          </span>
          <span>Upper & lowercase</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className={result.hasNumber ? "text-emerald-500 font-bold" : "text-slate-400"}>
            {result.hasNumber ? "✓" : "○"}
          </span>
          <span>At least one number</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className={result.hasSymbol || result.isPassphrase ? "text-emerald-500 font-bold" : "text-slate-400"}>
            {result.hasSymbol || result.isPassphrase ? "✓" : "○"}
          </span>
          <span>Symbol or 14+ passphrase</span>
        </div>
      </div>

      {/* Suggestions if weak or fair */}
      {result.suggestions.length > 0 && result.score <= 2 && (
        <div className={`p-2.5 rounded-xl border text-[11px] leading-relaxed ${colorStyles.badge}`}>
          <div className="font-semibold mb-0.5">Suggestions to strengthen your password:</div>
          <ul className="list-disc list-inside space-y-0.5">
            {result.suggestions.slice(0, 3).map((s, idx) => (
              <li key={idx}>{s}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Password Match Indicator */}
      {matchesConfirm && (
        <div
          className={`flex items-center gap-1.5 text-xs font-medium pt-1 ${
            passwordsMatch ? "text-emerald-600 dark:text-emerald-400" : "text-rose-600 dark:text-rose-400"
          }`}
        >
          <span>{passwordsMatch ? "✓" : "✕"}</span>
          <span>{passwordsMatch ? "Passwords match" : "Passwords do not match"}</span>
        </div>
      )}
    </div>
  );
}
