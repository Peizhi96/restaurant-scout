import Link from "next/link";

import { compactMoney, dateLabel, scoreLabel } from "@/lib/format";
import type { EnrichedListing } from "@/lib/types";
import { StatusPill } from "./status-pill";

export function ListingTable({ listings }: { listings: EnrichedListing[] }) {
  if (!listings.length) {
    return <div className="empty-state"><strong>No listings found</strong><p>Try widening the filters or wait for the next collection run.</p></div>;
  }
  return (
    <div className="table-scroll">
      <table className="listing-table">
        <thead><tr><th>Opportunity</th><th>Economics</th><th>Space</th><th>Scores</th><th>Pipeline</th><th>Last seen</th><th /></tr></thead>
        <tbody>
          {listings.map((listing) => (
            <tr key={listing.id}>
              <td><strong>{listing.title}</strong><span>{listing.city} · {listing.source.replaceAll("_", " ")}</span></td>
              <td><strong>{compactMoney(listing.asking_price)}</strong><span>{compactMoney(listing.monthly_rent)} / month</span></td>
              <td><strong>{listing.size_sqft ? `${listing.size_sqft.toLocaleString()} sf` : "—"}</strong><span>{listing.type1_hood === true ? "Type 1 hood" : "Hood unknown"}</span></td>
              <td><div className="inline-scores"><b>{scoreLabel(listing.overall_score)}</b><span>C {scoreLabel(listing.corporate_catering_score)} · R {scoreLabel(listing.restaurant_score)}</span></div></td>
              <td><StatusPill value={listing.status} /></td>
              <td>{dateLabel(listing.last_seen_at)}</td>
              <td><Link className="arrow-link" href={`/listings/${listing.id}`}>→</Link></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
