import { projectContext } from "../projectContext";
import type { BusinessCaseAnalysis, ConfirmedBusinessCase, ProjectContext } from "../types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";
const PUBLIC_ERROR = "No fue posible analizar el caso en este momento. Intenta nuevamente.";

async function requestJson<T>(path: string, body: unknown, signal?: AbortSignal): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal,
  });

  if (!response.ok) {
    throw new Error(PUBLIC_ERROR);
  }

  return response.json() as Promise<T>;
}

export async function analyzeBusinessCase(
  description: string,
  context?: ProjectContext,
  signal?: AbortSignal,
): Promise<BusinessCaseAnalysis> {
  const submittedContext = projectContext(context);
  const result = await requestJson<BusinessCaseAnalysis>(
    "/api/business-cases/analyze",
    { description: description.trim(), project_context: submittedContext },
    signal,
  );
  return { ...result, project_context: projectContext(result.project_context ?? submittedContext) };
}

export async function confirmBusinessCase(
  analysis: BusinessCaseAnalysis,
  signal?: AbortSignal,
): Promise<ConfirmedBusinessCase> {
  const context = projectContext(analysis.project_context);
  const result = await requestJson<ConfirmedBusinessCase>(
    "/api/business-cases/confirm",
    {
      business_case: analysis.business_case,
      project_context: context,
      requirements: analysis.requirements,
      additional_context: analysis.additional_context,
      priority_ranking: analysis.priority_ranking,
    },
    signal,
  );
  return { ...result, project_context: projectContext(result.project_context ?? context) };
}
