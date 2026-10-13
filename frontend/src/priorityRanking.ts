import { PRIORITY_CONFIGS } from "./requirements";
import type { PriorityRanking, PriorityStatement } from "./types";

export type PriorityState = "empty" | "partial" | "edited" | "detected";

const PRIORITY_KEYS: PriorityStatement[] = PRIORITY_CONFIGS.map((config) => config.key);

export const EMPTY_PRIORITY_RANKING: PriorityRanking = {
  never_stop_working: null,
  lowest_cost: null,
  fast_under_load: null,
  protect_information: null,
};

export function hasAnyPriority(ranking: PriorityRanking): boolean {
  return PRIORITY_KEYS.some((key) => ranking[key] !== null);
}

export function isCompleteRanking(ranking: PriorityRanking): boolean {
  return PRIORITY_KEYS.every((key) => ranking[key] !== null);
}

export function rankingsEqual(a: PriorityRanking, b: PriorityRanking): boolean {
  return PRIORITY_KEYS.every((key) => a[key] === b[key]);
}

/**
 * Asigna una posición a una prioridad sin dejar posiciones repetidas: si otra prioridad ya
 * ocupaba esa posición, intercambia (la otra recibe la posición anterior de esta, o queda
 * sin definir si esta no tenía).
 */
export function assignPriority(
  ranking: PriorityRanking,
  key: PriorityStatement,
  position: number | null,
): PriorityRanking {
  const next = { ...ranking, [key]: position };
  if (position === null) return next;

  const occupant = PRIORITY_KEYS.find((other) => other !== key && ranking[other] === position);
  if (occupant) next[occupant] = ranking[key];
  return next;
}

export function priorityState(ranking: PriorityRanking, detected: PriorityRanking): PriorityState {
  if (!hasAnyPriority(ranking)) return "empty";
  if (!isCompleteRanking(ranking)) return "partial";
  return rankingsEqual(ranking, detected) ? "detected" : "edited";
}
