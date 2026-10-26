import { useEffect, useState } from "react";
import { ArrowLeft, Check, Link2, Quote, Scale } from "lucide-react";

import { CaseNotFoundError, getCase } from "../api/cases";
import { ARCHITECTURE_IDS, architectureTitle } from "../architectures";
import { AwsDeploymentPanel } from "../components/AwsDeploymentPanel";
import { ErrorMessage } from "../components/ErrorMessage";
import { Link } from "../components/Link";
import { formatDate, formatPercent, formatScore } from "../format";
import { PRIORITY_CONFIGS, REQUIREMENT_CONFIGS } from "../requirements";
import type { CaseRecord } from "../types";

type LoadResult = { id: string; record: CaseRecord } | { id: string; error: Error };

// Escala real de la tabla de compatibilidad: -2 (peor) a +3 (mejor); los pesos suman 1.
const SCORE_MIN = -2;
const SCORE_MAX = 3;

function barWidth(total: number): string {
  const ratio = (total - SCORE_MIN) / (SCORE_MAX - SCORE_MIN);
  return `${Math.min(100, Math.max(0, ratio * 100))}%`;
}

function CaseDeployment({ caseId }: { caseId: string }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <details
      className="aws-deployment-section"
      onToggle={(event) => setExpanded(event.currentTarget.open)}
    >
      <summary>Despliegue en AWS</summary>
      {expanded && <AwsDeploymentPanel caseId={caseId} />}
    </details>
  );
}

export function CasePage({ caseId }: { caseId: string }) {
  const [result, setResult] = useState<LoadResult | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    let cancelled = false;
    getCase(caseId).then(
      (record) => {
        if (!cancelled) setResult({ id: caseId, record });
      },
      (error: Error) => {
        if (!cancelled) setResult({ id: caseId, error });
      },
    );
    return () => {
      cancelled = true;
    };
  }, [caseId]);

  async function copyLink() {
    try {
      await navigator.clipboard.writeText(window.location.href);
      setCopied(true);
    } catch {
      setCopied(false);
    }
  }

  const current = result?.id === caseId ? result : null;

  if (!current) {
    return (
      <section className="case-section" aria-busy="true">
        <p className="lead">Cargando el caso...</p>
      </section>
    );
  }

  if ("error" in current) {
    return (
      <section className="case-section">
        <Link className="back-button" to="/casos">
          <ArrowLeft size={17} aria-hidden="true" />
          Casos guardados
        </Link>
        <h1>{current.error instanceof CaseNotFoundError ? "Caso no encontrado" : "Error"}</h1>
        <ErrorMessage message={current.error.message} />
      </section>
    );
  }

  const { record } = current;
  const { recommendation, confirmed } = record;
  const winnerLabel = architectureTitle(recommendation.architecture);

  return (
    <section className="case-section" aria-labelledby="case-title">
      <Link className="back-button" to="/casos">
        <ArrowLeft size={17} aria-hidden="true" />
        Casos guardados
      </Link>

      <div className="section-kicker">
        <Scale size={18} aria-hidden="true" />
        Recomendación del motor de reglas
      </div>
      <h1 id="case-title">{winnerLabel}</h1>
      <p className="lead">{recommendation.message}</p>

      <div className="case-meta">
        <span>Caso {record.id.slice(0, 8)}</span>
        <span>{formatDate(record.created_at)}</span>
        {recommendation.trade_off && <span className="case-badge">Resultado ajustado</span>}
        <button className="link-button" type="button" onClick={copyLink}>
          {copied ? <Check size={15} aria-hidden="true" /> : <Link2 size={15} aria-hidden="true" />}
          {copied ? "Enlace copiado" : "Copiar enlace"}
        </button>
      </div>

      <section className="score-panel" aria-labelledby="scores-title">
        <h2 id="scores-title">Puntaje por arquitectura</h2>
        {ARCHITECTURE_IDS.map((id) => (
          <div
            className={`score-row${id === recommendation.architecture ? " is-winner" : ""}`}
            key={id}
          >
            <span className="score-name">{architectureTitle(id)}</span>
            <div
              className="score-track"
              role="img"
              aria-label={`${architectureTitle(id)}: ${formatScore(recommendation.totals[id])}`}
            >
              <div className="score-bar" style={{ width: barWidth(recommendation.totals[id]) }} />
            </div>
            <strong>{formatScore(recommendation.totals[id])}</strong>
          </div>
        ))}
        <p className="score-note">
          Escala de {SCORE_MIN} a +{SCORE_MAX}. El orden de prioridades solo cambia los pesos; el
          cálculo es siempre el mismo.
        </p>
      </section>

      <section className="weights-panel" aria-labelledby="weights-title">
        <h2 id="weights-title">Pesos usados</h2>
        <p>
          {recommendation.weights_source === "ranking"
            ? "Calculados a partir del orden de prioridades que confirmaste."
            : "Pesos iguales: no se definió un orden de prioridades completo."}
        </p>
        {confirmed.priority_ranking && recommendation.weights_source === "ranking" && (
          <ol className="priority-summary">
            {PRIORITY_CONFIGS.map((config) => ({
              config,
              position: confirmed.priority_ranking[config.key],
            }))
              .sort((a, b) => (a.position ?? 99) - (b.position ?? 99))
              .map(({ config }) => (
                <li key={config.key}>{config.statement}</li>
              ))}
          </ol>
        )}
      </section>

      <details className="calculation">
        <summary>Ver cálculo por variable</summary>
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th scope="col">Variable</th>
                <th scope="col">Valor confirmado</th>
                <th scope="col">Peso</th>
                {ARCHITECTURE_IDS.map((id) => (
                  <th scope="col" key={id}>
                    {id.slice(-1).toUpperCase()}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {REQUIREMENT_CONFIGS.map((config) => {
                const value = confirmed.requirements[config.key].value;
                const label =
                  config.options.find((option) => option.value === value)?.label ?? value;
                const isUnknown = recommendation.unknown_variables.includes(config.key);
                return (
                  <tr key={config.key}>
                    <th scope="row">{config.title}</th>
                    <td>{isUnknown ? `${label} (valor neutro)` : label}</td>
                    <td>{formatPercent(recommendation.weights[config.key])}</td>
                    {ARCHITECTURE_IDS.map((id) => (
                      <td key={id}>{formatScore(recommendation.contributions[id][config.key])}</td>
                    ))}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </details>

      <CaseDeployment key={record.id} caseId={record.id} />

      <section className="original-case" aria-labelledby="original-title">
        <h2 id="original-title">
          <Quote size={18} aria-hidden="true" />
          Caso original
        </h2>
        <blockquote>{confirmed.business_case}</blockquote>
      </section>

      <Link className="primary-button" to="/">
        Analizar otro caso
      </Link>
    </section>
  );
}
