import { projectContext, scenarioLabel } from "../projectContext";
import type { ProjectContext } from "../types";

export function ProjectContextSummary({ context }: { context?: ProjectContext }) {
  const saved = projectContext(context);
  return (
    <section className="project-context" aria-label="Contexto de la plataforma">
      <h2>Contexto de la plataforma</h2>
      <p className="scenario-label">{scenarioLabel(saved.scenario)}</p>
      {saved.scenario === "existing" && (
        <>
          <h3>Arquitectura actual</h3>
          <p className="preserved-text">{saved.current_architecture}</p>
        </>
      )}
    </section>
  );
}
