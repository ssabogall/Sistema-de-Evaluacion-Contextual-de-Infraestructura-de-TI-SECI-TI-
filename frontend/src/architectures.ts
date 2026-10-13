import type { ArchitectureId } from "./types";

export interface ArchitectureInfo {
  letter: string;
  name: string;
  summary: string;
}

export const ARCHITECTURE_IDS: ArchitectureId[] = [
  "architecture_a",
  "architecture_b",
  "architecture_c",
];

export const ARCHITECTURES: Record<ArchitectureId, ArchitectureInfo> = {
  architecture_a: {
    letter: "A",
    name: "Básica",
    summary: "Infraestructura sencilla para necesidades moderadas de capacidad y disponibilidad.",
  },
  architecture_b: {
    letter: "B",
    name: "Escalable",
    summary: "Pensada para adaptarse a cambios de demanda.",
  },
  architecture_c: {
    letter: "C",
    name: "Resiliente",
    summary: "Pensada para sostener el servicio cuando algo falla.",
  },
};

export function architectureTitle(id: ArchitectureId): string {
  const info = ARCHITECTURES[id];
  return `Arquitectura ${info.letter} · ${info.name}`;
}
