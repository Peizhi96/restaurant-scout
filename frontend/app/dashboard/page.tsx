import Link from "next/link";

import { ListingCard } from "@/components/listing-card";
import { ListingTable } from "@/components/listing-table";
import { ScoreRing } from "@/components/score-ring";
import { asNumber, compactMoney, dateLabel } from "@/lib/format";
import { enrichListings, getEvents, getListings } from "@/lib/api";
import type { EnrichedListing, ListingEvent } from "@/lib/types";

export const dynamic = "force-dynamic";

async function loadDashboard() {
  const listings = await enrichListings(await getListings("limit=100&sort_by=score"));
  const events = await Promise.all(
    listings.map(async (listing) => {
      try {
        return (await getEvents(listing.id)).map((event) => ({ ...event, listing }));
      } catch {
        return [];
      }
    }),
  );
  return { listings, events: events.flat(), loadedAt: Date.now() };
}

export default async function DashboardPage() {
  let listings: EnrichedListing[] = [];
  let events: (ListingEvent & { listing: EnrichedListing })[] = [];
  let loadedAt = 0;
  let unavailable = false;
  try {
    ({ listings, events, loadedAt } = await loadDashboard());
  } catch {
    unavailable = true;
  }

  const active = listings.filter((item) => item.market_status === "ACTIVE");
  const top = [...active]
    .filter((item) => {
      if (asNumber(item.overall_score) === null || item.scoreDetail === null) return false;
      const completeness =
        (Number(item.scoreDetail.corporate_completeness) +
          Number(item.scoreDetail.restaurant_completeness)) /
        2;
      return completeness >= 40;
    })
    .sort((a, b) => (asNumber(b.overall_score) ?? 0) - (asNumber(a.overall_score) ?? 0))
    .slice(0, 3);
  const recent = listings.filter((item) => loadedAt - new Date(item.first_seen_at).getTime() < 86_400_000);
  const priceDrops = events.filter((event) => event.event_type === "PRICE_DROP").slice(0, 5);
  const average = top.length
    ? top.reduce((sum, item) => sum + (asNumber(item.overall_score) ?? 0), 0) / top.length
    : null;

  return (
    <div className="page-wrap">
      <header className="page-header dashboard-header">
        <div><p className="eyebrow">Wednesday, August 19</p><h1>Your acquisition radar.</h1><p>New opportunities, meaningful changes, and the strongest candidates across the Peninsula.</p></div>
        <Link className="primary-button" href="/listings">Explore all listings <span>→</span></Link>
      </header>

      {unavailable ? <div className="notice"><strong>The dashboard cannot reach the API.</strong><span>Start the backend service and refresh this page.</span></div> : null}

      <section className="stat-grid" aria-label="Portfolio summary">
        <article><span className="stat-icon green">A</span><div><p>Active opportunities</p><strong>{active.length}</strong><small>across {new Set(active.map((item) => item.city)).size} target cities</small></div></article>
        <article><span className="stat-icon orange">N</span><div><p>New in 24 hours</p><strong>{recent.length}</strong><small>ready for first review</small></div></article>
        <article><span className="stat-icon blue">↓</span><div><p>Recent price drops</p><strong>{priceDrops.length}</strong><small>detected from source history</small></div></article>
        <article className="score-stat"><ScoreRing value={average} size="small" /><div><p>Top candidate average</p><strong>{average === null ? "—" : Math.round(average)}</strong><small>normalized deterministic score</small></div></article>
      </section>

      <section className="section-block">
        <div className="section-heading"><div><p className="eyebrow">Priority queue</p><h2>Top candidates</h2></div><p>Ranked by the 60/40 catering and restaurant blend. Completeness remains visible on each detail page.</p></div>
        {top.length ? <div className="candidate-grid">{top.map((listing, index) => <ListingCard listing={listing} rank={index + 1} key={listing.id} />)}</div> : <div className="empty-state"><strong>No scored active candidates yet</strong><p>A score is calculated when a listing is ingested or opened.</p></div>}
      </section>

      <section className="split-grid section-block">
        <div className="panel">
          <div className="panel-heading"><div><p className="eyebrow">Latest inventory</p><h2>Recently discovered</h2></div><Link href="/listings">View all →</Link></div>
          <ListingTable listings={listings.slice(0, 5)} />
        </div>
        <aside className="panel change-panel">
          <div className="panel-heading"><div><p className="eyebrow">Signal, not noise</p><h2>Price movement</h2></div></div>
          {priceDrops.length ? priceDrops.map((event) => (
            <Link href={`/listings/${event.listing.id}`} className="change-item" key={event.id}>
              <span className="change-mark">↓</span><div><strong>{event.listing.title}</strong><small>{event.listing.city} · {dateLabel(event.detected_at)}</small></div><b>{compactMoney(String(event.new_value?.asking_price ?? ""))}</b>
            </Link>
          )) : <div className="empty-compact">No price drops detected yet.</div>}
        </aside>
      </section>
    </div>
  );
}
