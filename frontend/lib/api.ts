import type {
  EnrichedListing,
  ExternalLead,
  Listing,
  ListingEvent,
  ListingScore,
  ListingSnapshot,
} from "./types";

const API_BASE_URL = (process.env.API_BASE_URL ?? "http://localhost:8000").replace(/\/$/, "");

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    cache: "no-store",
    headers: { "Content-Type": "application/json", ...init?.headers },
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
  });
}

export async function getExternalLeads(query = ""): Promise<ExternalLead[]> {
  return request<ExternalLead[]>(`/api/external-leads${query ? `?${query}` : ""}`);
}

export async function createExternalLead(payload: {
  source_url: string;
  city?: string | null;
  notes?: string | null;
}): Promise<ExternalLead> {
  return request<ExternalLead>("/api/external-leads", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateExternalLead(
  id: string,
  payload: { city?: string | null; status?: string; notes?: string | null },
): Promise<ExternalLead> {
  return request<ExternalLead>(`/api/external-leads/${id}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}
