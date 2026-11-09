import type { BusinessCaseAnalysis, CaseRecord, CaseSummary } from "../types";
import { projectContext } from "../projectContext";

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

function withDefaults(record: CaseRecord): CaseRecord {
  return {
    ...record,
    confirmed: {
      ...record.confirmed,
      project_context: projectContext(record.confirmed.project_context),
    },
    advice: record.advice ?? null,
  };
}

/** Confirma los requisitos, calcula la recomendación en el backend y guarda el caso. */
export async function createCase(
  analysis: BusinessCaseAnalysis,
  signal?: AbortSignal,
): Promise<CaseRecord> {
  const record = await request<CaseRecord>("/api/cases", SAVE_ERROR, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      business_case: analysis.business_case,
      project_context: projectContext(analysis.project_context),
      requirements: analysis.requirements,
      additional_context: analysis.additional_context,
      priority_ranking: analysis.priority_ranking,
    }),
    signal,
  });
  return withDefaults(record);
}

export async function getCase(caseId: string, signal?: AbortSignal): Promise<CaseRecord> {
  return withDefaults(
    await request<CaseRecord>(`/api/cases/${encodeURIComponent(caseId)}`, LOAD_ERROR, { signal }),
  );
}

export async function listCases(): Promise<CaseSummary[]> {
  const cases = await request<CaseSummary[]>("/api/cases", LOAD_ERROR);
  return cases.map((item) => ({ ...item, scenario: item.scenario ?? "new" }));
}
