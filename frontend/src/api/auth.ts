import { request } from './client';
import { AuthTokens, User } from '../types/api';

export async function login(credentials: { email: string; password: string }): Promise<AuthTokens> {
  return request<AuthTokens>('/auth/login', {
    method: 'POST',
    body: JSON.stringify(credentials),
  });
}

export async function getMe(): Promise<User> {
  return request<User>('/auth/me');
}
