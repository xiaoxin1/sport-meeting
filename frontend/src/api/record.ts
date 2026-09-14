import client from "./client";

export interface Record {
  id: number;
  academic_year_id: number;
  event_name: string;
  group_name: string;
  gender: string;
  sort_order: number;
  holder_name: string;
  result: string;
  current_holder_name: string;
  historical_result: string;
  created_at: string;
}

export interface RecordCreate {
  event_name: string;
  group_name: string;
  gender: string;
}

export interface RecordUpdate {
  holder_name: string;
  result: string;
  current_holder_name: string;
  historical_result: string;
}

export interface RecordSortUpdate {
  updates: Array<{ id: number; sort_order: number }>;
}

export async function getRecords(): Promise<Record[]> {
  const { data } = await client.get<Record[]>("/records");
  return data;
}

export async function createRecord(payload: RecordCreate): Promise<Record> {
  const { data } = await client.post<Record>("/records", payload);
  return data;
}

export async function updateRecord(id: number, payload: RecordUpdate): Promise<Record> {
  const { data } = await client.put<Record>(`/records/${id}`, payload);
  return data;
}

export async function updateRecordSort(payload: RecordSortUpdate): Promise<void> {
  await client.put("/records/sort", payload);
}

export async function deleteRecord(id: number): Promise<void> {
  await client.delete(`/records/${id}`);
}
