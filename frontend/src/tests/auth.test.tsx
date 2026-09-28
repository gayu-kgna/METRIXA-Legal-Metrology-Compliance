import { describe, it, expect, vi, beforeEach } from 'vitest';
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { LoginPage } from '../pages/LoginPage';
import { AuthProvider } from '../context/AuthContext';
import { ProtectedRoute } from '../components/common/ProtectedRoute';
import * as authApi from '../api/auth';

vi.mock('../api/auth');

describe('Authentication & Protected Route Suite', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  it('renders login page with Metrixa branding and credentials form', () => {
    render(
      <AuthProvider>
        <MemoryRouter initialEntries={['/login']}>
          <LoginPage />
        </MemoryRouter>
      </AuthProvider>
    );

    expect(screen.getByText('METRIXA')).toBeInTheDocument();
    expect(screen.getByLabelText(/Officer Username/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Security Password/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Access Inspection Console/i })).toBeInTheDocument();
  });

  it('handles successful officer login and stores token', async () => {
    vi.mocked(authApi.login).mockResolvedValue({
      access_token: 'test_token_123',
      token_type: 'bearer',
    });

    vi.mocked(authApi.getMe).mockResolvedValue({
      id: 'officer-1',
      username: 'inspector',
      email: 'inspector@gov.in',
      role: 'FIELD_OFFICER',
      is_active: true,
    });

    render(
      <AuthProvider>
        <MemoryRouter initialEntries={['/login']}>
          <LoginPage />
        </MemoryRouter>
      </AuthProvider>
    );

    fireEvent.change(screen.getByLabelText(/Officer Username/i), { target: { value: 'inspector' } });
    fireEvent.change(screen.getByLabelText(/Security Password/i), { target: { value: 'Secret@123' } });
    fireEvent.click(screen.getByRole('button', { name: /Access Inspection Console/i }));

    await waitFor(() => {
      expect(localStorage.getItem('metrixa_token')).toBe('test_token_123');
    });
  });

  it('redirects unauthenticated users away from protected route to /login', async () => {
    vi.mocked(authApi.getMe).mockRejectedValue(new Error('Unauthorized'));

    render(
      <AuthProvider>
        <MemoryRouter initialEntries={['/dashboard']}>
          <Routes>
            <Route path="/login" element={<div>LOGIN_PAGE_RENDERED</div>} />
            <Route
              path="/dashboard"
              element={
                <ProtectedRoute>
                  <div>PROTECTED_DASHBOARD_CONTENT</div>
                </ProtectedRoute>
              }
            />
          </Routes>
        </MemoryRouter>
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByText('LOGIN_PAGE_RENDERED')).toBeInTheDocument();
    });
  });
});
