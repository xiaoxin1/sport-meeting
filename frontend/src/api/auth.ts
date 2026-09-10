import client from "./client";

export interface LoginPayload {
  username: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  username: string;
}

export async function login(payload: LoginPayload): Promise<TokenResponse> {
  const { data } = await client.post<TokenResponse>("/auth/login", payload);
  return data;
}
