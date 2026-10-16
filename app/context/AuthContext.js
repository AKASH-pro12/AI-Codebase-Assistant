"use client";

import { createContext, useContext, useEffect, useState } from "react";
import { getMe } from "../lib/api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const storedUser = localStorage.getItem("user");
    const token = localStorage.getItem("access_token");

    if (token && storedUser) {
      try {
        setUser(JSON.parse(storedUser));
      } catch (_) {}
    }

    // Verify the stored token is still valid
    if (token) {
      getMe()
        .then((profile) => {
          setUser(profile);
          localStorage.setItem("user", JSON.stringify(profile));
        })
        .catch(() => {
          localStorage.removeItem("access_token");
          localStorage.removeItem("user");
          setUser(null);
        })
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, []);

  function setAuth(token, profile) {
    localStorage.setItem("access_token", token);
    localStorage.setItem("user", JSON.stringify(profile));
    setUser(profile);
  }

  function clearAuth() {
    localStorage.removeItem("access_token");
    localStorage.removeItem("user");
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ user, loading, setAuth, clearAuth }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
