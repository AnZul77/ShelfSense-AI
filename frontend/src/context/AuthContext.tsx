"use client";

import React, { createContext, useContext, useState, useEffect } from "react";
import { UserProfile, apiFetch } from "@/lib/api";

interface User {
  id: number;
  name: string;
  email: string;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  profile: UserProfile | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (name: string, email: string, password: string) => Promise<void>;
  logout: () => void;
  refreshProfile: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    try {
      const savedToken = localStorage.getItem("shelf_token");
      const savedUser = localStorage.getItem("shelf_user");
      if (savedToken && savedUser) {
        setToken(savedToken);
        setUser(JSON.parse(savedUser));
      }
    } catch (e) {
      console.error("Failed to read auth state from storage:", e);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (token) {
      refreshProfile();
    } else {
      setProfile(null);
    }
  }, [token]);

  const refreshProfile = async () => {
    if (!token) return;
    try {
      const data = await apiFetch<UserProfile>("/profile", {}, token);
      setProfile(data);
    } catch (err) {
      console.error("Failed to fetch user profile:", err);
    }
  };

  const login = async (email: string, password: string) => {
    const data = await apiFetch<{ token: string; user_id: number; name: string }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });

    const userObj = { id: data.user_id, name: data.name, email };
    localStorage.setItem("shelf_token", data.token);
    localStorage.setItem("shelf_user", JSON.stringify(userObj));
    setToken(data.token);
    setUser(userObj);
  };

  const register = async (name: string, email: string, password: string) => {
    const data = await apiFetch<{ token: string; user_id: number; name: string }>("/auth/register", {
      method: "POST",
      body: JSON.stringify({ name, email, password }),
    });

    const userObj = { id: data.user_id, name: data.name, email };
    localStorage.setItem("shelf_token", data.token);
    localStorage.setItem("shelf_user", JSON.stringify(userObj));
    setToken(data.token);
    setUser(userObj);
  };

  const logout = () => {
    localStorage.removeItem("shelf_token");
    localStorage.removeItem("shelf_user");
    setToken(null);
    setUser(null);
    setProfile(null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        profile,
        isLoading,
        login,
        register,
        logout,
        refreshProfile,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
