import request from './client';

export interface ScoreDetail {
  id: number;
  event_name: string;
  group_name: string;
  gender: string;
  is_team_event: boolean;
  athlete_name: string | null;
  rank: number;
  result: string;
  base_score: number;
  is_record_broken: boolean;
  final_score: number;
  created_at: string;
}

export interface ClassScore {
  id: number;
  class_team_id: number;
  grade: string;
  class_name: string;
  total_score: number;
  rank_in_grade: number;
  updated_at: string;
}

export interface AthleteScore {
  id: number;
  athlete_id: number;
  class_team_id: number;
  grade: string;
  class_name: string;
  athlete_name: string;
  total_score: number;
  rank_in_grade: number;
  updated_at: string;
}

export interface CalculateSummary {
  total_details: number;
  total_athletes: number;
  total_classes: number;
  calculated_at: string;
}

/**
 * 一键统计
 */
export function calculateScores() {
  return request.post<CalculateSummary>('/scores/calculate').then(res => res.data);
}

/**
 * 获取班级得分列表
 */
export function listClassScores(grade?: string) {
  return request.get<ClassScore[]>('/scores/classes', { params: { grade } }).then(res => res.data);
}

/**
 * 获取班级得分明细
 */
export function getClassDetails(classTeamId: number) {
  return request.get<ScoreDetail[]>(`/scores/classes/${classTeamId}/details`).then(res => res.data);
}

/**
 * 获取个人得分列表
 */
export function listAthleteScores(grade?: string) {
  return request.get<AthleteScore[]>('/scores/athletes', { params: { grade } }).then(res => res.data);
}

/**
 * 获取个人得分明细
 */
export function getAthleteDetails(athleteId: number) {
  return request.get<ScoreDetail[]>(`/scores/athletes/${athleteId}/details`).then(res => res.data);
}
