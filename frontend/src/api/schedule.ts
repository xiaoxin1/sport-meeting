import client from "./client";

export interface ScheduleConfig {
  id: number;
  academic_year_id: number;
  days: number;
  lanes: number;
  hard_rules: string;
  soft_rules: string;
  ai_history: string[];
  last_ai_request: string;
  last_ai_response: string;
  last_ai_report: string[];
  last_ai_mode: string;
  last_ai_time: string | null;
  generated_at: string | null;
}

export interface ScheduleConfigInput {
  lanes: number;
}

export interface EntryUpdateInput {
  start_time: string;
  end_time: string;
  venue: string;
}

export interface EntryCreateInput {
  event_id: number;
  day_index: number;
  period: string;
  round_type: string;
  start_time: string;
  end_time: string;
  venue: string;
}

export interface LaneCreateInput {
  group_id: number;
  athlete_id: number | null;
  class_team_id: number | null;
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

export async function generateSchedule(): Promise<ScheduleData> {
  const { data } = await client.post<ScheduleData>("/schedule/generate");
  return data;
}

export async function updateConfig(payload: ScheduleConfigInput): Promise<ScheduleConfig> {
  const { data } = await client.put<ScheduleConfig>("/schedule/config", payload);
  return data;
}

export async function clearSchedule(adminPassword: string): Promise<ScheduleConfig> {
  const { data } = await client.post<ScheduleConfig>("/schedule/clear", {
    admin_password: adminPassword,
  });
  return data;
}

export interface AIOptimizeResult {
  issues: string[];
  mode: "generate" | "optimize";
}

export async function aiOptimize(message: string): Promise<AIOptimizeResult> {
  const { data } = await client.post<AIOptimizeResult>(
    "/schedule/ai-optimize",
    { message },
    { timeout: 0 }, // 生成/优化耗时较长，不设超时上限
  );
  return data;
}

export async function aiCheck(message: string): Promise<AIOptimizeResult> {
  const { data } = await client.post<AIOptimizeResult>(
    "/schedule/ai-check",
    { message },
    { timeout: 0 }, // AI 检查耗时较长，不设超时上限
  );
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

export async function createEntry(input: EntryCreateInput): Promise<ScheduleEntry> {
  const { data } = await client.post<ScheduleEntry>("/schedule/entries", input);
  return data;
}

export async function deleteEntry(entryId: number): Promise<void> {
  await client.delete(`/schedule/entries/${entryId}`);
}

export async function addGroup(entryId: number): Promise<EntryDetail> {
  const { data } = await client.post<EntryDetail>(`/schedule/entries/${entryId}/groups`);
  return data;
}

export async function deleteGroup(entryId: number, groupId: number): Promise<EntryDetail> {
  const { data } = await client.delete<EntryDetail>(`/schedule/entries/${entryId}/groups/${groupId}`);
  return data;
}

export async function addLane(entryId: number, input: LaneCreateInput): Promise<EntryDetail> {
  const { data } = await client.post<EntryDetail>(`/schedule/entries/${entryId}/lanes/add`, input);
  return data;
}

export async function deleteLane(entryId: number, laneId: number): Promise<EntryDetail> {
  const { data } = await client.delete<EntryDetail>(`/schedule/entries/${entryId}/lanes/${laneId}`);
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
