import client from "./client";

export interface LoginPayload {
  username: string;
  password: string;
  grade?: string;
  class_name?: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  username: string;
  role: string; // "admin" | "leader"
  class_team_id: number | null;
  grade: string | null;
  class_name: string | null;
}

export async function login(payload: LoginPayload): Promise<TokenResponse> {
  const { data } = await client.post<TokenResponse>("/auth/login", payload);
  return data;
}
