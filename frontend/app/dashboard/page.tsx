import Link from "next/link";

import { ListingCard } from "@/components/listing-card";
import { ListingTable } from "@/components/listing-table";
import { ScoreRing } from "@/components/score-ring";
import { asNumber, compactMoney, dateLabel, dateTimeLabel } from "@/lib/format";
import { enrichListings, getCollectionRuns, getEvents, getListings, getSchedulerStatus } from "@/lib/api";
import { candidateMinimumCompleteness } from "@/lib/ranking";
import type { CollectionRun, EnrichedListing, ListingEvent, SchedulerStatus } from "@/lib/types";

export const dynamic = "force-dynamic";

async function loadDashboard() {
  const listings = await enrichListings(await getListings("limit=100&sort_by=recent"));
  const [collectionRunsResult, schedulerResult] = await Promise.allSettled([
    getCollectionRuns(),
    getSchedulerStatus(),
  ]);
  const collectionRuns = collectionRunsResult.status === "fulfilled" ? collectionRunsResult.value : [];
  const scheduler = schedulerResult.status === "fulfilled" ? schedulerResult.value : null;
  const events = await Promise.all(
    listings.map(async (listing) => {
      try {
        return (await getEvents(listing.id)).map((event) => ({ ...event, listing }));
      } catch {
        return [];
      }
    }),
  );
  return { listings, events: events.flat(), collectionRuns, scheduler, loadedAt: Date.now() };
}

export default async function DashboardPage() {
  let listings: EnrichedListing[] = [];
  let events: (ListingEvent & { listing: EnrichedListing })[] = [];
  let collectionRuns: CollectionRun[] = [];
  let scheduler: SchedulerStatus | null = null;
  let loadedAt = 0;
  let unavailable = false;
  try {
    ({ listings, events, collectionRuns, scheduler, loadedAt } = await loadDashboard());
  } catch {
    unavailable = true;
  }

  const active = listings.filter((item) => item.market_status === "ACTIVE");
  const minimumCompleteness = candidateMinimumCompleteness();
  const top = [...active]
    .filter((item) => {
      if (asNumber(item.overall_score) === null || item.scoreDetail === null) return false;
      const completeness =
        (Number(item.scoreDetail.corporate_completeness) +
          Number(item.scoreDetail.restaurant_completeness)) /
        2;
      return completeness >= minimumCompleteness;
    })
    .sort((a, b) => (asNumber(b.overall_score) ?? 0) - (asNumber(a.overall_score) ?? 0))
    .slice(0, 3);
  const recentInventory = [...listings]
    .sort(
      (a, b) =>
        new Date(b.first_seen_at).getTime() - new Date(a.first_seen_at).getTime(),
    )
    .slice(0, 5);
  const recent = listings.filter((item) => loadedAt - new Date(item.first_seen_at).getTime() < 86_400_000);
  const priceDrops = events.filter((event) => event.event_type === "PRICE_DROP").slice(0, 5);
  const average = top.length
    ? top.reduce((sum, item) => sum + (asNumber(item.overall_score) ?? 0), 0) / top.length
    : null;
  const latestSuccessfulRun = collectionRuns.find(
    (run) => run.status === "COMPLETED" && run.completed_at !== null,
  );
  const todayLabel = new Intl.DateTimeFormat("en-US", {
    weekday: "long",
    month: "long",
    day: "numeric",
    timeZone: "America/Los_Angeles",
  }).format(new Date());

  return (
    <div className="page-wrap">
      <header className="page-header dashboard-header">
        <div><p className="eyebrow">{todayLabel}</p><h1>Your acquisition radar.</h1><p>New opportunities, meaningful changes, and the strongest candidates across the Peninsula.</p></div>
        <Link className="primary-button" href="/listings">Explore all listings <span>→</span></Link>
      </header>

      {unavailable ? <div className="notice"><strong>The dashboard cannot reach the API.</strong><span>Start the backend service and refresh this page.</span></div> : null}

      {!unavailable ? <section className="freshness-strip" aria-label="Collection freshness">
        <article><span className="live-dot" /><div><small>Last successful source scan</small><strong>{latestSuccessfulRun?.completed_at ? dateTimeLabel(latestSuccessfulRun.completed_at) : "No successful scan yet"}</strong></div></article>
        <article><span className="schedule-mark">8:00</span><div><small>Next scheduled scan</small><strong>{scheduler ? dateTimeLabel(scheduler.next_run_at) : "Schedule unavailable"}</strong></div></article>
        <p>“Discovered” is when a listing first entered Scout; “Last checked” confirms when its source was most recently scanned.</p>
      </section> : null}

      <section className="stat-grid" aria-label="Portfolio summary">
        <article><span className="stat-icon green">A</span><div><p>Active opportunities</p><strong>{active.length}</strong><small>across {new Set(active.map((item) => item.city)).size} target cities</small></div></article>
        <article><span className="stat-icon orange">N</span><div><p>New in 24 hours</p><strong>{recent.length}</strong><small>ready for first review</small></div></article>
        <article><span className="stat-icon blue">↓</span><div><p>Recent price drops</p><strong>{priceDrops.length}</strong><small>detected from source history</small></div></article>
        <article className="score-stat"><ScoreRing value={average} size="small" /><div><p>Top candidate average</p><strong>{average === null ? "—" : Math.round(average)}</strong><small>normalized deterministic score</small></div></article>
      </section>

      <section className="section-block">
        <div className="section-heading"><div><p className="eyebrow">Priority queue</p><h2>Qualified candidates</h2></div><p>Active listings with at least {minimumCompleteness}% of scoring inputs known, ranked by the 60/40 catering and restaurant blend. Preliminary scores stay in inventory until more facts are verified.</p></div>
        {top.length ? <div className="candidate-grid">{top.map((listing, index) => <ListingCard listing={listing} rank={index + 1} key={listing.id} />)}</div> : <div className="empty-state"><strong>No scored active candidates yet</strong><p>A score is calculated when a listing is ingested or opened.</p></div>}
      </section>

      <section className="split-grid section-block">
        <div className="panel">
          <div className="panel-heading"><div><p className="eyebrow">Latest inventory · newest first</p><h2>Recently discovered and rechecked</h2></div><Link href="/listings">View all →</Link></div>
          <ListingTable listings={recentInventory} dateMode="discovered" />
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
