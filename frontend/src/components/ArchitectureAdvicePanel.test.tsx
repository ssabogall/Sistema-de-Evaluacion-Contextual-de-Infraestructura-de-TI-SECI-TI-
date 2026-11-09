import { act, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { generateAdvice } from "../api/advice";
import { adviceFixture } from "../test/adviceFixture";
import type { AdviceCategory, SavedArchitectureAdvice } from "../types";
import { ArchitectureAdvicePanel } from "./ArchitectureAdvicePanel";

vi.mock("../api/advice", async (importOriginal) => ({
  ...await importOriginal<typeof import("../api/advice")>(),
  generateAdvice: vi.fn(),
}));

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (error: Error) => void;
  const promise = new Promise<T>((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
}

beforeEach(() => vi.mocked(generateAdvice).mockReset());

describe("Architecture advice", () => {
  it("stays empty without generating automatically and shows the report limits", () => {
    render(<ArchitectureAdvicePanel caseId="case-a" />);
    expect(screen.getByText("Sin informe generado.")).toBeVisible();
    expect(screen.getByText(/no es una auditoría/)).toHaveTextContent(/no se despliegan con la demo de AWS/);
    expect(screen.getByRole("button", { name: "Generar recomendaciones" })).toBeEnabled();
    expect(generateAdvice).not.toHaveBeenCalled();
  });

  it("renders persisted content in priority order, filters categories and shows alternatives and limits", async () => {
    const saved = adviceFixture();
    const user = userEvent.setup();
    render(<ArchitectureAdvicePanel caseId="case-a" savedAdvice={saved} />);
    expect(generateAdvice).not.toHaveBeenCalled();
    expect(screen.getByText(saved.content.summary)).toBeVisible();
    expect(screen.getByText(saved.content.current_architecture_assessment!)).toBeVisible();
    expect(screen.getByText(/Proveedor de prueba · modelo-prueba/)).toBeVisible();
    expect(screen.getByText(/Generado el/).querySelector("time")).toHaveAttribute("datetime", saved.generated_at);
    const recommendations = within(screen.getByRole("list", { name: "Recomendaciones por prioridad" })).getAllByRole("listitem");
    expect(recommendations[0]).toHaveTextContent("Aislar las notificaciones");
    expect(recommendations[0]).toHaveTextContent("Prioridad alta");
    expect(recommendations[0]).toHaveTextContent("Esfuerzo: medio");
    expect(recommendations[0]).toHaveTextContent("Entrega eventual y gestión de reintentos.");
    expect(recommendations.at(-1)).toHaveTextContent("Revisar el gasto");
    await user.click(screen.getByText("Evidencia de la descripción"));
    expect(screen.getByText(saved.content.recommendations[1].evidence[0])).toBeVisible();

    for (const text of [saved.content.alternatives[0].name, saved.content.alternatives[0].suitable_when,
      saved.content.alternatives[0].tradeoffs, ...saved.content.alternatives[0].migration_steps,
      ...saved.content.next_steps, ...saved.content.assumptions, ...saved.content.open_questions]) {
      expect(screen.getByText(text)).toBeVisible();
    }
    await user.selectOptions(screen.getByLabelText("Filtrar por categoría"), "cost");
    expect(screen.queryByText("Aislar las notificaciones")).not.toBeInTheDocument();
    expect(screen.getByText("Revisar el gasto")).toBeVisible();
    await user.selectOptions(screen.getByLabelText("Filtrar por categoría"), "security");
    expect(screen.getByText("No hay recomendaciones en esta categoría.")).toBeVisible();
    expect(generateAdvice).not.toHaveBeenCalled();
  });

  it("generates once on double click and regenerates explicitly while retaining the previous report", async () => {
    const first = deferred<SavedArchitectureAdvice>();
    const second = deferred<SavedArchitectureAdvice>();
    vi.mocked(generateAdvice).mockReturnValueOnce(first.promise).mockReturnValueOnce(second.promise);
    const user = userEvent.setup();
    render(<ArchitectureAdvicePanel caseId="case-a" />);
    await user.dblClick(screen.getByRole("button", { name: "Generar recomendaciones" }));
    expect(generateAdvice).toHaveBeenCalledTimes(1);
    expect(generateAdvice).toHaveBeenLastCalledWith("case-a", false, expect.any(AbortSignal));
    expect(screen.getByRole("button", { name: "Generando..." })).toBeDisabled();
    expect(screen.getByRole("status")).toHaveTextContent("Generando recomendaciones");
    await act(async () => first.resolve(adviceFixture("Primer informe")));
    await user.click(screen.getByRole("button", { name: "Regenerar recomendaciones" }));
    expect(generateAdvice).toHaveBeenLastCalledWith("case-a", true, expect.any(AbortSignal));
    expect(screen.getByText("Primer informe")).toBeVisible();
    await act(async () => second.resolve(adviceFixture("Informe actualizado")));
    expect(screen.getByText("Informe actualizado")).toBeVisible();
    expect(screen.queryByText("Primer informe")).not.toBeInTheDocument();
  });

  it("retries the first generation with regenerate false", async () => {
    vi.mocked(generateAdvice).mockRejectedValueOnce(new Error("El proveedor no está disponible."))
      .mockResolvedValueOnce(adviceFixture());
    const user = userEvent.setup();
    render(<ArchitectureAdvicePanel caseId="case-a" />);
    await user.click(screen.getByRole("button", { name: "Generar recomendaciones" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("El proveedor no está disponible.");
    await user.click(screen.getByRole("button", { name: "Reintentar recomendaciones" }));
    expect(await screen.findByText(adviceFixture().content.summary)).toBeVisible();
    expect(generateAdvice).toHaveBeenLastCalledWith("case-a", false, expect.any(AbortSignal));
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("keeps a saved report after a regeneration error and retries with regenerate true", async () => {
    vi.mocked(generateAdvice).mockRejectedValueOnce(new Error("La IA no está disponible."))
      .mockResolvedValueOnce(adviceFixture("Nuevo informe"));
    const user = userEvent.setup();
    render(<ArchitectureAdvicePanel caseId="case-a" savedAdvice={adviceFixture("Informe guardado")} />);
    await user.click(screen.getByRole("button", { name: "Regenerar recomendaciones" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("La IA no está disponible.");
    expect(screen.getByText("Informe guardado")).toBeVisible();
    expect(screen.getByText("Se conserva el informe anterior.")).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Reintentar recomendaciones" }));
    expect(await screen.findByText("Nuevo informe")).toBeVisible();
    expect(generateAdvice).toHaveBeenLastCalledWith("case-a", true, expect.any(AbortSignal));
  });

  it.each([false, true])("aborts and ignores a stale response after changing case (failure: %s)", async (failure) => {
    const old = deferred<SavedArchitectureAdvice>();
    vi.mocked(generateAdvice).mockReturnValueOnce(old.promise);
    const user = userEvent.setup();
    const { rerender } = render(<ArchitectureAdvicePanel caseId="case-a" />);
    await user.click(screen.getByRole("button", { name: "Generar recomendaciones" }));
    const signal = vi.mocked(generateAdvice).mock.calls[0][2];
    rerender(<ArchitectureAdvicePanel caseId="case-b" savedAdvice={adviceFixture("Informe B")} />);
    expect(signal?.aborted).toBe(true);
    await act(async () => {
      if (failure) old.reject(new Error("Error del caso anterior"));
      else old.resolve(adviceFixture("Informe A tardío"));
    });
    expect(screen.getByText("Informe B")).toBeVisible();
    expect(screen.queryByText("Informe A tardío")).not.toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(generateAdvice).toHaveBeenCalledTimes(1);
  });

  it.each([false, true])("aborts an in-flight request on unmount (failure: %s)", async (failure) => {
    const pending = deferred<SavedArchitectureAdvice>();
    vi.mocked(generateAdvice).mockReturnValueOnce(pending.promise);
    const user = userEvent.setup();
    const { unmount } = render(<ArchitectureAdvicePanel caseId="case-a" />);
    await user.click(screen.getByRole("button", { name: "Generar recomendaciones" }));
    const signal = vi.mocked(generateAdvice).mock.calls[0][2];
    unmount();
    expect(signal?.aborted).toBe(true);
    await act(async () => {
      if (failure) pending.reject(new Error("Error tardío"));
      else pending.resolve(adviceFixture());
    });
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(generateAdvice).toHaveBeenCalledTimes(1);
  });

  it("allows a new platform report without an assessment or model", () => {
    const saved = adviceFixture();
    saved.model = null;
    saved.content.current_architecture_assessment = null;
    saved.content.assumptions = [];
    saved.content.open_questions = [];
    render(<ArchitectureAdvicePanel caseId="case-a" savedAdvice={saved} />);
    expect(screen.queryByRole("heading", { name: "Evaluación de la arquitectura actual" })).not.toBeInTheDocument();
    expect(screen.queryByText("null")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Regenerar recomendaciones" })).toBeEnabled();
  });

  it("renders and filters all eight backend categories", async () => {
    const categories: [AdviceCategory, string][] = [
      ["architecture", "Arquitectura"], ["application", "Aplicación"], ["data", "Datos"],
      ["security", "Seguridad"], ["reliability", "Fiabilidad"], ["performance", "Rendimiento"],
      ["operations", "Operación"], ["cost", "Costo"],
    ];
    const saved = adviceFixture();
    saved.content.recommendations = categories.map(([category, title]) => ({
      ...saved.content.recommendations[0], category, title: `Mejora de ${title}`,
    }));
    const user = userEvent.setup();
    render(<ArchitectureAdvicePanel caseId="case-a" savedAdvice={saved} />);
    for (const [category, label] of categories) {
      await user.selectOptions(screen.getByLabelText("Filtrar por categoría"), category);
      const list = screen.getByRole("list", { name: "Recomendaciones por prioridad" });
      expect(within(list).getAllByRole("listitem")).toHaveLength(1);
      expect(within(list).getByText(label)).toBeVisible();
      expect(within(list).getByRole("heading", { name: `Mejora de ${label}` })).toBeVisible();
    }
  });
});
