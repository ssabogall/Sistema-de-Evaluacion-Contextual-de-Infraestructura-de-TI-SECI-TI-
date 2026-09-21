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

export interface BusinessCaseAnalysis {
  business_case: string;
  requirements: Requirements;
  additional_context: AdditionalContext;
  missing_requirements: RequirementKey[];
  warnings: string[];
  requires_user_confirmation: true;
}

export interface ConfirmedBusinessCase {
  status: "confirmed";
  business_case: string;
  requirements: Requirements;
  additional_context: AdditionalContext;
}
