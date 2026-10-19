import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

// Vitest no expone `afterEach` como global, así que Testing Library no desmonta solo
// los componentes: sin esto los tests se contaminan entre sí (elementos duplicados).
afterEach(() => {
  cleanup();
});
