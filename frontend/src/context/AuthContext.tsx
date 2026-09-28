import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { User } from '../types/api';
import { login as apiLogin, getMe } from '../api/auth';

interface AuthContextType {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(() => {
    const saved = localStorage.getItem('metrixa_user');
    if (saved) {
      try {
        return JSON.parse(saved);
      } catch {
        return null;
      }
    }
    return null;
  });
  const [token, setToken] = useState<string | null>(() => localStorage.getItem('metrixa_token'));
  const [isLoading, setIsLoading] = useState<boolean>(true);

  useEffect(() => {
    async function verifyAuth() {
      const storedToken = localStorage.getItem('metrixa_token');
      if (storedToken) {
        try {
          const profile = await getMe();
          setUser(profile);
          localStorage.setItem('metrixa_user', JSON.stringify(profile));
        } catch {
          localStorage.removeItem('metrixa_token');
          localStorage.removeItem('metrixa_user');
          setToken(null);
          setUser(null);
        }
      }
      setIsLoading(false);
    }

    verifyAuth();

    const handleExpired = () => {
      setUser(null);
      setToken(null);
    };

    window.addEventListener('auth:expired', handleExpired);
    return () => window.removeEventListener('auth:expired', handleExpired);
  }, []);

  const login = async (identifier: string, password: string) => {
    const email = identifier.includes('@') ? identifier : `${identifier}@metrixa.gov.in`;
    const tokens = await apiLogin({ email, password });
    localStorage.setItem('metrixa_token', tokens.access_token);
    setToken(tokens.access_token);

    // Fetch user profile
    const profile = await getMe();
    setUser(profile);
    localStorage.setItem('metrixa_user', JSON.stringify(profile));
  };

  const logout = () => {
    localStorage.removeItem('metrixa_token');
    localStorage.removeItem('metrixa_user');
    setToken(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isAuthenticated: !!user && !!token,
        isLoading,
        login,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
