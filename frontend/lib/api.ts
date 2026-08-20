import type {
  EnrichedListing,
  ExternalLead,
  BizBuySellEmailSyncStatus,
  ExternalLeadSyncRun,
  Listing,
  ListingEvent,
  ListingScore,
  ListingSnapshot,
  ListingAIAnalysis,
  DueDiligenceSummary,
  DueDiligenceEvent,
  FinancialMetric,
} from "./types";

const API_BASE_URL = (process.env.API_BASE_URL ?? "http://localhost:8000").replace(/\/$/, "");

function protectedHeaders(operatorId?: string): Record<string, string> {
  const apiKey = process.env.INTERNAL_API_KEY;
  if (!apiKey && process.env.APP_ENV === "production") {
    throw new Error("INTERNAL_API_KEY is not configured");
  }
  return {
    ...(apiKey ? { "X-Internal-API-Key": apiKey } : {}),
    ...(operatorId ? { "X-Operator-Id": operatorId } : {}),
  };
}

async function request<T>(
  path: string,
  init?: RequestInit,
  options?: { protected?: boolean; operatorId?: string },
): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    cache: "no-store",
    headers: {
      "Content-Type": "application/json",
      ...(options?.protected ? protectedHeaders(options.operatorId) : {}),
      ...init?.headers,
    },
  });
  if (!response.ok) {
    let detail = `Restaurant Scout API returned ${response.status}`;
    try {
      const payload = (await response.json()) as { detail?: unknown };
      if (typeof payload.detail === "string") detail = payload.detail;
    } catch {
      // Keep the status-based fallback when the API did not return JSON.
    }
    throw new Error(detail);
  }
  return response.json() as Promise<T>;
}

async function optionalRequest<T>(path: string, options?: { protected?: boolean }): Promise<T | null> {
  try {
    return await request<T>(path, undefined, options);
  } catch (error) {
    if (error instanceof Error && error.message.includes("not generated")) return null;
    throw error;
  }
}

export async function getListings(query = ""): Promise<Listing[]> {
  return request<Listing[]>(`/api/listings${query ? `?${query}` : ""}`);
}

export async function getListing(id: string): Promise<Listing> {
  return request<Listing>(`/api/listings/${id}`);
}

export async function getScore(id: string): Promise<ListingScore> {
  return request<ListingScore>(`/api/listings/${id}/scores`);
}

export async function getHistory(id: string): Promise<ListingSnapshot[]> {
  return request<ListingSnapshot[]>(`/api/listings/${id}/history`);
}

export async function getEvents(id: string): Promise<ListingEvent[]> {
  return request<ListingEvent[]>(`/api/listings/${id}/events`);
}

export async function enrichListings(listings: Listing[]): Promise<EnrichedListing[]> {
  return Promise.all(
    listings.map(async (listing) => {
      try {
        const scoreDetail = await getScore(listing.id);
        return {
          ...listing,
          overall_score: scoreDetail.overall_score,
          corporate_catering_score: scoreDetail.corporate_catering_score,
          restaurant_score: scoreDetail.restaurant_score,
          scoreDetail,
        };
      } catch {
        return { ...listing, scoreDetail: null };
      }
    }),
  );
}

export async function updateListing(
  id: string,
  payload: { status?: string; notes?: string | null },
): Promise<Listing> {
  return request<Listing>(`/api/listings/${id}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  }, { protected: true });
}

export async function getExternalLeads(query = ""): Promise<ExternalLead[]> {
  return request<ExternalLead[]>(`/api/external-leads${query ? `?${query}` : ""}`);
}

export async function getBizBuySellEmailSyncStatus(): Promise<BizBuySellEmailSyncStatus> {
  return request<BizBuySellEmailSyncStatus>(
    "/api/external-leads/bizbuysell-email/status",
    undefined,
    { protected: true },
  );
}

export async function syncBizBuySellEmailLinks(): Promise<ExternalLeadSyncRun> {
  return request<ExternalLeadSyncRun>(
    "/api/external-leads/bizbuysell-email/sync",
    { method: "POST" },
    { protected: true },
  );
}

export async function createExternalLead(payload: {
  source_url: string;
  city?: string | null;
  notes?: string | null;
}): Promise<ExternalLead> {
  return request<ExternalLead>("/api/external-leads", {
    method: "POST",
    body: JSON.stringify(payload),
  }, { protected: true });
}

export async function updateExternalLead(
  id: string,
  payload: { city?: string | null; status?: string; notes?: string | null },
): Promise<ExternalLead> {
  return request<ExternalLead>(`/api/external-leads/${id}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  }, { protected: true });
}

export async function getAIAnalysis(id: string): Promise<ListingAIAnalysis | null> {
  return optionalRequest<ListingAIAnalysis>(`/api/listings/${id}/analysis`);
}

export async function generateAIAnalysis(id: string): Promise<ListingAIAnalysis> {
  return request<ListingAIAnalysis>(`/api/listings/${id}/analysis/generate`, {
    method: "POST",
    body: JSON.stringify({ force: true }),
  }, { protected: true });
}

export async function getDueDiligence(id: string): Promise<DueDiligenceSummary> {
  return request<DueDiligenceSummary>(`/api/listings/${id}/due-diligence`, undefined, {
    protected: true,
  });
}

export async function getDueDiligenceEvents(id: string): Promise<DueDiligenceEvent[]> {
  return request<DueDiligenceEvent[]>(`/api/listings/${id}/due-diligence/events`, undefined, {
    protected: true,
  });
}

export async function updateDueDiligenceProfile(
  id: string,
  payload: Record<string, unknown>,
  operatorId: string,
): Promise<DueDiligenceSummary["profile"]> {
  return request(`/api/listings/${id}/due-diligence/profile`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  }, { protected: true, operatorId });
}

export async function createFinancialMetric(
  id: string,
  payload: Record<string, unknown>,
  operatorId: string,
): Promise<FinancialMetric> {
  return request(`/api/listings/${id}/due-diligence/metrics`, {
    method: "POST",
    body: JSON.stringify(payload),
  }, { protected: true, operatorId });
}

export async function updateFinancialMetric(
  listingId: string,
  metricId: string,
  payload: Record<string, unknown>,
  operatorId: string,
): Promise<FinancialMetric> {
  return request(`/api/listings/${listingId}/due-diligence/metrics/${metricId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  }, { protected: true, operatorId });
}
