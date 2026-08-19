import Link from "next/link";

import { compactMoney, scoreLabel } from "@/lib/format";
import type { EnrichedListing } from "@/lib/types";
import { StatusPill } from "./status-pill";

export function ListingCard({ listing, rank }: { listing: EnrichedListing; rank?: number }) {
  return (
    <article className="listing-card">
      <div className="listing-card-top">
        {rank ? <span className="rank">#{rank.toString().padStart(2, "0")}</span> : null}
        <StatusPill value={listing.market_status} kind="market" />
      </div>
      <div>
        <p className="eyebrow">{listing.city} · {listing.source.replaceAll("_", " ")}</p>
        <h3><Link href={`/listings/${listing.id}`}>{listing.title}</Link></h3>
      </div>
      <div className="listing-metrics">
        <div><span>Overall</span><strong>{scoreLabel(listing.overall_score)}</strong></div>
        <div><span>Asking</span><strong>{compactMoney(listing.asking_price)}</strong></div>
        <div><span>Rent / mo.</span><strong>{compactMoney(listing.monthly_rent)}</strong></div>
      </div>
      <div className="listing-card-foot">
        <span>{listing.size_sqft ? `${listing.size_sqft.toLocaleString()} sf` : "Size unknown"}</span>
        <span>{listing.type1_hood === true ? "Type 1 hood" : listing.type1_hood === false ? "No Type 1" : "Hood unknown"}</span>
        <span>{listing.scoreDetail ? `${Math.round((Number(listing.scoreDetail.corporate_completeness) + Number(listing.scoreDetail.restaurant_completeness)) / 2)}% data` : "Unscored"}</span>
        <Link href={`/listings/${listing.id}`} aria-label={`Review ${listing.title}`}>Review →</Link>
      </div>
    </article>
  );
}
