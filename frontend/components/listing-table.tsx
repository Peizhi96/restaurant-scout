import Link from "next/link";

import { compactMoney, dateLabel, scoreLabel } from "@/lib/format";
import { candidateMinimumCompleteness } from "@/lib/ranking";
import type { EnrichedListing } from "@/lib/types";
import { StatusPill } from "./status-pill";

export function ListingTable({
  listings,
  dateMode = "lastSeen",
}: {
  listings: EnrichedListing[];
  dateMode?: "discovered" | "lastSeen";
}) {
  const minimumCompleteness = candidateMinimumCompleteness();
  if (!listings.length) {
    return <div className="empty-state"><strong>No listings found</strong><p>Try widening the filters or wait for the next collection run.</p></div>;
  }
  return (
    <div className="table-scroll">
      <table className="listing-table">
        <thead><tr><th>Opportunity</th><th>Economics</th><th>Space</th><th>Scores</th><th>Pipeline</th><th>Discovery / freshness</th><th /></tr></thead>
        <tbody>
          {listings.map((listing) => (
            <tr key={listing.id}>
              <td><strong>{listing.title}</strong><span>{listing.city} · {listing.source.replaceAll("_", " ")}</span></td>
              <td><strong>{compactMoney(listing.asking_price)}</strong><span>{compactMoney(listing.monthly_rent)} / month</span></td>
              <td><strong>{listing.size_sqft ? `${listing.size_sqft.toLocaleString()} sf` : "—"}</strong><span>{listing.type1_hood === true ? "Type 1 hood" : "Hood unknown"}</span></td>
              <td><div className="inline-scores"><b>{scoreLabel(listing.overall_score)}</b><span>C {scoreLabel(listing.corporate_catering_score)} · R {scoreLabel(listing.restaurant_score)}</span><small>{scoreLabel(listing.score_completeness)}% data · {Number(listing.score_completeness ?? 0) >= minimumCompleteness ? "candidate-ready" : "preliminary"}</small></div></td>
              <td><StatusPill value={listing.status} /><small>Market: {listing.market_status.replaceAll("_", " ").toLowerCase()}</small></td>
              <td className="freshness-cell">
                <strong>{dateMode === "discovered" ? "Discovered" : "Last checked"} {dateLabel(dateMode === "discovered" ? listing.first_seen_at : listing.last_seen_at)}</strong>
                <span>{dateMode === "discovered" ? "Last checked" : "Discovered"} {dateLabel(dateMode === "discovered" ? listing.last_seen_at : listing.first_seen_at)}</span>
              </td>
              <td><Link className="arrow-link" href={`/listings/${listing.id}`}>→</Link></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
