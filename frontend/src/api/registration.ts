import client from "./client";

export interface ClassTeam {
  id: number;
  academic_year_id: number;
  grade: string;
  class_name: string;
  leader_name: string;
  male_count: number;
  female_count: number;
  created_at: string;
  password: string; // 仅管理员返回明文，领队为空串
}

export interface ClassTeamInput {
  grade: string;
  class_name: string;
  leader_name: string;
  male_count: number;
  female_count: number;
  password?: string;
}

export interface Athlete {
  id: number;
  class_team_id: number;
  name: string;
  gender: "男" | "女";
  number: number | null;
  event_ids: number[];
  grade: string;
  class_name: string;
}

export interface AthleteInput {
  name: string;
  gender: "男" | "女";
  event_ids: number[];
}

export interface ClassTeamDetail extends ClassTeam {
  athletes: Athlete[];
  team_event_ids: number[];
}

export async function listClasses(): Promise<ClassTeam[]> {
  const { data } = await client.get<ClassTeam[]>("/registration/classes");
  return data;
}

export async function listAthletes(): Promise<Athlete[]> {
  const { data } = await client.get<Athlete[]>("/registration/athletes");
  return data;
}

export async function createClass(payload: ClassTeamInput): Promise<ClassTeam> {
  const { data } = await client.post<ClassTeam>("/registration/classes", payload);
  return data;
}

export async function updateClass(id: number, payload: ClassTeamInput): Promise<ClassTeam> {
  const { data } = await client.put<ClassTeam>(`/registration/classes/${id}`, payload);
  return data;
}

export async function deleteClass(id: number): Promise<void> {
  await client.delete(`/registration/classes/${id}`);
}

export async function getClassDetail(id: number): Promise<ClassTeamDetail> {
  const { data } = await client.get<ClassTeamDetail>(`/registration/classes/${id}`);
  return data;
}

export async function generateNumbers(): Promise<{ assigned: number }> {
  const { data } = await client.post<{ assigned: number }>("/registration/generate-numbers");
  return data;
}

export async function addAthlete(classId: number, payload: AthleteInput): Promise<Athlete> {
  const { data } = await client.post<Athlete>(
    `/registration/classes/${classId}/athletes`,
    payload,
  );
  return data;
}

export async function updateAthlete(athleteId: number, payload: AthleteInput): Promise<Athlete> {
  const { data } = await client.put<Athlete>(`/registration/athletes/${athleteId}`, payload);
  return data;
}

export async function deleteAthlete(athleteId: number): Promise<void> {
  await client.delete(`/registration/athletes/${athleteId}`);
}

export async function updateTeamEvents(
  classId: number,
  eventIds: number[],
): Promise<ClassTeamDetail> {
  const { data } = await client.put<ClassTeamDetail>(
    `/registration/classes/${classId}/team-events`,
    { event_ids: eventIds },
  );
  return data;
}

export interface EventRegistrationEntry {
  class_id: number;
  grade: string;
  class_name: string;
  athlete_name: string | null;
  number: number | null;
}

export interface EventRegistrationList {
  event_id: number;
  event_name: string;
  is_team: boolean;
  entries: EventRegistrationEntry[];
}

export async function getEventRegistrations(
  eventId: number,
): Promise<EventRegistrationList> {
  const { data } = await client.get<EventRegistrationList>(
    `/registration/events/${eventId}/registrations`,
  );
  return data;
}

// ---------- 报名规则配置 + 整体保存 ----------
export interface RegistrationConfig {
  hint: string;
  max_per_event: number;
  max_events_per_person: number;
}

export async function getRegistrationConfig(): Promise<RegistrationConfig> {
  const { data } = await client.get<RegistrationConfig>("/registration/config");
  return data;
}

export interface RegistrationAthleteInput {
  id: number | null;
  name: string;
  gender: "男" | "女";
  event_ids: number[];
}

export interface RegistrationSaveRequest {
  male_count: number;
  female_count: number;
  athletes: RegistrationAthleteInput[];
  team_event_ids: number[];
}

export async function saveRegistration(
  classId: number,
  payload: RegistrationSaveRequest,
): Promise<ClassTeamDetail> {
  const { data } = await client.put<ClassTeamDetail>(
    `/registration/classes/${classId}/registration`,
    payload,
  );
  return data;
}
