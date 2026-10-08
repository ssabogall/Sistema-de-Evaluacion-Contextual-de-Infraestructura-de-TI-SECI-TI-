import type { BusinessCaseAnalysis, ConfirmedBusinessCase } from "../types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";
const PUBLIC_ERROR = "No fue posible analizar el caso en este momento. Intenta nuevamente.";

async function requestJson<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    throw new Error(PUBLIC_ERROR);
  }

  return response.json() as Promise<T>;
}

export function analyzeBusinessCase(description: string): Promise<BusinessCaseAnalysis> {
  return requestJson<BusinessCaseAnalysis>("/api/business-cases/analyze", { description });
}

export function confirmBusinessCase(
  analysis: BusinessCaseAnalysis,
): Promise<ConfirmedBusinessCase> {
  return requestJson<ConfirmedBusinessCase>("/api/business-cases/confirm", {
    business_case: analysis.business_case,
    requirements: analysis.requirements,
    additional_context: analysis.additional_context,
  });
}
