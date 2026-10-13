export type RequirementStatus = "detected" | "unknown" | "conflict";

export interface RequirementItem {
  value: string;
  status: RequirementStatus;
  evidence: string[];
}

export type RequirementKey =
  | "service_interruption_tolerance"
  | "business_continuity_criticality"
  | "information_sensitivity"
  | "available_budget"
  | "demand_pattern"
  | "expected_load_volume";

export type Requirements = Record<RequirementKey, RequirementItem>;

export interface AdditionalContext {
  business_description: string | null;
  expected_users: number | null;
  concurrent_users: number | null;
  requests_per_second: number | null;
  expected_growth: string | null;
  geographical_scope: string | null;
  explicit_availability_target: string | null;
  explicit_response_time_target: string | null;
  budget_raw: number | null;
  currency: string | null;
  budget_period: string | null;
}

export type PriorityStatement =
  "never_stop_working" | "lowest_cost" | "fast_under_load" | "protect_information";

/** Posición de cada prioridad: 1 = la más importante, 4 = la menos importante, null = sin definir. */
export type PriorityRanking = Record<PriorityStatement, number | null>;

export interface BusinessCaseAnalysis {
  business_case: string;
  requirements: Requirements;
  additional_context: AdditionalContext;
  missing_requirements: RequirementKey[];
  priority_ranking: PriorityRanking;
  priority_ranking_evidence: string[];
  warnings: string[];
  requires_user_confirmation: true;
}

export interface ConfirmedBusinessCase {
  status: "confirmed";
  business_case: string;
  requirements: Requirements;
  additional_context: AdditionalContext;
  priority_ranking: PriorityRanking;
}

export type ArchitectureId = "architecture_a" | "architecture_b" | "architecture_c";

export type WeightsSource = "ranking" | "equal";

export interface Recommendation {
  architecture: ArchitectureId;
  runner_up: ArchitectureId;
  totals: Record<ArchitectureId, number>;
  margin: number;
  trade_off: boolean;
  tie_broken: boolean;
  message: string;
  weights: Record<RequirementKey, number>;
  weights_source: WeightsSource;
  unknown_variables: RequirementKey[];
  contributions: Record<ArchitectureId, Record<RequirementKey, number>>;
}

export interface CaseRecord {
  id: string;
  created_at: string;
  confirmed: ConfirmedBusinessCase;
  recommendation: Recommendation;
}

export interface CaseSummary {
  id: string;
  created_at: string;
  business_case_excerpt: string;
  architecture: ArchitectureId;
  trade_off: boolean;
}
