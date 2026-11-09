import { afterEach, describe, expect, it, vi } from "vitest";

import { adviceFixture } from "../test/adviceFixture";
import { ADVICE_ERROR, generateAdvice } from "./advice";

afterEach(() => vi.unstubAllGlobals());

describe("Advice API contract", () => {
  it("encodes the case and sends explicit regenerate booleans with cancellation", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => adviceFixture() });
    vi.stubGlobal("fetch", fetchMock);
    const signal = new AbortController().signal;
    await expect(generateAdvice("case/a", false, signal)).resolves.toEqual(adviceFixture());
    await generateAdvice("case/a", true, signal);
    expect(fetchMock.mock.calls).toEqual([false, true].map((regenerate) => [
      "/api/cases/case%2Fa/advice",
      { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ regenerate }), signal },
    ]));
  });

  it("preserves the friendly HTTP 503 detail", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: false, status: 503, json: async () => ({ detail: "El proveedor IA no está disponible. Intenta más tarde." }),
    }));
    await expect(generateAdvice("case-a")).rejects.toThrow("El proveedor IA no está disponible. Intenta más tarde.");
  });

  it.each([
    { ok: false, status: 503, json: async () => ({ detail: [{ msg: "interno" }] }) },
    { ok: false, status: 503, json: async () => ({ detail: "  " }) },
    { ok: false, status: 503, json: async () => { throw new SyntaxError("proxy"); } },
    { ok: false, status: 500, json: async () => ({ detail: "Internal traceback" }) },
    { ok: true, json: async () => { throw new SyntaxError("invalid JSON"); } },
  ])("uses a friendly fallback for unusable responses %#", async (response) => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response));
    await expect(generateAdvice("case-a")).rejects.toThrow(ADVICE_ERROR);
  });

  it("translates network failures and preserves cancellation", async () => {
    const aborted = new DOMException("Cancelled", "AbortError");
    vi.stubGlobal("fetch", vi.fn().mockRejectedValueOnce(new TypeError("Failed to fetch")).mockRejectedValueOnce(aborted));
    await expect(generateAdvice("case-a")).rejects.toThrow(ADVICE_ERROR);
    const controller = new AbortController();
    controller.abort();
    await expect(generateAdvice("case-a", false, controller.signal)).rejects.toBe(aborted);
  });
});
