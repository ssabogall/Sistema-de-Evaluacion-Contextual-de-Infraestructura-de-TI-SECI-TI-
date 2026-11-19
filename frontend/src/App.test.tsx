import { act, fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "./App";
import { analyzeBusinessCase, confirmBusinessCase } from "./api/businessCases";
import { createCase, getCase, listCases } from "./api/cases";
import { CasePage } from "./pages/CasePage";
import { adviceFixture } from "./test/adviceFixture";
import type {
  ArchitectureId,
  BusinessCaseAnalysis,
  CaseRecord,
  CaseSummary,
  PriorityRanking,
  ProjectContext,
  Recommendation,
  RequirementKey,
  SavedArchitectureAdvice,
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

describe("Project context", () => {
  const currentArchitecture = "API y procesos de notificación en una VM. PostgreSQL local, " +
    "integración con pagos, acceso por VPN, copias diarias y monitoreo manual. " +
    "Las notificaciones se envían durante el pago.";
  const existingContext: ProjectContext = { scenario: "existing", current_architecture: currentArchitecture };

  it("sends a complete existing context through analysis, review and saving without generating advice", async () => {
    const record = caseRecord();
    record.confirmed.project_context = existingContext;
    const fetchMock = mockApi({
      "POST /api/business-cases/analyze": () => ({ body: { ...analysis, project_context: existingContext } }),
      "POST /api/cases": () => ({ status: 201, body: record }),
      [`GET /api/cases/${CASE_ID}`]: () => ({ body: record }),
    });
    const user = userEvent.setup();
    render(<App />);
    await user.click(screen.getByRole("radio", { name: "Plataforma existente" }));
    fireEvent.change(screen.getByLabelText("Caso de negocio"), { target: { value: `  ${analysis.business_case}  ` } });
    fireEvent.change(screen.getByLabelText("Arquitectura actual completa"), { target: { value: `  ${currentArchitecture}  ` } });
    await user.click(screen.getByRole("button", { name: "Analizar requisitos" }));
    await screen.findByRole("heading", { name: "Requisitos identificados" });
    expect(screen.getByText("Plataforma existente")).toBeVisible();
    expect(screen.getByText(currentArchitecture)).toBeVisible();
    expect(fetchMock.mock.calls[0][0]).toBe("/api/business-cases/analyze");
    expect(JSON.parse(String(fetchMock.mock.calls[0][1]?.body))).toEqual({
      description: analysis.business_case, project_context: existingContext,
    });
    await user.click(screen.getByRole("button", { name: CONFIRM }));
    await screen.findByRole("heading", { name: RECOMMENDATION_HEADING });
    expect(createCaseBody(fetchMock).project_context).toEqual(existingContext);
    expect(screen.getByText(currentArchitecture)).toBeVisible();
    expect(screen.getByText("Plataforma existente")).toBeVisible();
    expect(fetchMock.mock.calls.map(([url]) => url)).not.toContain(`/api/cases/${CASE_ID}/advice`);
  });

  it("preserves the architecture draft across scenario changes and returning from review", async () => {
    const fetchMock = mockFlow(analysis);
    const user = userEvent.setup();
    render(<App />);
    expect(screen.getByRole("radio", { name: "Plataforma nueva" })).toBeChecked();
    expect(screen.queryByLabelText("Arquitectura actual completa")).not.toBeInTheDocument();
    await user.click(screen.getByRole("radio", { name: "Plataforma existente" }));
    fireEvent.change(screen.getByLabelText("Arquitectura actual completa"), { target: { value: currentArchitecture } });
    fireEvent.change(screen.getByLabelText("Caso de negocio"), { target: { value: analysis.business_case } });
    await user.click(screen.getByRole("radio", { name: "Plataforma nueva" }));
    expect(screen.queryByLabelText("Arquitectura actual completa")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Analizar requisitos" }));
    await screen.findByRole("heading", { name: "Requisitos identificados" });
    expect(JSON.parse(String(fetchMock.mock.calls[0][1]?.body)).project_context).toEqual({ scenario: "new", current_architecture: null });
    await user.click(screen.getByRole("button", { name: "Volver al caso" }));
    await user.click(screen.getByRole("radio", { name: "Plataforma existente" }));
    expect(screen.getByLabelText("Arquitectura actual completa")).toHaveValue(currentArchitecture);
    expect(screen.getByLabelText("Caso de negocio")).toHaveValue(analysis.business_case);
  });

  it("validates existing architecture limits after trimming and supports native radio keyboard navigation", async () => {
    const fetchMock = mockFlow(analysis);
    const user = userEvent.setup();
    render(<App />);
    fireEvent.change(screen.getByLabelText("Caso de negocio"), { target: { value: analysis.business_case } });
    const newRadio = screen.getByRole("radio", { name: "Plataforma nueva" });
    newRadio.focus();
    await user.keyboard("{ArrowRight}");
    expect(screen.getByRole("radio", { name: "Plataforma existente" })).toBeChecked();
    const architecture = screen.getByLabelText("Arquitectura actual completa");
    const analyze = screen.getByRole("button", { name: "Analizar requisitos" });
    for (const value of ["", "          ", "  123456789  ", "a".repeat(20_001)]) {
      fireEvent.change(architecture, { target: { value } });
      expect(analyze).toBeDisabled();
      expect(architecture).toHaveAttribute("aria-invalid", "true");
    }
    for (const value of ["  1234567890  ", `  ${"a".repeat(20_000)}  `]) {
      fireEvent.change(architecture, { target: { value } });
      expect(analyze).toBeEnabled();
      expect(architecture).toHaveAttribute("aria-invalid", "false");
    }
    fireEvent.change(screen.getByLabelText("Caso de negocio"), { target: { value: "  123456789  " } });
    expect(analyze).toBeDisabled();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("shows existing and legacy default scenarios in the saved cases list", async () => {
    mockApi({ "GET /api/cases": () => ({ body: [
      { id: "existing-case", created_at: caseRecord().created_at, business_case_excerpt: "Caso existente", architecture: "architecture_b", trade_off: false, scenario: "existing" },
      { id: "legacy-case", created_at: caseRecord().created_at, business_case_excerpt: "Caso anterior", architecture: "architecture_a", trade_off: false },
    ] }) });
    window.history.pushState({}, "", "/casos");
    render(<App />);
    expect(await screen.findByText("Plataforma existente")).toBeVisible();
    expect(screen.getByText("Plataforma nueva")).toBeVisible();
  });
});

describe("Persisted advice integration", () => {
  it("generates on demand, reloads saved advice via GET without another POST and preserves it on 503", async () => {
    let savedAdvice: SavedArchitectureAdvice | null = null;
    let advicePosts = 0;
    const saved = adviceFixture();
    const fetchMock = mockApi({
      [`GET /api/cases/${CASE_ID}`]: () => ({ body: caseRecord({ advice: savedAdvice }) }),
      [`POST /api/cases/${CASE_ID}/advice`]: (init) => {
        advicePosts++;
        expect(JSON.parse(String(init?.body))).toEqual({ regenerate: advicePosts > 1 });
        if (advicePosts > 1) return { status: 503, body: { detail: "El proveedor IA no está disponible." } };
        savedAdvice = saved;
        return { body: saved };
      },
    });
    window.history.pushState({}, "", `/casos/${CASE_ID}`);
    const user = userEvent.setup();
    const first = render(<App />);
    await screen.findByRole("heading", { name: RECOMMENDATION_HEADING });
    expect(advicePosts).toBe(0);
    await user.click(screen.getByRole("button", { name: "Generar recomendaciones" }));
    expect(await screen.findByText(saved.content.summary)).toBeVisible();
    expect(advicePosts).toBe(1);

    first.unmount();
    render(<App />);
    expect(await screen.findByText(saved.content.summary)).toBeVisible();
    expect(fetchMock.mock.calls.filter(([url, init]) => url === `/api/cases/${CASE_ID}` && !init?.method)).toHaveLength(2);
    expect(advicePosts).toBe(1);
    await user.click(screen.getByRole("button", { name: "Regenerar recomendaciones" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("El proveedor IA no está disponible.");
    expect(screen.getByText(saved.content.summary)).toBeVisible();
    expect(screen.getByRole("heading", { name: RECOMMENDATION_HEADING })).toBeVisible();
    await user.click(screen.getByText("Ver cálculo por variable"));
    expect(screen.getByRole("table")).toBeVisible();
    expect(screen.getByText("Despliegue en AWS")).toBeVisible();
    expect(advicePosts).toBe(2);
  });

  it("loads legacy cases with an empty report and default new scenario", async () => {
    const fetchMock = mockApi({ [`GET /api/cases/${CASE_ID}`]: () => ({ body: caseRecord() }) });
    window.history.pushState({}, "", `/casos/${CASE_ID}`);
    render(<App />);
    await screen.findByRole("heading", { name: RECOMMENDATION_HEADING });
    expect(screen.getByText("Plataforma nueva")).toBeVisible();
    expect(screen.getByText("Sin informe generado.")).toBeVisible();
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
});

describe("Context API contract and defaults", () => {
  it.each<ProjectContext>([
    { scenario: "new", current_architecture: null },
    { scenario: "existing", current_architecture: "  Aplicación monolítica, PostgreSQL y acceso por VPN.  " },
  ])("sends project_context on analyze, confirm and create for $scenario", async (context) => {
    const normalized = { ...context, current_architecture: context.current_architecture?.trim() ?? null };
    const fetchMock = mockApi({
      "POST /api/business-cases/analyze": () => ({ body: analysis }),
      "POST /api/business-cases/confirm": () => ({ body: caseRecord().confirmed }),
      "POST /api/cases": () => ({ body: caseRecord() }),
    });
    const signal = new AbortController().signal;
    const result = await analyzeBusinessCase(`  ${analysis.business_case}  `, context, signal);
    expect(result.project_context).toEqual(normalized);
    const confirmed = await confirmBusinessCase(result, signal);
    expect(confirmed.project_context).toEqual(normalized);
    await createCase(result, signal);
    expect(fetchMock.mock.calls.map(([url]) => url)).toEqual([
      "/api/business-cases/analyze", "/api/business-cases/confirm", "/api/cases",
    ]);
    expect(JSON.parse(String(fetchMock.mock.calls[0][1]?.body))).toEqual({ description: analysis.business_case, project_context: normalized });
    for (const [, init] of fetchMock.mock.calls.slice(1)) {
      expect(JSON.parse(String(init?.body))).toEqual({
        business_case: analysis.business_case,
        project_context: normalized,
        requirements: analysis.requirements,
        additional_context: analysis.additional_context,
        priority_ranking: analysis.priority_ranking,
      });
      expect(init?.signal).toBe(signal);
    }
  });

  it("normalizes legacy analysis, confirmation, case and list responses", async () => {
    mockApi({
      "POST /api/business-cases/analyze": () => ({ body: analysis }),
      "POST /api/business-cases/confirm": () => ({ body: caseRecord().confirmed }),
      "POST /api/cases": () => ({ body: caseRecord() }),
      [`GET /api/cases/${CASE_ID}`]: () => ({ body: caseRecord() }),
      "GET /api/cases": () => ({ body: [{ id: CASE_ID }] }),
    });
    const context = { scenario: "new", current_architecture: null };
    expect((await analyzeBusinessCase(analysis.business_case)).project_context).toEqual(context);
    expect((await confirmBusinessCase(analysis)).project_context).toEqual(context);
    for (const record of [await createCase(analysis), await getCase(CASE_ID)]) {
      expect(record.confirmed.project_context).toEqual(context);
      expect(record.advice).toBeNull();
    }
    expect((await listCases())[0].scenario).toBe("new");
  });
});

describe("Request lifecycle", () => {
  it.each(["analysis", "confirmation"])("aborts %s on unmount and ignores late results", async (stage) => {
    let resolve!: (value: unknown) => void;
    const pending = new Promise((yes) => { resolve = yes; });
    let requestSignal: AbortSignal | undefined;
    vi.stubGlobal("fetch", vi.fn(async (_url: string, init?: RequestInit) => {
      if (stage === "analysis" || init?.method === "POST" && _url === "/api/cases") {
        requestSignal = init?.signal as AbortSignal;
        await pending;
        return { ok: true, json: async () => stage === "analysis" ? analysis : caseRecord() };
      }
      return { ok: true, json: async () => analysis };
    }));
    const user = userEvent.setup();
    const view = render(<App />);
    fireEvent.change(screen.getByLabelText("Caso de negocio"), { target: { value: analysis.business_case } });
    await user.click(screen.getByRole("button", { name: "Analizar requisitos" }));
    if (stage === "confirmation") {
      await screen.findByRole("heading", { name: "Requisitos identificados" });
      await user.click(screen.getByRole("button", { name: CONFIRM }));
    }
    view.unmount();
    expect(requestSignal?.aborted).toBe(true);
    await act(async () => resolve(undefined));
    expect(window.location.pathname).toBe("/");
  });

  it("ignores a late case GET when navigating and aborts GET on unmount", async () => {
    let resolveOld!: (value: unknown) => void;
    const old = new Promise((yes) => { resolveOld = yes; });
    const fetchMock = vi.fn(async (url: string) => {
      if (url === "/api/cases/case-a") await old;
      return { ok: true, json: async () => caseRecord({ id: url.endsWith("case-a") ? "case-a" : "case-b" }) };
    });
    vi.stubGlobal("fetch", fetchMock);
    const { rerender, unmount } = render(<CasePage caseId="case-a" />);
    const firstSignal = (vi.mocked(fetch).mock.calls[0][1] as RequestInit).signal;
    rerender(<CasePage caseId="case-b" />);
    expect(firstSignal?.aborted).toBe(true);
    await screen.findByText("Caso case-b");
    await act(async () => resolveOld(undefined));
    expect(screen.queryByText("Caso case-a")).not.toBeInTheDocument();
    const secondSignal = (vi.mocked(fetch).mock.calls[1][1] as RequestInit).signal;
    unmount();
    expect(secondSignal?.aborted).toBe(true);
  });
});
