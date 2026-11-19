import type { AwsConnection, AwsDeployment } from "../types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";
const REQUEST_ERROR = "No fue posible comunicarse con AWS. Intenta refrescar el estado.";

async function request<T>(path: string, init: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, init);
  } catch (error) {
    if (init.signal?.aborted) throw error;
    throw new Error(REQUEST_ERROR, { cause: error });
  }

  if (!response.ok) {
    let message = REQUEST_ERROR;
    try {
      const body: unknown = await response.json();
      if (
        body &&
        typeof body === "object" &&
        "detail" in body &&
        typeof body.detail === "string" &&
        body.detail.trim()
      ) {
        message = body.detail.trim();
      }
    } catch {
      // Un proxy puede devolver un error sin JSON.
    }
    throw new Error(message);
  }

  try {
    return (await response.json()) as T;
  } catch (error) {
    if (init.signal?.aborted) throw error;
    throw new Error(REQUEST_ERROR, { cause: error });
  }
}

function deploymentPath(caseId: string): string {
  return `/api/cases/${encodeURIComponent(caseId)}/deployment`;
}

export function getAwsConnection(signal?: AbortSignal): Promise<AwsConnection> {
  return request("/api/aws/connection", { signal });
}

export function getCaseDeployment(caseId: string, signal?: AbortSignal): Promise<AwsDeployment> {
  return request(deploymentPath(caseId), { signal });
}

export function createCaseDeployment(caseId: string, signal?: AbortSignal): Promise<AwsDeployment> {
  return request(deploymentPath(caseId), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ confirm_costs: true }),
    signal,
  });
}

export function deleteCaseDeployment(caseId: string, signal?: AbortSignal): Promise<AwsDeployment> {
  return request(deploymentPath(caseId), { method: "DELETE", signal });
}
