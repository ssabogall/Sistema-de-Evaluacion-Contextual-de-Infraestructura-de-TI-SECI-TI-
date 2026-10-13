import { useMemo, useState, type FormEvent } from "react";
import {
  AlertCircle,
  ArrowLeft,
  CheckCircle2,
  LoaderCircle,
  Send,
  ShieldCheck,
  Sparkles,
} from "lucide-react";

import { analyzeBusinessCase } from "../api/businessCases";
import { createCase } from "../api/cases";
import { ErrorMessage } from "../components/ErrorMessage";
import { PriorityRankingPanel } from "../components/PriorityRankingPanel";
import { RequirementCard } from "../components/RequirementCard";
import { assignPriority, EMPTY_PRIORITY_RANKING } from "../priorityRanking";
import { ADDITIONAL_CONTEXT_LABELS, REQUIREMENT_CONFIGS } from "../requirements";
import { navigate } from "../router";
import type {
  BusinessCaseAnalysis,
  PriorityRanking,
  PriorityStatement,
  RequirementKey,
} from "../types";

const PLACEHOLDER =
  "Ejemplo: Necesitamos una plataforma de comercio electrónico para aproximadamente 3.000 usuarios. Durante campañas de marketing podemos tener aumentos repentinos de tráfico. Si el servicio deja de funcionar perdemos ventas y contamos inicialmente con un presupuesto limitado.";

export function AnalyzePage() {
  const [description, setDescription] = useState("");
  const [analysis, setAnalysis] = useState<BusinessCaseAnalysis | null>(null);
  // Orden que el modelo transcribió del texto; sirve para saber si el usuario lo editó.
  const [detectedRanking, setDetectedRanking] = useState<PriorityRanking>(EMPTY_PRIORITY_RANKING);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isConfirming, setIsConfirming] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const additionalContext = useMemo(() => {
    if (!analysis) return [];
    return Object.entries(analysis.additional_context).filter(
      ([, value]) => value !== null && value !== "",
    );
  }, [analysis]);

  async function handleAnalyze(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setIsAnalyzing(true);
    try {
      const result = await analyzeBusinessCase(description.trim());
      setDetectedRanking(result.priority_ranking);
      setAnalysis(result);
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "No fue posible analizar el caso en este momento. Intenta nuevamente.",
      );
    } finally {
      setIsAnalyzing(false);
    }
  }

  function updateRequirement(key: RequirementKey, value: string) {
    setAnalysis((current) => {
      if (!current) return current;
      const currentRequirement = current.requirements[key];
      const requirements = {
        ...current.requirements,
        [key]: {
          ...currentRequirement,
          value,
          status: value === "unknown" ? "unknown" : "detected",
          evidence: value === "unknown" ? [] : currentRequirement.evidence,
        },
      };
      const missingRequirements = REQUIREMENT_CONFIGS.filter(
        (config) => requirements[config.key].value === "unknown",
      ).map((config) => config.key);
      return { ...current, requirements, missing_requirements: missingRequirements };
    });
  }

  function updatePriority(key: PriorityStatement, position: number | null) {
    setAnalysis((current) =>
      current
        ? { ...current, priority_ranking: assignPriority(current.priority_ranking, key, position) }
        : current,
    );
  }

  function clearPriorities() {
    setAnalysis((current) =>
      current ? { ...current, priority_ranking: EMPTY_PRIORITY_RANKING } : current,
    );
  }

  async function handleConfirm() {
    if (!analysis) return;
    setError(null);
    setIsConfirming(true);
    try {
      const record = await createCase(analysis);
      navigate(`/casos/${record.id}`);
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "No fue posible guardar el caso en este momento. Intenta nuevamente.",
      );
    } finally {
      setIsConfirming(false);
    }
  }

  function returnToDescription() {
    setAnalysis(null);
    setError(null);
  }

  if (!analysis) {
    return (
      <section className="entry-section" aria-labelledby="entry-title">
        <div className="section-kicker">
          <Sparkles size={18} aria-hidden="true" />
          Análisis inicial
        </div>
        <h1 id="entry-title">Describe tu caso de negocio</h1>
        <p className="lead">
          Describe la aplicación o sistema que deseas soportar. Puedes incluir información sobre
          usuarios, comportamiento del tráfico, importancia de la disponibilidad, presupuesto y tipo
          de información manejada.
        </p>

        <form onSubmit={handleAnalyze} className="business-form">
          <label htmlFor="business-case">Caso de negocio</label>
          <textarea
            id="business-case"
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            placeholder={PLACEHOLDER}
            rows={10}
            maxLength={20_000}
            required
          />
          <div className="form-footer">
            <span>{description.length.toLocaleString("es-CO")} / 20.000</span>
            <button
              className="primary-button"
              type="submit"
              disabled={description.trim().length < 10 || isAnalyzing}
            >
              {isAnalyzing ? (
                <>
                  <LoaderCircle className="spin" size={18} aria-hidden="true" />
                  Analizando caso de negocio...
                </>
              ) : (
                <>
                  <Send size={18} aria-hidden="true" />
                  Analizar requisitos
                </>
              )}
            </button>
          </div>
        </form>

        {error && <ErrorMessage message={error} />}

        <div className="trust-note">
          <ShieldCheck size={20} aria-hidden="true" />
          <p>
            El análisis solo identifica requisitos. La arquitectura la elige un motor de reglas
            determinístico después de que confirmes el resultado.
          </p>
        </div>
      </section>
    );
  }

  return (
    <section className="review-section" aria-labelledby="review-title">
      <button className="back-button" type="button" onClick={returnToDescription}>
        <ArrowLeft size={17} aria-hidden="true" />
        Volver al caso
      </button>

      <div className="review-header">
        <div>
          <div className="section-kicker">Revisión humana</div>
          <h1 id="review-title">Requisitos identificados</h1>
          <p>
            Revisa cada resultado, completa los valores no definidos y resuelve los conflictos antes
            de confirmar.
          </p>
        </div>
        <div className="review-count">
          <strong>6</strong>
          <span>variables canónicas</span>
        </div>
      </div>

      {analysis.warnings.length > 0 && (
        <div className="warning-panel">
          <AlertCircle size={20} aria-hidden="true" />
          <div>
            {analysis.warnings.map((warning) => (
              <p key={warning}>{warning}</p>
            ))}
          </div>
        </div>
      )}

      <div className="requirements-grid">
        {REQUIREMENT_CONFIGS.map((config) => (
          <RequirementCard
            key={config.key}
            config={config}
            requirement={analysis.requirements[config.key]}
            onChange={(value) => updateRequirement(config.key, value)}
          />
        ))}
      </div>

      <PriorityRankingPanel
        ranking={analysis.priority_ranking}
        detectedRanking={detectedRanking}
        evidence={analysis.priority_ranking_evidence}
        onAssign={updatePriority}
        onClear={clearPriorities}
      />

      {additionalContext.length > 0 && (
        <section className="context-section" aria-labelledby="context-title">
          <h2 id="context-title">Contexto adicional identificado</h2>
          <dl>
            {additionalContext.map(([key, value]) => (
              <div key={key}>
                <dt>{ADDITIONAL_CONTEXT_LABELS[key] ?? key}</dt>
                <dd>{String(value)}</dd>
              </div>
            ))}
          </dl>
        </section>
      )}

      {error && <ErrorMessage message={error} />}

      <div className="confirmation-bar">
        <div>
          <strong>Confirmación obligatoria</strong>
          <span>Al confirmar se calcula la recomendación y se guarda el caso.</span>
        </div>
        <button
          className="primary-button confirm-button"
          type="button"
          onClick={handleConfirm}
          disabled={isConfirming}
        >
          {isConfirming ? (
            <>
              <LoaderCircle className="spin" size={18} aria-hidden="true" />
              Calculando...
            </>
          ) : (
            <>
              <CheckCircle2 size={18} aria-hidden="true" />
              Confirmar y ver recomendación
            </>
          )}
        </button>
      </div>
    </section>
  );
}
