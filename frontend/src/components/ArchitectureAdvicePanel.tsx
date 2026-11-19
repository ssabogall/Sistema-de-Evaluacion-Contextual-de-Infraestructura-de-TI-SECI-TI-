import { useEffect, useRef, useState } from "react";
import { LoaderCircle, RefreshCw, Sparkles } from "lucide-react";

import { ADVICE_ERROR, generateAdvice } from "../api/advice";
import { formatDate } from "../format";
import type { AdviceCategory, AdviceLevel, SavedArchitectureAdvice } from "../types";
import { ErrorMessage } from "./ErrorMessage";

const CATEGORY_LABELS: Record<AdviceCategory, string> = {
  architecture: "Arquitectura",
  application: "Aplicación",
  data: "Datos",
  security: "Seguridad",
  reliability: "Fiabilidad",
  performance: "Rendimiento",
  operations: "Operación",
  cost: "Costo",
};
const LEVEL_LABELS: Record<AdviceLevel, string> = { high: "Alta", medium: "Media", low: "Baja" };
const EFFORT_LABELS: Record<AdviceLevel, string> = { high: "Alto", medium: "Medio", low: "Bajo" };
const PRIORITY_ORDER: Record<AdviceLevel, number> = { high: 0, medium: 1, low: 2 };

interface Props {
  caseId: string;
  savedAdvice?: SavedArchitectureAdvice | null;
}

// Un cambio de caso desmonta también las solicitudes y el filtro del informe anterior.
export function ArchitectureAdvicePanel(props: Props) {
  return <AdvicePanel key={props.caseId} {...props} />;
}

function AdvicePanel({ caseId, savedAdvice }: Props) {
  const [advice, setAdvice] = useState(savedAdvice ?? null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [category, setCategory] = useState<AdviceCategory | "all">("all");
  const request = useRef<AbortController | null>(null);

  useEffect(() => () => request.current?.abort(), []);

  async function generate() {
    if (request.current) return;
    const controller = new AbortController();
    request.current = controller;
    setIsLoading(true);
    setError(null);
    try {
      const result = await generateAdvice(caseId, advice !== null, controller.signal);
      if (!controller.signal.aborted) {
        setAdvice(result);
        setCategory("all");
      }
    } catch (requestError) {
      if (!controller.signal.aborted) {
        setError(requestError instanceof Error ? requestError.message : ADVICE_ERROR);
      }
    } finally {
      if (!controller.signal.aborted) {
        request.current = null;
        setIsLoading(false);
      }
    }
  }

  const content = advice?.content;
  const recommendations =
    content?.recommendations
      .filter((item) => category === "all" || item.category === category)
      .sort((a, b) =>
        PRIORITY_ORDER[a.priority] - PRIORITY_ORDER[b.priority] ||
        CATEGORY_LABELS[a.category].localeCompare(CATEGORY_LABELS[b.category], "es"),
      ) ?? [];
  const ActionIcon = isLoading ? LoaderCircle : advice ? RefreshCw : Sparkles;
  const actionLabel = isLoading
    ? "Generando..."
    : error
      ? "Reintentar recomendaciones"
      : advice
        ? "Regenerar recomendaciones"
        : "Generar recomendaciones";

  return (
    <section className="advice-section" aria-labelledby="advice-title">
      <div className="advice-heading">
        <h2 id="advice-title">
          <Sparkles size={20} aria-hidden="true" />
          Informe avanzado de arquitectura IA
        </h2>
      </div>
      <p className="advice-limits">
        Informe basado en la descripción confirmada; no es una auditoría. Las sugerencias
        requieren revisión y no se despliegan con la demo de AWS.
      </p>
      {!advice && !isLoading && !error && (
        <p className="advice-empty">
          Sin informe generado.
        </p>
      )}
      <div className="advice-actions">
        <button className="primary-button" type="button" disabled={isLoading} onClick={generate}>
          <ActionIcon className={isLoading ? "spin" : undefined} size={18} aria-hidden="true" />
          {actionLabel}
        </button>
        {advice && <span>Regenerar sustituye el informe guardado cuando el nuevo esté listo.</span>}
      </div>
      <div role="status" aria-live="polite">
        {isLoading && (
          <p className="advice-progress">
            Generando recomendaciones...
          </p>
        )}
      </div>
      {error && <ErrorMessage message={error} />}
      {error && advice && <p className="field-hint">Se conserva el informe anterior.</p>}

      {advice && content && (
        <div className="advice-content" aria-busy={isLoading}>
          <p className="advice-meta">
            Generado el <time dateTime={advice.generated_at}>{formatDate(advice.generated_at)}</time>
            {" · "}{advice.provider}{advice.model ? ` · ${advice.model}` : ""}
          </p>
          <h3>Resumen</h3>
          <p className="preserved-text">{content.summary}</p>
          {content.current_architecture_assessment && (
            <>
              <h3>Evaluación de la arquitectura actual</h3>
              <p className="preserved-text">{content.current_architecture_assessment}</p>
            </>
          )}
          <div className="advice-recommendations-heading">
            <h3>Recomendaciones por prioridad</h3>
            <div className="select-label">
              <label htmlFor="advice-category">Filtrar por categoría</label>
              <select
                id="advice-category"
                value={category}
                onChange={(event) => setCategory(event.target.value as AdviceCategory | "all")}
              >
                <option value="all">Todas las categorías</option>
                {Object.entries(CATEGORY_LABELS).map(([key, label]) => (
                  <option key={key} value={key}>{label}</option>
                ))}
              </select>
            </div>
          </div>
          {recommendations.length === 0 && <p>No hay recomendaciones en esta categoría.</p>}
          <ol className="advice-list" aria-label="Recomendaciones por prioridad">
            {recommendations.map((item, index) => (
              <li key={`${item.title}-${index}`}>
                <div className="advice-tags">
                  <span className={`advice-priority is-${item.priority}`}>
                    Prioridad {LEVEL_LABELS[item.priority].toLowerCase()}
                  </span>
                  <span>{CATEGORY_LABELS[item.category]}</span>
                  <span>Esfuerzo: {EFFORT_LABELS[item.effort].toLowerCase()}</span>
                </div>
                <h4>{item.title}</h4>
                <p className="preserved-text">{item.recommendation}</p>
                <dl className="advice-details">
                  <div>
                    <dt>Justificación</dt>
                    <dd>{item.rationale}</dd>
                  </div>
                  <div>
                    <dt>Beneficio esperado</dt>
                    <dd>{item.expected_benefit}</dd>
                  </div>
                  <div>
                    <dt>Costos y límites</dt>
                    <dd>{item.tradeoffs}</dd>
                  </div>
                </dl>
                {item.evidence.length > 0 && (
                  <details>
                    <summary>Evidencia de la descripción</summary>
                    <ul>
                      {item.evidence.map((text, i) => <li key={i}>{text}</li>)}
                    </ul>
                  </details>
                )}
              </li>
            ))}
          </ol>

          <h3>Alternativas de arquitectura</h3>
          <ul className="advice-list" aria-label="Alternativas de arquitectura">
            {content.alternatives.map((item, index) => (
              <li key={`${item.name}-${index}`}>
                <h4>{item.name}</h4>
                <p className="preserved-text">{item.description}</p>
                <dl className="advice-details">
                  <div>
                    <dt>Cuándo conviene</dt>
                    <dd>{item.suitable_when}</dd>
                  </div>
                  <div>
                    <dt>Costos y límites</dt>
                    <dd>{item.tradeoffs}</dd>
                  </div>
                </dl>
                <h5>Pasos de migración o adopción</h5>
                <ol>
                  {item.migration_steps.map((step, i) => <li key={i}>{step}</li>)}
                </ol>
              </li>
            ))}
          </ul>
          <h3>Próximos pasos</h3>
          <ol>
            {content.next_steps.map((step, i) => <li key={i}>{step}</li>)}
          </ol>
          {content.assumptions.length > 0 && (
            <>
              <h3>Supuestos</h3>
              <ul>
                {content.assumptions.map((text, i) => <li key={i}>{text}</li>)}
              </ul>
            </>
          )}
          {content.open_questions.length > 0 && (
            <>
              <h3>Preguntas pendientes</h3>
              <ul>
                {content.open_questions.map((text, i) => <li key={i}>{text}</li>)}
              </ul>
            </>
          )}
        </div>
      )}
    </section>
  );
}
