import type { ProjectContext, ProjectScenario } from "./types";

export function projectContext(context?: ProjectContext): ProjectContext {
  return context?.scenario === "existing"
    ? { scenario: "existing", current_architecture: context.current_architecture.trim() }
    : { scenario: "new", current_architecture: null };
}

export function scenarioLabel(scenario: ProjectScenario = "new"): string {
  return scenario === "existing" ? "Plataforma existente" : "Plataforma nueva";
}
