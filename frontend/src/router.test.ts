import { describe, expect, it } from "vitest";

import { isCasesListPath, matchCasePath } from "./router";

describe("matchCasePath", () => {
  it("extracts the case id", () => {
    expect(matchCasePath("/casos/abc123")).toBe("abc123");
    expect(matchCasePath("/casos/abc123/")).toBe("abc123");
  });

  it("ignores other paths", () => {
    expect(matchCasePath("/")).toBeNull();
    expect(matchCasePath("/casos")).toBeNull();
    expect(matchCasePath("/casos/a/b")).toBeNull();
  });
});

describe("isCasesListPath", () => {
  it("only matches the list path", () => {
    expect(isCasesListPath("/casos")).toBe(true);
    expect(isCasesListPath("/casos/")).toBe(true);
    expect(isCasesListPath("/casos/abc")).toBe(false);
    expect(isCasesListPath("/")).toBe(false);
  });
});
