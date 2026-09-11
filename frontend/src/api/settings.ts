import client from "./client";

export interface Setting {
  id: number;
  key: string;
  value: string;
  description: string;
}

export async function getSettings(): Promise<Setting[]> {
  const { data } = await client.get<Setting[]>("/settings");
  return data;
}

export async function updateSetting(key: string, value: string): Promise<Setting> {
  const { data } = await client.put<Setting>(`/settings/${key}`, { value });
  return data;
}
