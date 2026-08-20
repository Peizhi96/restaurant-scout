export type ListingStatus =
  | "NEW"
  | "REVIEWING"
  | "CONTACT_BROKER"
  | "PASSED"
  | "DUE_DILIGENCE"
  | "REJECTED"
  | "SOLD"
  | "OFF_MARKET";

export type MarketStatus = "UNKNOWN" | "ACTIVE" | "PENDING" | "SOLD" | "OFF_MARKET";

export interface Listing {
  id: string;
  title: string;
  business_name: string | null;
  description: string | null;
  address: string | null;
  city: string;
  zip: string | null;
  asking_price: string | null;
  monthly_rent: string | null;
  size_sqft: number | null;
  seats: number | null;
  parking: boolean | null;
  loading_access: boolean | null;
  type1_hood: boolean | null;
  grease_trap: boolean | null;
  walk_in_cooler: boolean | null;
  source: string;
  source_url: string;
  status: ListingStatus;
  market_status: MarketStatus;
  notes: string | null;
  first_seen_at: string;
  last_seen_at: string;
  overall_score: string | null;
  corporate_catering_score: string | null;
  restaurant_score: string | null;
  score_completeness: string | null;
}

export interface ScoreFactor {
  weight: number;
  score: number | null;
  weighted_points: number | null;
  available: boolean;
  evidence: Record<string, unknown>;
  missing: string[];
}

export interface ListingScore {
  listing_id: string;
  corporate_catering_score: string | null;
  restaurant_score: string | null;
  overall_score: string | null;
  corporate_completeness: string;
  restaurant_completeness: string;
  corporate_factors: Record<string, ScoreFactor>;
  restaurant_factors: Record<string, ScoreFactor>;
  missing_information: string[];
  config_version: string;
  calculated_at: string;
  updated_at: string;
}

export interface ListingEvent {
  id: string;
  event_type: string;
  old_value: Record<string, unknown> | null;
  new_value: Record<string, unknown> | null;
  detected_at: string;
}

export interface ListingSnapshot {
  id: string;
  asking_price: string | null;
  monthly_rent: string | null;
  description: string | null;
  market_status: MarketStatus;
  captured_at: string;
}

export interface EnrichedListing extends Listing {
  scoreDetail: ListingScore | null;
}

export type ExternalLeadSource = "BIZBUYSELL" | "LOOPNET";
export type ExternalLeadStatus = "NEW" | "REVIEWING" | "CONTACT_BROKER" | "PASSED";
export type ExternalLeadDiscoveryMethod = "MANUAL" | "EMAIL_ALERT";

export interface ExternalLead {
  id: string;
  source: ExternalLeadSource;
  source_url: string;
  city: string | null;
  status: ExternalLeadStatus;
  notes: string | null;
  discovery_method: ExternalLeadDiscoveryMethod;
  discovered_at: string;
  created_at: string;
  updated_at: string;
}

export interface ExternalLeadSyncRun {
  id: string;
  source: ExternalLeadSource;
  status: "RUNNING" | "SUCCEEDED" | "FAILED";
  messages_scanned: number;
  links_found: number;
  leads_created: number;
  leads_existing: number;
  error_message: string | null;
  started_at: string;
  completed_at: string | null;
}

export interface BizBuySellEmailSyncStatus {
  enabled: boolean;
  configured: boolean;
  latest_run: ExternalLeadSyncRun | null;
}

export type AIRecommendation = "STRONG_CANDIDATE" | "REVIEW" | "PASS" | "INSUFFICIENT_DATA";

export interface ListingAIAnalysis {
  listing_id: string;
  recommendation: AIRecommendation;
  strengths: string[];
  risks: string[];
  missing_information: string[];
  confidence: string;
  model: string;
  prompt_version: string;
  generated_at: string;
  updated_at: string;
}

export type DueDiligenceAccessMethod = "UNKNOWN" | "EXTERNAL_NDA" | "BROKER_CONTACT";
export type ConfidentialDataStatus =
  | "UNKNOWN"
  | "NDA_REQUIRED"
  | "REQUESTED"
  | "RECEIVED_UNVERIFIED"
  | "VERIFIED"
  | "NOT_PROVIDED";

export interface DueDiligenceProfile {
  id: string;
  listing_id: string;
  access_method: DueDiligenceAccessMethod;
  access_status: ConfidentialDataStatus;
  external_url: string | null;
  broker_contact_name: string | null;
  broker_contact_email: string | null;
  broker_contact_phone: string | null;
  inventory_included: boolean | null;
  ffe_included: boolean | null;
  notes: string | null;
  requested_at: string | null;
  received_at: string | null;
  verified_at: string | null;
  created_by: string;
  updated_by: string;
  created_at: string;
  updated_at: string;
}

export interface FinancialMetric {
  id: string;
  listing_id: string;
  metric_type: string;
  amount: string;
  currency: string;
  period_start: string | null;
  period_end: string | null;
  source: string;
  source_reference: string | null;
  verification_status: "UNVERIFIED" | "VERIFIED";
  notes: string | null;
  created_by: string;
  updated_by: string;
  created_at: string;
  updated_at: string;
}

export interface DueDiligenceSummary {
  profile: DueDiligenceProfile | null;
  metrics: FinancialMetric[];
}

export interface DueDiligenceEvent {
  id: string;
  listing_id: string;
  event_type: string;
  actor: string;
  old_value: Record<string, unknown> | null;
  new_value: Record<string, unknown> | null;
  created_at: string;
}
