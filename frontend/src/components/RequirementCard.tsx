import { AlertTriangle, Quote } from "lucide-react";

import { STATUS_LABELS, type RequirementConfig } from "../requirements";
import type { RequirementItem } from "../types";

interface RequirementCardProps {
  config: RequirementConfig;
  requirement: RequirementItem;
  onChange: (value: string) => void;
}

export function RequirementCard({ config, requirement, onChange }: RequirementCardProps) {
  const selectedLabel =
    config.options.find((option) => option.value === requirement.value)?.label ?? "No definido";

  return (
    <article className={`requirement-card status-${requirement.status}`}>
      <div className="requirement-heading">
        <div>
          <h2>{config.title}</h2>
          <p>{config.description}</p>
        </div>
        <span className="status-badge">
          {requirement.status === "conflict" && <AlertTriangle size={15} aria-hidden="true" />}
          {STATUS_LABELS[requirement.status]}
        </span>
      </div>

      <div className="detected-value">
        <span>Resultado actual</span>
        <strong>{selectedLabel}</strong>
      </div>

      <div className="evidence-block">
        <div className="evidence-label">
          <Quote size={16} aria-hidden="true" />
          Evidencia del caso
        </div>
        {requirement.evidence.length > 0 ? (
          <ul>
            {requirement.evidence.map((fragment) => (
              <li key={fragment}>“{fragment}”</li>
            ))}
          </ul>
        ) : (
          <p className="empty-evidence">No se encontró evidencia suficiente.</p>
        )}
      </div>

      <label className="select-label" htmlFor={config.key}>
        Revisar valor
        <select
          id={config.key}
          value={requirement.value}
          onChange={(event) => onChange(event.target.value)}
        >
          {config.options.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </label>
    </article>
  );
}
