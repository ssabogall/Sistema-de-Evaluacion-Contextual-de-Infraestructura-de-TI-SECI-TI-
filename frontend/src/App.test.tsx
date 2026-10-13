import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "./App";
import type {
  ArchitectureId,
  BusinessCaseAnalysis,
  CaseRecord,
  CaseSummary,
  PriorityRanking,
  Recommendation,
  RequirementKey,
} from "./types";

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
  priority_ranking: {
    never_stop_working: null,
    lowest_cost: null,
    fast_under_load: null,
    protect_information: null,
  },
  priority_ranking_evidence: [],
  warnings: [],
  requires_user_confirmation: true,
};

const NEVER_STOP = "Que la aplicación nunca deje de funcionar, incluso si eso cuesta más.";
const LOWEST_COST = "Mantener el costo de infraestructura lo más bajo posible.";
const FAST_UNDER_LOAD = "Que la aplicación responda rápido incluso en momentos de mucho tráfico.";
const PROTECT_INFORMATION = "Proteger al máximo la información que manejo.";

const REQUIREMENT_KEYS: RequirementKey[] = [
  "service_interruption_tolerance",
  "business_continuity_criticality",
  "information_sensitivity",
  "available_budget",
  "demand_pattern",
  "expected_load_volume",
];

function perVariable(value: number): Record<RequirementKey, number> {
  return Object.fromEntries(REQUIREMENT_KEYS.map((key) => [key, value])) as Record<
    RequirementKey,
    number
  >;
}

const recommendation: Recommendation = {
  architecture: "architecture_b",
  runner_up: "architecture_c",
  totals: { architecture_a: 0.9, architecture_b: 1.7, architecture_c: 1.4 },
  margin: 0.3,
  trade_off: true,
  tie_broken: false,
  message: "Se recomienda la Arquitectura B (escalable), con un puntaje de 1.70.",
  weights: perVariable(1 / 6),
  weights_source: "equal",
  unknown_variables: ["information_sensitivity"],
  contributions: {
    architecture_a: perVariable(0.15),
    architecture_b: perVariable(0.28),
    architecture_c: perVariable(0.23),
  } satisfies Record<ArchitectureId, Record<RequirementKey, number>>,
};

const CASE_ID = "abcdef0123456789abcdef0123456789";

function caseRecord(overrides: Partial<CaseRecord> = {}): CaseRecord {
  return {
    id: CASE_ID,
    created_at: "2026-10-13T20:30:00Z",
    confirmed: {
      status: "confirmed",
      business_case: analysis.business_case,
      requirements: analysis.requirements,
      additional_context: analysis.additional_context,
      priority_ranking: analysis.priority_ranking,
    },
    recommendation,
    ...overrides,
  };
}

type Route = (init?: RequestInit) => { status?: number; body?: unknown };

function mockApi(routes: Record<string, Route>) {
  const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
    const key = `${init?.method ?? "GET"} ${url}`;
    const route = routes[key];
    if (!route) throw new Error(`Unexpected request: ${key}`);
    const { status = 200, body } = route(init);
    return { ok: status < 400, status, json: async () => body };
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

/** Cuerpo JSON enviado en la última llamada a POST /api/cases. */
function createCaseBody(fetchMock: ReturnType<typeof mockApi>) {
  const call = fetchMock.mock.calls.find(
    ([url, init]) => url === "/api/cases" && init?.method === "POST",
  );
  return JSON.parse(String(call?.[1]?.body));
}

/** API completa del flujo: analizar, guardar el caso y consultarlo por id. */
function mockFlow(analysisResult: BusinessCaseAnalysis) {
  return mockApi({
    "POST /api/business-cases/analyze": () => ({ body: analysisResult }),
    "POST /api/cases": () => ({ status: 201, body: caseRecord() }),
    [`GET /api/cases/${CASE_ID}`]: () => ({ body: caseRecord() }),
  });
}

async function openReview(user: ReturnType<typeof userEvent.setup>) {
  render(<App />);
  await user.type(
    screen.getByLabelText("Caso de negocio"),
    "Una aplicacion interna con trafico estable y presupuesto limitado.",
  );
  await user.click(screen.getByRole("button", { name: "Analizar requisitos" }));
  await screen.findByRole("heading", { name: "Requisitos identificados" });
}

const CONFIRM = "Confirmar y ver recomendación";
const RECOMMENDATION_HEADING = "Arquitectura B · Escalable";

beforeEach(() => {
  window.history.pushState({}, "", "/");
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("Analysis flow", () => {
  it("analyzes, lets the user edit, saves the case and opens its page", async () => {
    const fetchMock = mockFlow(analysis);
    const user = userEvent.setup();
    await openReview(user);

    expect(screen.getByRole("heading", { name: "Requisitos identificados" })).toBeVisible();
    await user.selectOptions(
      screen.getByLabelText("Revisar valor", { selector: "#service_interruption_tolerance" }),
      "medium",
    );
    await user.click(screen.getByRole("button", { name: CONFIRM }));

    expect(await screen.findByRole("heading", { name: RECOMMENDATION_HEADING })).toBeVisible();
    expect(window.location.pathname).toBe(`/casos/${CASE_ID}`);
    const body = createCaseBody(fetchMock);
    expect(body.requirements.service_interruption_tolerance).toMatchObject({
      value: "medium",
      status: "detected",
    });
    expect(body).not.toHaveProperty("architecture");
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

  it("keeps the review open and shows an error when saving fails", async () => {
    mockApi({
      "POST /api/business-cases/analyze": () => ({ body: analysis }),
      "POST /api/cases": () => ({ status: 503, body: { detail: "interno" } }),
    });
    const user = userEvent.setup();
    await openReview(user);

    await user.click(screen.getByRole("button", { name: CONFIRM }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "No fue posible guardar el caso en este momento. Intenta nuevamente.",
    );
    expect(window.location.pathname).toBe("/");
    expect(screen.getByRole("heading", { name: "Requisitos identificados" })).toBeVisible();
  });
});

describe("Priority ranking", () => {
  it("starts without an order when the text does not state one", async () => {
    const fetchMock = mockFlow(analysis);
    const user = userEvent.setup();
    await openReview(user);

    expect(screen.getByTestId("priority-state")).toHaveTextContent("Sin definir");
    expect(
      screen.getByText("Sin un orden definido, las cuatro prioridades pesan igual."),
    ).toBeVisible();

    await user.click(screen.getByRole("button", { name: CONFIRM }));
    await screen.findByRole("heading", { name: RECOMMENDATION_HEADING });

    expect(createCaseBody(fetchMock).priority_ranking).toEqual(analysis.priority_ranking);
  });

  it("shows the order and evidence transcribed from the text, and sends the edited order", async () => {
    const partial: PriorityRanking = {
      never_stop_working: 1,
      lowest_cost: 2,
      fast_under_load: null,
      protect_information: null,
    };
    const fetchMock = mockFlow({
      ...analysis,
      priority_ranking: partial,
      priority_ranking_evidence: ["primero que no se caiga, luego el costo"],
    });
    const user = userEvent.setup();
    await openReview(user);

    expect(screen.getByTestId("priority-state")).toHaveTextContent("Incompleto");
    expect(screen.getByText("“primero que no se caiga, luego el costo”")).toBeVisible();
    expect(screen.getByLabelText(NEVER_STOP)).toHaveValue("1");
    expect(screen.getByLabelText(LOWEST_COST)).toHaveValue("2");

    await user.selectOptions(screen.getByLabelText(FAST_UNDER_LOAD), "3");
    await user.selectOptions(screen.getByLabelText(PROTECT_INFORMATION), "4");

    expect(screen.getByTestId("priority-state")).toHaveTextContent("Editado por ti");
    await user.click(screen.getByRole("button", { name: CONFIRM }));
    await screen.findByRole("heading", { name: RECOMMENDATION_HEADING });

    expect(createCaseBody(fetchMock).priority_ranking).toEqual({
      never_stop_working: 1,
      lowest_cost: 2,
      fast_under_load: 3,
      protect_information: 4,
    });
  });

  it("marks a complete order from the text as detected and swaps repeated positions", async () => {
    mockFlow({
      ...analysis,
      priority_ranking: {
        never_stop_working: 1,
        lowest_cost: 2,
        fast_under_load: 3,
        protect_information: 4,
      },
      priority_ranking_evidence: ["lo mas importante es que no se caiga"],
    });
    const user = userEvent.setup();
    await openReview(user);

    expect(screen.getByTestId("priority-state")).toHaveTextContent("Detectado en tu texto");

    await user.selectOptions(screen.getByLabelText(LOWEST_COST), "1");

    expect(screen.getByLabelText(LOWEST_COST)).toHaveValue("1");
    expect(screen.getByLabelText(NEVER_STOP)).toHaveValue("2");
    expect(screen.getByTestId("priority-state")).toHaveTextContent("Editado por ti");
  });

  it("clears the order and falls back to equal weights", async () => {
    mockFlow({
      ...analysis,
      priority_ranking: {
        never_stop_working: 1,
        lowest_cost: 2,
        fast_under_load: 3,
        protect_information: 4,
      },
      priority_ranking_evidence: ["lo mas importante es que no se caiga"],
    });
    const user = userEvent.setup();
    await openReview(user);

    await user.click(screen.getByRole("button", { name: "Quitar orden" }));

    expect(screen.getByTestId("priority-state")).toHaveTextContent("Sin definir");
    expect(screen.queryByText("“lo mas importante es que no se caiga”")).not.toBeInTheDocument();
    expect(screen.getByLabelText(NEVER_STOP)).toHaveValue("");
  });
});

describe("Case page", () => {
  it("loads a saved case directly from its URL and shows the recommendation", async () => {
    mockApi({ [`GET /api/cases/${CASE_ID}`]: () => ({ body: caseRecord() }) });
    window.history.pushState({}, "", `/casos/${CASE_ID}`);

    render(<App />);

    expect(await screen.findByRole("heading", { name: RECOMMENDATION_HEADING })).toBeVisible();
    expect(screen.getByText(recommendation.message)).toBeVisible();
    expect(screen.getByText("Resultado ajustado")).toBeVisible();
    expect(screen.getByText("Caso abcdef01")).toBeVisible();
    expect(screen.getAllByRole("img", { name: /^Arquitectura [ABC] · /i })).toHaveLength(3);
    expect(
      screen.getByText("Pesos iguales: no se definió un orden de prioridades completo."),
    ).toBeVisible();
    // Está dentro de <details> cerrado: existe en el documento pero jest-dom no lo da por visible.
    expect(screen.getByText("No definido (valor neutro)")).toBeInTheDocument();
    expect(screen.getByText(analysis.business_case)).toBeVisible();
  });

  it("lists the priorities in the confirmed order when weights came from the ranking", async () => {
    const ranking: PriorityRanking = {
      never_stop_working: 2,
      lowest_cost: 4,
      fast_under_load: 3,
      protect_information: 1,
    };
    const record = caseRecord();
    mockApi({
      [`GET /api/cases/${CASE_ID}`]: () => ({
        body: {
          ...record,
          confirmed: { ...record.confirmed, priority_ranking: ranking },
          recommendation: { ...recommendation, weights_source: "ranking" },
        },
      }),
    });
    window.history.pushState({}, "", `/casos/${CASE_ID}`);

    render(<App />);

    await screen.findByRole("heading", { name: RECOMMENDATION_HEADING });
    const items = within(screen.getByRole("list")).getAllByRole("listitem");
    expect(items.map((item) => item.textContent)).toEqual([
      PROTECT_INFORMATION,
      NEVER_STOP,
      FAST_UNDER_LOAD,
      LOWEST_COST,
    ]);
  });

  it("shows a not-found message for an unknown case", async () => {
    mockApi({ "GET /api/cases/no-existe": () => ({ status: 404, body: { detail: "x" } }) });
    window.history.pushState({}, "", "/casos/no-existe");

    render(<App />);

    expect(await screen.findByRole("heading", { name: "Caso no encontrado" })).toBeVisible();
    expect(screen.getByRole("alert")).toHaveTextContent("No encontramos ese caso.");
  });
});

describe("Saved cases list", () => {
  it("lists saved cases with a link to each one", async () => {
    const summary: CaseSummary = {
      id: CASE_ID,
      created_at: "2026-10-13T20:30:00Z",
      business_case_excerpt: "Una aplicacion interna con trafico estable…",
      architecture: "architecture_a",
      trade_off: false,
    };
    mockApi({ "GET /api/cases": () => ({ body: [summary] }) });
    window.history.pushState({}, "", "/casos");

    render(<App />);

    const link = await screen.findByRole("link", { name: /Una aplicacion interna/ });
    expect(link).toHaveAttribute("href", `/casos/${CASE_ID}`);
    expect(within(link).getByText("Arquitectura A · Básica")).toBeVisible();
  });

  it("shows an empty state when there are no cases", async () => {
    mockApi({ "GET /api/cases": () => ({ body: [] }) });
    window.history.pushState({}, "", "/casos");

    render(<App />);

    expect(await screen.findByText(/Aún no hay casos guardados/)).toBeVisible();
  });

  it("navigates from the top bar without reloading the page", async () => {
    mockApi({ "GET /api/cases": () => ({ body: [] }) });
    const user = userEvent.setup();
    render(<App />);

    await user.click(screen.getByRole("link", { name: "Casos guardados" }));

    expect(await screen.findByRole("heading", { name: "Casos guardados" })).toBeVisible();
    expect(window.location.pathname).toBe("/casos");
  });
});

describe("Unknown routes", () => {
  it("shows a not-found page", () => {
    window.history.pushState({}, "", "/otra-cosa");

    render(<App />);

    expect(screen.getByRole("heading", { name: "Página no encontrada" })).toBeVisible();
  });
});
