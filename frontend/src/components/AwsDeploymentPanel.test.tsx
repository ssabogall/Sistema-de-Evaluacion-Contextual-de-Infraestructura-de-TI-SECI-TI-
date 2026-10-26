import { act, cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  createCaseDeployment,
  deleteCaseDeployment,
  getAwsConnection,
  getCaseDeployment,
} from "../api/aws";
import { getCase } from "../api/cases";
import { CasePage } from "../pages/CasePage";
import type {
  AwsConnection,
  AwsDeployment,
  CaseRecord,
  RequirementKey,
} from "../types";
import { AwsDeploymentPanel } from "./AwsDeploymentPanel";

vi.mock("../api/aws", () => ({
  getAwsConnection: vi.fn(),
  getCaseDeployment: vi.fn(),
  createCaseDeployment: vi.fn(),
  deleteCaseDeployment: vi.fn(),
}));

vi.mock("../api/cases", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../api/cases")>()),
  getCase: vi.fn(),
}));

const connection: AwsConnection = {
  status: "connected",
  region: "us-east-1",
  account_id: "123456789012",
  principal_arn: "arn:aws:iam::123456789012:role/deployer",
  deployments_enabled: true,
  message: "Conexión verificada.",
};

function deployment(overrides: Partial<AwsDeployment> = {}): AwsDeployment {
  return {
    case_id: "case-a",
    architecture: "architecture_a",
    region: "us-east-1",
    stack_name: "seci-case-a",
    stack_id: null,
    status: "NOT_DEPLOYED",
    outputs: {},
    events: [],
    last_updated_at: null,
    ...overrides,
  };
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((done) => {
    resolve = done;
  });
  return { promise, resolve };
}

beforeEach(() => {
  vi.resetAllMocks();
  vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("Unexpected network request")));
  vi.mocked(getAwsConnection).mockResolvedValue(connection);
  vi.mocked(getCaseDeployment).mockResolvedValue(deployment());
});

afterEach(() => {
  cleanup();
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe("AWS deployment panel", () => {
  it("does not query a stack when the connection is disabled", async () => {
    vi.mocked(getAwsConnection).mockResolvedValue({
      ...connection,
      status: "disabled",
      account_id: null,
      principal_arn: null,
      deployments_enabled: false,
      message: "AWS no está configurado en este entorno.",
    });

    render(<AwsDeploymentPanel caseId="case-a" />);

    expect(await screen.findByText("Deshabilitada")).toBeVisible();
    expect(screen.getByText("AWS no está configurado en este entorno.")).toBeVisible();
    expect(screen.getByText("us-east-1")).toBeVisible();
    expect(getCaseDeployment).not.toHaveBeenCalled();
    expect(screen.getByRole("button", { name: "Desplegar" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Eliminar" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Refrescar estado AWS" })).toBeEnabled();
  });

  it("allows inspection but blocks operations when deployments are disabled", async () => {
    vi.mocked(getAwsConnection).mockResolvedValue({ ...connection, deployments_enabled: false });
    vi.mocked(getCaseDeployment).mockResolvedValue(deployment({ status: "CREATE_COMPLETE" }));

    render(<AwsDeploymentPanel caseId="case-a" />);

    expect(await screen.findByText("CREATE_COMPLETE")).toBeVisible();
    expect(screen.getByText(connection.account_id!)).toBeVisible();
    expect(screen.getByText("Las operaciones de despliegue están deshabilitadas.")).toBeVisible();
    expect(screen.getByRole("button", { name: "Desplegar" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Eliminar" })).toBeDisabled();
  });

  it("shows credential errors and retries the connection before querying a stack", async () => {
    vi.mocked(getAwsConnection).mockRejectedValueOnce(
      new Error("Las credenciales de AWS no son válidas. Revisa la configuración."),
    );
    const user = userEvent.setup();
    render(<AwsDeploymentPanel caseId="case-a" />);

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Las credenciales de AWS no son válidas",
    );
    expect(getCaseDeployment).not.toHaveBeenCalled();
    expect(screen.getByRole("button", { name: "Desplegar" })).toBeDisabled();

    await user.click(screen.getByRole("button", { name: "Refrescar estado AWS" }));

    expect(await screen.findByText("NOT_DEPLOYED")).toBeVisible();
    expect(getAwsConnection).toHaveBeenCalledTimes(2);
    expect(getCaseDeployment).toHaveBeenCalledWith("case-a", expect.any(AbortSignal));
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("requires cost confirmation, supports cancellation and sends only one create request", async () => {
    const pendingCreate = deferred<AwsDeployment>();
    vi.mocked(createCaseDeployment).mockReturnValue(pendingCreate.promise);
    const user = userEvent.setup();
    render(<AwsDeploymentPanel caseId="case-a" />);
    await screen.findByText("NOT_DEPLOYED");

    await user.click(screen.getByRole("button", { name: "Desplegar" }));
    let dialog = screen.getByRole("dialog", { name: "Confirmar costos de AWS" });
    expect(dialog).toHaveTextContent("pueden generar cargos");
    expect(dialog).toHaveTextContent(connection.account_id!);
    expect(within(dialog).getByRole("button", { name: "Cancelar" })).toHaveFocus();
    expect(createCaseDeployment).not.toHaveBeenCalled();

    await user.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Desplegar" })).toHaveFocus();
    expect(createCaseDeployment).not.toHaveBeenCalled();

    await user.click(screen.getByRole("button", { name: "Desplegar" }));
    dialog = screen.getByRole("dialog");
    await user.dblClick(
      within(dialog).getByRole("button", { name: "Confirmar costos y desplegar" }),
    );

    expect(createCaseDeployment).toHaveBeenCalledTimes(1);
    expect(createCaseDeployment).toHaveBeenCalledWith("case-a", expect.any(AbortSignal));
    expect(screen.getByRole("button", { name: "Desplegar" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Refrescar estado AWS" })).toBeDisabled();
    await act(async () => pendingCreate.resolve(deployment({ status: "CREATE_IN_PROGRESS" })));
    expect(screen.getByText("CREATE_IN_PROGRESS")).toBeVisible();
    expect(screen.getByRole("button", { name: "Desplegar" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Eliminar" })).toBeDisabled();
  });

  it("shows operation errors without accepting another create until the state is refreshed", async () => {
    vi.mocked(createCaseDeployment).mockRejectedValue(
      new Error("No tienes permisos para crear el stack."),
    );
    const user = userEvent.setup();
    render(<AwsDeploymentPanel caseId="case-a" />);
    await screen.findByText("NOT_DEPLOYED");

    await user.click(screen.getByRole("button", { name: "Desplegar" }));
    await user.click(screen.getByRole("button", { name: "Confirmar costos y desplegar" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "No tienes permisos para crear el stack.",
    );
    expect(screen.getByRole("button", { name: "Desplegar" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Refrescar estado AWS" })).toBeEnabled();
  });

  it("refreshes the state and displays a safe application link and dated events, newest first", async () => {
    vi.mocked(getCaseDeployment)
      .mockResolvedValueOnce(deployment())
      .mockResolvedValueOnce(
        deployment({
          status: "CREATE_COMPLETE",
          stack_id: "arn:aws:cloudformation:us-east-1:123456789012:stack/seci-case-a/1",
          outputs: { ApplicationUrl: "https://example.com/app" },
          last_updated_at: "2026-10-26T12:05:00Z",
          events: [
            {
              timestamp: "2026-10-26T12:00:00Z",
              logical_resource_id: "Server",
              resource_status: "CREATE_IN_PROGRESS",
              reason: null,
            },
            {
              timestamp: "2026-10-26T12:05:00Z",
              logical_resource_id: "Application",
              resource_status: "CREATE_COMPLETE",
              reason: "Recursos listos.",
            },
          ],
        }),
      );
    const user = userEvent.setup();
    render(<AwsDeploymentPanel caseId="case-a" />);
    await screen.findByText("NOT_DEPLOYED");

    const refresh = screen.getByRole("button", { name: "Refrescar estado AWS" });
    expect(refresh).toHaveAttribute("title", "Refrescar estado AWS");
    await user.click(refresh);

    const link = await screen.findByRole("link", { name: "Abrir aplicación" });
    expect(link).toHaveAttribute("href", "https://example.com/app");
    expect(link).toHaveAttribute("rel", "noopener noreferrer");
    const events = within(
      screen.getByRole("list", { name: "Últimos eventos del despliegue" }),
    ).getAllByRole("listitem");
    expect(events[0]).toHaveTextContent("Application");
    expect(events[0].querySelector("time")).toHaveAttribute("datetime", "2026-10-26T12:05:00Z");
    expect(events[0]).toHaveTextContent("Recursos listos.");
    expect(events[1]).toHaveTextContent("Server");
    expect(getAwsConnection).toHaveBeenCalledTimes(2);
    expect(getCaseDeployment).toHaveBeenCalledTimes(2);
  });

  it.each(["javascript:alert(1)", "data:text/html,test", "/relative-path"])(
    "does not render an unsafe ApplicationUrl: %s",
    async (ApplicationUrl) => {
      vi.mocked(getCaseDeployment).mockResolvedValue(
        deployment({ status: "CREATE_COMPLETE", outputs: { ApplicationUrl } }),
      );
      render(<AwsDeploymentPanel caseId="case-a" />);
      await screen.findByText("CREATE_COMPLETE");
      expect(screen.queryByRole("link", { name: "Abrir aplicación" })).not.toBeInTheDocument();
    },
  );

  it("requires destructive confirmation to delete a failed stack before redeployment", async () => {
    vi.mocked(getCaseDeployment)
      .mockResolvedValueOnce(deployment({ status: "ROLLBACK_COMPLETE" }))
      .mockResolvedValueOnce(deployment({ status: "NOT_DEPLOYED" }));
    vi.mocked(deleteCaseDeployment).mockResolvedValue(deployment({ status: "DELETE_IN_PROGRESS" }));
    const user = userEvent.setup();
    render(<AwsDeploymentPanel caseId="case-a" />);
    await screen.findByText("ROLLBACK_COMPLETE");
    expect(screen.getByRole("button", { name: "Desplegar" })).toBeDisabled();

    await user.click(screen.getByRole("button", { name: "Eliminar" }));
    let dialog = screen.getByRole("dialog", { name: "Confirmar eliminación" });
    expect(dialog).toHaveTextContent("puede destruir datos y no se puede deshacer");
    expect(dialog).toHaveTextContent("seci-case-a");
    expect(deleteCaseDeployment).not.toHaveBeenCalled();
    await user.click(within(dialog).getByRole("button", { name: "Cancelar" }));
    expect(deleteCaseDeployment).not.toHaveBeenCalled();

    await user.click(screen.getByRole("button", { name: "Eliminar" }));
    dialog = screen.getByRole("dialog");
    await user.dblClick(
      within(dialog).getByRole("button", { name: "Confirmar eliminación de recursos" }),
    );

    expect(await screen.findByText("DELETE_IN_PROGRESS")).toBeVisible();
    expect(deleteCaseDeployment).toHaveBeenCalledTimes(1);
    expect(screen.getByRole("button", { name: "Eliminar" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Desplegar" })).toBeDisabled();

    await user.click(screen.getByRole("button", { name: "Refrescar estado AWS" }));
    await screen.findByText("NOT_DEPLOYED");
    expect(screen.getByRole("button", { name: "Desplegar" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "Eliminar" })).toBeDisabled();
  });

  it("aborts and ignores a stale deployment response when the case changes", async () => {
    const oldDeployment = deferred<AwsDeployment>();
    vi.mocked(getCaseDeployment)
      .mockReturnValueOnce(oldDeployment.promise)
      .mockResolvedValueOnce(
        deployment({ case_id: "case-b", stack_name: "seci-case-b", status: "CREATE_COMPLETE" }),
      );
    const { rerender } = render(<AwsDeploymentPanel caseId="case-a" />);
    await waitFor(() => expect(getCaseDeployment).toHaveBeenCalledTimes(1));
    const oldSignal = vi.mocked(getCaseDeployment).mock.calls[0][1];

    rerender(<AwsDeploymentPanel caseId="case-b" />);
    expect(oldSignal?.aborted).toBe(true);
    expect(await screen.findByText("seci-case-b")).toBeVisible();

    await act(async () => oldDeployment.resolve(deployment({ status: "CREATE_FAILED" })));
    expect(screen.getByText("CREATE_COMPLETE")).toBeVisible();
    expect(screen.queryByText("CREATE_FAILED")).not.toBeInTheDocument();
    expect(screen.queryByText("seci-case-a")).not.toBeInTheDocument();
  });

  it("does not start a stack request if unmounted while checking the connection", async () => {
    const pendingConnection = deferred<AwsConnection>();
    vi.mocked(getAwsConnection).mockReturnValue(pendingConnection.promise);
    const { unmount } = render(<AwsDeploymentPanel caseId="case-a" />);
    const signal = vi.mocked(getAwsConnection).mock.calls[0][0];

    unmount();
    expect(signal?.aborted).toBe(true);
    await act(async () => pendingConnection.resolve(connection));
    expect(getCaseDeployment).not.toHaveBeenCalled();
  });
});

describe("AWS polling", () => {
  beforeEach(() => vi.useFakeTimers());

  it.each([
    "CREATE_IN_PROGRESS",
    "REVIEW_IN_PROGRESS",
    "ROLLBACK_IN_PROGRESS",
    "DELETE_IN_PROGRESS",
  ])("polls %s after ten seconds and stops when complete", async (status) => {
    vi.mocked(getCaseDeployment)
      .mockResolvedValueOnce(deployment({ status }))
      .mockResolvedValueOnce(deployment({ status: "CREATE_COMPLETE" }));
    await act(async () => render(<AwsDeploymentPanel caseId="case-a" />));
    expect(screen.getByText(status)).toBeVisible();
    expect(screen.getByRole("button", { name: "Desplegar" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Eliminar" })).toBeDisabled();

    await act(async () => vi.advanceTimersByTimeAsync(9_999));
    expect(getCaseDeployment).toHaveBeenCalledTimes(1);
    await act(async () => vi.advanceTimersByTimeAsync(1));
    expect(getCaseDeployment).toHaveBeenCalledTimes(2);
    expect(screen.getByText("CREATE_COMPLETE")).toBeVisible();
    await act(async () => vi.advanceTimersByTimeAsync(30_000));
    expect(getCaseDeployment).toHaveBeenCalledTimes(2);
  });

  it("clears its timer on unmount", async () => {
    vi.mocked(getCaseDeployment).mockResolvedValue(deployment({ status: "CREATE_IN_PROGRESS" }));
    let unmount!: () => void;
    await act(async () => {
      ({ unmount } = render(<AwsDeploymentPanel caseId="case-a" />));
    });

    unmount();
    await act(async () => vi.advanceTimersByTimeAsync(30_000));
    expect(getAwsConnection).toHaveBeenCalledTimes(1);
    expect(getCaseDeployment).toHaveBeenCalledTimes(1);
  });

  it.each([
    "NOT_DEPLOYED",
    "DELETE_COMPLETE",
    "CREATE_COMPLETE",
    "CREATE_FAILED",
    "DELETE_FAILED",
    "ROLLBACK_COMPLETE",
  ])("does not poll a terminal state: %s", async (status) => {
    vi.mocked(getCaseDeployment).mockResolvedValue(deployment({ status }));
    await act(async () => render(<AwsDeploymentPanel caseId="case-a" />));
    await act(async () => vi.advanceTimersByTimeAsync(30_000));
    expect(getCaseDeployment).toHaveBeenCalledTimes(1);
    expect(screen.getByRole("button", { name: "Desplegar" })).toHaveProperty(
      "disabled",
      !["NOT_DEPLOYED", "DELETE_COMPLETE"].includes(status),
    );
  });
});

describe("Case page integration", () => {
  it("loads AWS only when expanded and resets the disclosure when navigating between cases", async () => {
    const variables: RequirementKey[] = [
      "service_interruption_tolerance",
      "business_continuity_criticality",
      "information_sensitivity",
      "available_budget",
      "demand_pattern",
      "expected_load_volume",
    ];
    const unknown = { value: "unknown", status: "unknown" as const, evidence: [] };
    const scores = Object.fromEntries(variables.map((key) => [key, 0])) as Record<
      RequirementKey,
      number
    >;
    const record: CaseRecord = {
      id: "case-a",
      created_at: "2026-10-26T12:00:00Z",
      confirmed: {
        status: "confirmed",
        business_case: "Aplicación interna.",
        requirements: {
          service_interruption_tolerance: unknown,
          business_continuity_criticality: unknown,
          information_sensitivity: unknown,
          available_budget: unknown,
          demand_pattern: unknown,
          expected_load_volume: unknown,
        },
        priority_ranking: {
          never_stop_working: null,
          lowest_cost: null,
          fast_under_load: null,
          protect_information: null,
        },
        additional_context: {
          business_description: null,
          expected_users: null,
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
      },
      recommendation: {
        architecture: "architecture_a",
        runner_up: "architecture_b",
        totals: { architecture_a: 0, architecture_b: 0, architecture_c: 0 },
        margin: 0,
        trade_off: false,
        tie_broken: false,
        message: "Arquitectura recomendada.",
        weights: scores,
        weights_source: "equal",
        unknown_variables: variables,
        contributions: { architecture_a: scores, architecture_b: scores, architecture_c: scores },
      },
    };
    vi.mocked(getCase).mockImplementation(async (id) => ({ ...record, id }));
    const user = userEvent.setup();
    const { rerender } = render(<CasePage caseId="case-a" />);
    await screen.findByText("Caso case-a");
    expect(getAwsConnection).not.toHaveBeenCalled();

    await user.click(screen.getByText("Despliegue en AWS"));
    await screen.findByText("NOT_DEPLOYED");
    expect(getAwsConnection).toHaveBeenCalledTimes(1);

    rerender(<CasePage caseId="case-b" />);
    await screen.findByText("Caso case-b");
    expect(
      screen.queryByRole("heading", { name: "Estado del despliegue" }),
    ).not.toBeInTheDocument();
    expect(getAwsConnection).toHaveBeenCalledTimes(1);
    await user.click(screen.getByText("Despliegue en AWS"));
    await screen.findByText("NOT_DEPLOYED");
    expect(getCaseDeployment).toHaveBeenLastCalledWith("case-b", expect.any(AbortSignal));

    rerender(<CasePage caseId="case-a" />);
    await screen.findByText("Caso case-a");
    expect(
      screen.queryByRole("heading", { name: "Estado del despliegue" }),
    ).not.toBeInTheDocument();
    expect(getAwsConnection).toHaveBeenCalledTimes(2);
  });
});

describe("AWS API contract", () => {
  it("uses the agreed paths, cost confirmation JSON and a DELETE without a body", async () => {
    const api = await vi.importActual<typeof import("../api/aws")>("../api/aws");
    const fetchMock = vi
      .fn()
      .mockResolvedValue({ ok: true, status: 202, json: async () => deployment() });
    vi.stubGlobal("fetch", fetchMock);
    const signal = new AbortController().signal;

    await api.getAwsConnection(signal);
    await api.getCaseDeployment("case/a", signal);
    await api.createCaseDeployment("case/a", signal);
    await api.deleteCaseDeployment("case/a", signal);

    expect(fetchMock.mock.calls).toEqual([
      ["/api/aws/connection", { signal }],
      ["/api/cases/case%2Fa/deployment", { signal }],
      [
        "/api/cases/case%2Fa/deployment",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: '{"confirm_costs":true}',
          signal,
        },
      ],
      ["/api/cases/case%2Fa/deployment", { method: "DELETE", signal }],
    ]);
  });

  it("preserves friendly HTTP 503 detail and translates network errors", async () => {
    const api = await vi.importActual<typeof import("../api/aws")>("../api/aws");
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: false,
        status: 503,
        json: async () => ({ detail: "Configura credenciales válidas para AWS." }),
      })
      .mockRejectedValueOnce(new TypeError("Failed to fetch"))
      .mockResolvedValueOnce({
        ok: false,
        status: 502,
        json: async () => {
          throw new SyntaxError("Not JSON");
        },
      });
    vi.stubGlobal("fetch", fetchMock);

    await expect(api.getAwsConnection()).rejects.toThrow(
      "Configura credenciales válidas para AWS.",
    );
    await expect(api.getAwsConnection()).rejects.toThrow("No fue posible comunicarse con AWS.");
    await expect(api.getAwsConnection()).rejects.toThrow("No fue posible comunicarse con AWS.");
  });
});
