import type { RequirementKey } from "./types";

export interface RequirementOption {
  value: string;
  label: string;
}

export interface RequirementConfig {
  key: RequirementKey;
  title: string;
  description: string;
  options: RequirementOption[];
}

export const REQUIREMENT_CONFIGS: RequirementConfig[] = [
  {
    key: "service_interruption_tolerance",
    title: "Tolerancia a interrupción del servicio",
    description: "Cuánto tiempo podría estar fuera de servicio sin consecuencias inaceptables.",
    options: [
      { value: "high", label: "Se pueden tolerar interrupciones largas" },
      { value: "medium", label: "Solo se toleran interrupciones cortas" },
      { value: "low", label: "Prácticamente no puede interrumpirse" },
      { value: "unknown", label: "No definido" },
    ],
  },
  {
    key: "business_continuity_criticality",
    title: "Criticidad para el negocio",
    description: "Impacto que tendría una interrupción sobre la operación del negocio.",
    options: [
      { value: "low", label: "Impacto bajo" },
      { value: "medium", label: "Impacto moderado" },
      { value: "high", label: "Impacto alto" },
      { value: "unknown", label: "No definido" },
    ],
  },
  {
    key: "information_sensitivity",
    title: "Sensibilidad de la información",
    description: "Nivel inicial de sensibilidad de los datos que manejará el sistema.",
    options: [
      { value: "low", label: "Baja" },
      { value: "medium", label: "Media" },
      { value: "high", label: "Alta" },
      { value: "unknown", label: "No definido" },
    ],
  },
  {
    key: "available_budget",
    title: "Presupuesto disponible",
    description: "Nivel de presupuesto descrito, sin inferir categorías desde montos aislados.",
    options: [
      { value: "low", label: "Bajo" },
      { value: "medium", label: "Medio" },
      { value: "high", label: "Alto" },
      { value: "unknown", label: "No definido" },
    ],
  },
  {
    key: "demand_pattern",
    title: "Comportamiento del tráfico",
    description: "Forma en que cambia la demanda de usuarios o solicitudes en el tiempo.",
    options: [
      { value: "constant", label: "Estable" },
      { value: "predictable_peaks", label: "Picos predecibles" },
      { value: "unpredictable_peaks", label: "Picos impredecibles" },
      { value: "unknown", label: "No definido" },
    ],
  },
  {
    key: "expected_load_volume",
    title: "Volumen esperado de carga",
    description: "Magnitud general de la carga cuando el texto permite clasificarla.",
    options: [
      { value: "low", label: "Bajo" },
      { value: "medium", label: "Medio" },
      { value: "high", label: "Alto" },
      { value: "unknown", label: "No definido" },
    ],
  },
];

export const STATUS_LABELS = {
  detected: "Detectado",
  unknown: "No definido",
  conflict: "Conflicto",
} as const;

export const ADDITIONAL_CONTEXT_LABELS: Record<string, string> = {
  business_description: "Descripción del negocio",
  expected_users: "Usuarios esperados",
  concurrent_users: "Usuarios simultáneos",
  requests_per_second: "Solicitudes por segundo",
  expected_growth: "Crecimiento esperado",
  geographical_scope: "Alcance geográfico",
  explicit_availability_target: "Objetivo de disponibilidad",
  explicit_response_time_target: "Objetivo de tiempo de respuesta",
  budget_raw: "Monto de presupuesto",
  currency: "Moneda",
  budget_period: "Periodo del presupuesto",
};
