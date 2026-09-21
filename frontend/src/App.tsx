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

import { analyzeBusinessCase, confirmBusinessCase } from "./api/businessCases";
import { RequirementCard } from "./components/RequirementCard";
import {
  ADDITIONAL_CONTEXT_LABELS,
  REQUIREMENT_CONFIGS,
} from "./requirements";
import type {
  BusinessCaseAnalysis,
  ConfirmedBusinessCase,
  RequirementKey,
} from "./types";

const PLACEHOLDER =
  "Ejemplo: Necesitamos una plataforma de comercio electrónico para aproximadamente 3.000 usuarios. Durante campañas de marketing podemos tener aumentos repentinos de tráfico. Si el servicio deja de funcionar perdemos ventas y contamos inicialmente con un presupuesto limitado.";

function App() {
  const [description, setDescription] = useState("");
  const [analysis, setAnalysis] = useState<BusinessCaseAnalysis | null>(null);
  const [confirmed, setConfirmed] = useState<ConfirmedBusinessCase | null>(null);
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
    setConfirmed(null);
    setIsAnalyzing(true);
    try {
      setAnalysis(await analyzeBusinessCase(description.trim()));
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
    setConfirmed(null);
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

  async function handleConfirm() {
    if (!analysis) return;
    setError(null);
    setIsConfirming(true);
    try {
      setConfirmed(await confirmBusinessCase(analysis));
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "No fue posible confirmar los requisitos en este momento.",
      );
    } finally {
      setIsConfirming(false);
    }
  }

  function returnToDescription() {
    setAnalysis(null);
    setConfirmed(null);
    setError(null);
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand-mark" aria-hidden="true">S</div>
        <div>
          <strong>SECI-TI</strong>
          <span>Evaluación contextual de infraestructura</span>
        </div>
        <div className="phase-indicator">PB-01 · Requisitos</div>
      </header>

      <main>
        {!analysis ? (
          <section className="entry-section" aria-labelledby="entry-title">
            <div className="section-kicker">
              <Sparkles size={18} aria-hidden="true" />
              Análisis inicial
            </div>
            <h1 id="entry-title">Describe tu caso de negocio</h1>
            <p className="lead">
              Describe la aplicación o sistema que deseas soportar. Puedes incluir
              información sobre usuarios, comportamiento del tráfico, importancia de la
              disponibilidad, presupuesto y tipo de información manejada.
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
                El análisis identifica requisitos. Ninguna arquitectura se selecciona en
                esta etapa y siempre tendrás que confirmar el resultado.
              </p>
            </div>
          </section>
        ) : (
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
                  Revisa cada resultado, completa los valores no definidos y resuelve los
                  conflictos antes de confirmar.
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
                  {analysis.warnings.map((warning) => <p key={warning}>{warning}</p>)}
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
                <span>Este objeto quedará listo para el futuro PB-02.</span>
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
                    Confirmando...
                  </>
                ) : (
                  <>
                    <CheckCircle2 size={18} aria-hidden="true" />
                    Confirmar requisitos
                  </>
                )}
              </button>
            </div>

            {confirmed && (
              <section className="success-panel" aria-live="polite">
                <div className="success-heading">
                  <CheckCircle2 size={24} aria-hidden="true" />
                  <div>
                    <h2>Requisitos confirmados correctamente.</h2>
                    <p>El resultado conserva las seis variables y el contexto adicional.</p>
                  </div>
                </div>
                <details>
                  <summary>Ver objeto confirmado</summary>
                  <pre>{JSON.stringify(confirmed, null, 2)}</pre>
                </details>
              </section>
            )}
          </section>
        )}
      </main>
    </div>
  );
}

function ErrorMessage({ message }: { message: string }) {
  return (
    <div className="error-message" role="alert">
      <AlertCircle size={20} aria-hidden="true" />
      <span>{message}</span>
    </div>
  );
}

export default App;
