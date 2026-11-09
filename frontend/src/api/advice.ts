import type { SavedArchitectureAdvice } from "../types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";
export const ADVICE_ERROR = "No fue posible generar las recomendaciones. Intenta nuevamente.";

export async function generateAdvice(
  caseId: string,
  regenerate = false,
  signal?: AbortSignal,
): Promise<SavedArchitectureAdvice> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/api/cases/${encodeURIComponent(caseId)}/advice`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ regenerate }),
      signal,
    });
  } catch (error) {
    if (signal?.aborted) throw error;
    throw new Error(ADVICE_ERROR, { cause: error });
  }

  if (!response.ok) {
    let message = ADVICE_ERROR;
    if (response.status === 503) {
      const body: unknown = await response.json().catch(() => null);
      if (
        body &&
        typeof body === "object" &&
        "detail" in body &&
        typeof body.detail === "string" &&
        body.detail.trim()
      ) {
        message = body.detail.trim();
      }
    }
    throw new Error(message);
  }

  try {
    return (await response.json()) as SavedArchitectureAdvice;
  } catch (error) {
    if (signal?.aborted) throw error;
    throw new Error(ADVICE_ERROR, { cause: error });
  }
}
