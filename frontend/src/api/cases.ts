import type { BusinessCaseAnalysis, CaseRecord, CaseSummary } from "../types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

export const SAVE_ERROR = "No fue posible guardar el caso en este momento. Intenta nuevamente.";
export const LOAD_ERROR = "No fue posible consultar los casos en este momento. Intenta nuevamente.";

export class CaseNotFoundError extends Error {
  constructor() {
    super("No encontramos ese caso.");
    this.name = "CaseNotFoundError";
  }
}

async function request<T>(path: string, errorMessage: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, init);
  if (response.status === 404) throw new CaseNotFoundError();
  if (!response.ok) throw new Error(errorMessage);
  return response.json() as Promise<T>;
}

/** Confirma los requisitos, calcula la recomendación en el backend y guarda el caso. */
export function createCase(analysis: BusinessCaseAnalysis): Promise<CaseRecord> {
  return request<CaseRecord>("/api/cases", SAVE_ERROR, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      business_case: analysis.business_case,
      requirements: analysis.requirements,
      additional_context: analysis.additional_context,
      priority_ranking: analysis.priority_ranking,
    }),
  });
}

export function getCase(caseId: string): Promise<CaseRecord> {
  return request<CaseRecord>(`/api/cases/${encodeURIComponent(caseId)}`, LOAD_ERROR);
}

export function listCases(): Promise<CaseSummary[]> {
  return request<CaseSummary[]>("/api/cases", LOAD_ERROR);
}
