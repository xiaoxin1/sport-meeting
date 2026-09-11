import client from "./client";

export interface ScheduleConfig {
  id: number;
  academic_year_id: number;
  days: number;
  lanes: number;
  hard_rules: string;
  soft_rules: string;
  ai_history: string[];
  generated_at: string | null;
}

export interface ScheduleConfigInput {
  days: number;
  lanes: number;
  hard_rules: string;
  soft_rules: string;
}

export interface EntryUpdateInput {
  day_index: number;
  period: string;
  order_no: number;
  start_time: string;
  end_time: string;
  venue: string;
}

export interface ScheduleEntry {
  id: number;
  event_id: number;
  event_name: string;
  group_name: string;
  gender: string;
  is_team: boolean;
  day_index: number;
  period: string;
  round_type: string;
  order_no: number;
  group_count: number;
  advance_count: number;
  start_time: string;
  end_time: string;
  venue: string;
}

export interface ScheduleLane {
  id: number;
  lane_no: number;
  athlete_id: number | null;
  class_team_id: number | null;
  athlete_name: string | null;
  number: number | null;
  grade: string | null;
  class_name: string | null;
  result: string;
  rank: number | null;
}

export interface ScheduleGroup {
  id: number;
  group_no: number;
  lanes: ScheduleLane[];
}

export interface EntryDetail extends ScheduleEntry {
  groups: ScheduleGroup[];
}

export interface ScheduleData {
  config: ScheduleConfig | null;
  entries: ScheduleEntry[];
  day_dates: Record<string, string>;
}

export async function getConfig(): Promise<ScheduleConfig> {
  const { data } = await client.get<ScheduleConfig>("/schedule/config");
  return data;
}

export async function updateConfig(payload: ScheduleConfigInput): Promise<ScheduleConfig> {
  const { data } = await client.put<ScheduleConfig>("/schedule/config", payload);
  return data;
}

export async function regenerate(): Promise<ScheduleConfig> {
  const { data } = await client.post<ScheduleConfig>("/schedule/generate");
  return data;
}

export async function aiOptimize(message: string): Promise<ScheduleConfig> {
  const { data } = await client.post<ScheduleConfig>("/schedule/ai-optimize", { message }, {
    timeout: 300000, // AI优化需要5分钟超时时间
  });
  return data;
}

export async function getSchedule(): Promise<ScheduleData> {
  const { data } = await client.get<ScheduleData>("/schedule");
  return data;
}

export async function updateEntry(entryId: number, input: EntryUpdateInput): Promise<ScheduleEntry> {
  const { data } = await client.put<ScheduleEntry>(`/schedule/entries/${entryId}`, input);
  return data;
}

export async function getEntryDetail(entryId: number): Promise<EntryDetail> {
  const { data } = await client.get<EntryDetail>(`/schedule/entries/${entryId}`);
  return data;
}

export interface LaneResult {
  lane_id: number;
  result: string;
  rank: number | null;
}

export interface LaneUpdate {
  lane_id: number;
  athlete_id: number | null;
  class_team_id: number | null;
}

export async function updateLanes(entryId: number, lanes: LaneUpdate[]): Promise<EntryDetail> {
  const { data } = await client.put<EntryDetail>(`/schedule/entries/${entryId}/lanes`, lanes);
  return data;
}

export async function updateResults(entryId: number, results: LaneResult[]): Promise<EntryDetail> {
  const { data } = await client.put<EntryDetail>(`/schedule/entries/${entryId}/results`, {
    results,
  });
  return data;
}

export async function buildFinals(entryId: number): Promise<EntryDetail> {
  const { data } = await client.post<EntryDetail>(`/schedule/entries/${entryId}/build-finals`);
  return data;
}
