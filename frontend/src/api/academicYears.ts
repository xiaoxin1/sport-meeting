import client from "./client";

export interface AcademicYear {
  id: number;
  name: string;
  meet_start_date: string | null;
  meet_end_date: string | null;
  is_active: boolean;
  created_at: string;
}

export interface AcademicYearInput {
  name: string;
  meet_start_date: string | null;
  meet_end_date: string | null;
}

export async function listYears(): Promise<AcademicYear[]> {
  const { data } = await client.get<AcademicYear[]>("/academic-years");
  return data;
}

export async function getActiveYear(): Promise<AcademicYear | null> {
  const { data } = await client.get<AcademicYear | null>("/academic-years/active");
  return data;
}

export async function createYear(payload: AcademicYearInput): Promise<AcademicYear> {
  const { data } = await client.post<AcademicYear>("/academic-years", payload);
  return data;
}

export async function updateYear(
  id: number,
  payload: Partial<AcademicYearInput>,
): Promise<AcademicYear> {
  const { data } = await client.put<AcademicYear>(`/academic-years/${id}`, payload);
  return data;
}

export async function activateYear(id: number): Promise<AcademicYear> {
  const { data } = await client.post<AcademicYear>(`/academic-years/${id}/activate`);
  return data;
}

export async function deleteYear(id: number): Promise<void> {
  await client.delete(`/academic-years/${id}`);
}
