import client from "./client";

export type Gender = "男" | "女" | "混合";

export interface Event {
  id: number;
  academic_year_id: number;
  name: string;
  group_name: string;
  gender: Gender;
  venue: string;
  final_teams: number;
  is_team: boolean;
  description: string;
  created_at: string;
}

export interface EventInput {
  name: string;
  group_name: string;
  gender: Gender;
  venue: string;
  final_teams: number;
  is_team: boolean;
  description: string;
}

export async function listEvents(): Promise<Event[]> {
  const { data } = await client.get<Event[]>("/events");
  return data;
}

export async function createEvent(payload: EventInput): Promise<Event> {
  const { data } = await client.post<Event>("/events", payload);
  return data;
}

export async function updateEvent(id: number, payload: EventInput): Promise<Event> {
  const { data } = await client.put<Event>(`/events/${id}`, payload);
  return data;
}

export async function deleteEvent(id: number): Promise<void> {
  await client.delete(`/events/${id}`);
}
