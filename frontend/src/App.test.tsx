import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import App from "./App";
import type { BusinessCaseAnalysis } from "./types";

const unknown = { value: "unknown", status: "unknown" as const, evidence: [] };
const analysis: BusinessCaseAnalysis = {
  business_case: "Una aplicacion interna con trafico estable y presupuesto limitado.",
  requirements: {
    service_interruption_tolerance: unknown,
    business_continuity_criticality: unknown,
    information_sensitivity: unknown,
    available_budget: {
      value: "low",
      status: "detected",
      evidence: ["presupuesto limitado"],
    },
    demand_pattern: {
      value: "constant",
      status: "detected",
      evidence: ["trafico estable"],
    },
    expected_load_volume: unknown,
  },
  additional_context: {
    business_description: null,
    expected_users: 50,
    concurrent_users: null,
    requests_per_second: null,
    expected_growth: null,
    geographical_scope: null,
    explicit_availability_target: null,
    explicit_response_time_target: null,
    budget_raw: null,
    currency: null,
    budget_period: null,
  },
  missing_requirements: [
    "service_interruption_tolerance",
    "business_continuity_criticality",
    "information_sensitivity",
    "expected_load_volume",
  ],
  warnings: [],
  requires_user_confirmation: true,
};

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("PB-01 flow", () => {
  it("analyzes, lets the user edit, and confirms the requirements", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({ ok: true, json: async () => analysis })
      .mockImplementationOnce(async (_url: string, options: RequestInit) => {
        const request = JSON.parse(String(options.body));
        return {
          ok: true,
          json: async () => ({ status: "confirmed", ...request }),
        };
      });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    render(<App />);

    await user.type(
      screen.getByLabelText("Caso de negocio"),
      "Una aplicacion interna con trafico estable y presupuesto limitado.",
    );
    await user.click(screen.getByRole("button", { name: "Analizar requisitos" }));

    expect(await screen.findByRole("heading", { name: "Requisitos identificados" })).toBeVisible();
    await user.selectOptions(
      screen.getByLabelText("Revisar valor", { selector: "#service_interruption_tolerance" }),
      "medium",
    );
    await user.click(screen.getByRole("button", { name: "Confirmar requisitos" }));

    expect(await screen.findByText("Requisitos confirmados correctamente.")).toBeVisible();
    const confirmBody = JSON.parse(fetchMock.mock.calls[1][1].body);
    expect(confirmBody.requirements.service_interruption_tolerance).toMatchObject({
      value: "medium",
      status: "detected",
    });
    expect(confirmBody).not.toHaveProperty("architecture");
  });

  it("shows the friendly error when analysis fails", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false }));
    const user = userEvent.setup();
    render(<App />);

    await user.type(screen.getByLabelText("Caso de negocio"), "Un caso valido para analizar.");
    await user.click(screen.getByRole("button", { name: "Analizar requisitos" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "No fue posible analizar el caso en este momento. Intenta nuevamente.",
    );
  });
});
