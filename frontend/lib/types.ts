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
