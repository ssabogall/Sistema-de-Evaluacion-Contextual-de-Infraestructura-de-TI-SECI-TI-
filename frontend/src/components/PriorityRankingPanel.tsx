import { ListOrdered, Quote } from "lucide-react";

import { priorityState } from "../priorityRanking";
import { PRIORITY_CONFIGS, PRIORITY_POSITION_LABELS, PRIORITY_STATE_LABELS } from "../requirements";
import type { PriorityRanking, PriorityStatement } from "../types";

interface PriorityRankingPanelProps {
  ranking: PriorityRanking;
  detectedRanking: PriorityRanking;
  evidence: string[];
  onAssign: (key: PriorityStatement, position: number | null) => void;
  onClear: () => void;
}

const STATE_HINTS = {
  empty: "Sin un orden definido, las cuatro prioridades pesan igual.",
  partial:
    "El orden está incompleto: mientras no asignes las cuatro posiciones, las prioridades pesarán igual.",
  edited: null,
  detected: null,
} as const;

export function PriorityRankingPanel({
  ranking,
  detectedRanking,
  evidence,
  onAssign,
  onClear,
}: PriorityRankingPanelProps) {
  const state = priorityState(ranking, detectedRanking);
  const hint = STATE_HINTS[state];

  return (
    <section className="priority-section" aria-labelledby="priority-title">
      <div className="priority-heading">
        <div>
          <h2 id="priority-title">
            <ListOrdered size={20} aria-hidden="true" />
            Prioridades del negocio
          </h2>
          <p>
            Ordena de la más a la menos importante para tu caso. Este orden decide cuánto pesa cada
            criterio en la recomendación.
          </p>
        </div>
        <span className={`priority-badge priority-${state}`} data-testid="priority-state">
          {PRIORITY_STATE_LABELS[state]}
        </span>
      </div>

      {state !== "empty" && evidence.length > 0 && (
        <div className="evidence-block priority-evidence">
          <div className="evidence-label">
            <Quote size={16} aria-hidden="true" />
            Evidencia del caso
          </div>
          <ul>
            {evidence.map((fragment) => (
              <li key={fragment}>“{fragment}”</li>
            ))}
          </ul>
        </div>
      )}

      <div className="priority-list">
        {PRIORITY_CONFIGS.map((config) => (
          <div className="priority-row" key={config.key}>
            <label htmlFor={`priority-${config.key}`}>{config.statement}</label>
            <select
              id={`priority-${config.key}`}
              value={ranking[config.key] === null ? "" : String(ranking[config.key])}
              onChange={(event) =>
                onAssign(config.key, event.target.value === "" ? null : Number(event.target.value))
              }
            >
              <option value="">Sin definir</option>
              {PRIORITY_POSITION_LABELS.map((label, index) => (
                <option key={label} value={index + 1}>
                  {label}
                </option>
              ))}
            </select>
          </div>
        ))}
      </div>

      <div className="priority-footer">
        {hint && <p className="priority-hint">{hint}</p>}
        {state !== "empty" && (
          <button className="link-button" type="button" onClick={onClear}>
            Quitar orden
          </button>
        )}
      </div>
    </section>
  );
}
