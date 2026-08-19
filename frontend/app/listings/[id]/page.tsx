import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { ScoreRing } from "@/components/score-ring";
import { StatusPill } from "@/components/status-pill";
import { getEvents, getHistory, getListing, getScore } from "@/lib/api";
import { dateLabel, money, scoreLabel, titleCase } from "@/lib/format";
import type { Listing, ListingEvent, ListingScore, ListingSnapshot, ScoreFactor } from "@/lib/types";
import { saveListing } from "./actions";

export const dynamic = "force-dynamic";

async function load(id: string) {
  const [listing, score, history, events] = await Promise.all([
    getListing(id),
    getScore(id),
    getHistory(id),
    getEvents(id),
  ]);
  return { listing, score, history, events };
}

export async function generateMetadata({ params }: { params: Promise<{ id: string }> }): Promise<Metadata> {
  const { id } = await params;
  try {
    const listing = await getListing(id);
    return { title: listing.title, description: `${listing.city} restaurant acquisition opportunity.` };
  } catch {
    return { title: "Listing" };
  }
}

function DataPoint({ label, value, hint }: { label: string; value: React.ReactNode; hint?: string }) {
  return <div className="data-point"><span>{label}</span><strong>{value ?? "Unknown"}</strong>{hint ? <small>{hint}</small> : null}</div>;
}

function Fact({ label, value }: { label: string; value: boolean | null }) {
  return <div className="fact-row"><span>{label}</span><strong className={value === true ? "yes" : value === false ? "no" : "unknown"}>{value === true ? "Confirmed" : value === false ? "No" : "Unknown"}</strong></div>;
}

function FactorList({ factors }: { factors: Record<string, ScoreFactor> }) {
  return <div className="factor-list">{Object.entries(factors).map(([name, factor]) => <div className="factor-row" key={name}><div><strong>{titleCase(name)}</strong><span>{factor.available ? `Weight ${factor.weight}` : "Awaiting data"}</span></div><div className="factor-track"><i style={{ width: `${factor.score ?? 0}%` }} /></div><b>{factor.score === null ? "—" : Math.round(factor.score)}</b></div>)}</div>;
}

export default async function ListingDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  let listing: Listing;
  let score: ListingScore;
  let history: ListingSnapshot[];
  let events: ListingEvent[];
  try {
    ({ listing, score, history, events } = await load(id));
  } catch (error) {
    if (error instanceof Error && error.message.includes("404")) notFound();
    throw error;
  }

  return (
    <div className="page-wrap detail-page">
      <div className="breadcrumb"><Link href="/listings">All listings</Link><span>/</span><span>{listing.city}</span></div>
      <header className="detail-hero">
        <div className="detail-title"><div className="pill-row"><StatusPill value={listing.market_status} kind="market" /><StatusPill value={listing.status} /></div><p className="eyebrow">{listing.city} · {listing.source.replaceAll("_", " ")}</p><h1>{listing.title}</h1><p>{listing.description ?? "The source has not published a description for this opportunity."}</p><div className="hero-actions"><a className="primary-button" href={listing.source_url} target="_blank" rel="noreferrer">Open source listing ↗</a><span>Last seen {dateLabel(listing.last_seen_at)}</span></div></div>
        <div className="hero-score"><ScoreRing value={score.overall_score} label="Overall" size="large" /><div><span>60% catering</span><span>40% restaurant</span></div></div>
      </header>

      <section className="economics-strip">
        <DataPoint label="Asking price" value={money(listing.asking_price)} />
        <DataPoint label="Monthly rent" value={money(listing.monthly_rent)} hint={listing.monthly_rent && listing.size_sqft ? `${money(Number(listing.monthly_rent) / listing.size_sqft)} / sf` : undefined} />
        <DataPoint label="Interior" value={listing.size_sqft ? `${listing.size_sqft.toLocaleString()} sf` : "Unknown"} />
        <DataPoint label="Seats" value={listing.seats ?? "Unknown"} />
      </section>

      <div className="detail-grid">
        <div className="detail-main">
          <section className="panel score-panel"><div className="panel-heading"><div><p className="eyebrow">Deterministic analysis</p><h2>Two lenses, kept separate</h2></div><span className="calculated-label">Updated {dateLabel(score.calculated_at)}</span></div><div className="dual-score"><div><ScoreRing value={score.corporate_catering_score} label="Catering" /><p><strong>{scoreLabel(score.corporate_completeness)}% complete</strong><span>Kitchen production, delivery logistics, rent, and scale.</span></p></div><div><ScoreRing value={score.restaurant_score} label="Restaurant" /><p><strong>{scoreLabel(score.restaurant_completeness)}% complete</strong><span>Rent, parking, kitchen, seats, and local demand inputs.</span></p></div></div><div className="factor-columns"><div><h3>Corporate catering factors</h3><FactorList factors={score.corporate_factors} /></div><div><h3>Restaurant factors</h3><FactorList factors={score.restaurant_factors} /></div></div></section>

          <section className="panel"><div className="panel-heading"><div><p className="eyebrow">Source history</p><h2>Economics over time</h2></div></div>{history.length ? <div className="table-scroll"><table className="history-table"><thead><tr><th>Captured</th><th>Asking</th><th>Rent / mo.</th><th>Market</th></tr></thead><tbody>{history.map((snapshot) => <tr key={snapshot.id}><td>{dateLabel(snapshot.captured_at)}</td><td>{money(snapshot.asking_price)}</td><td>{money(snapshot.monthly_rent)}</td><td><StatusPill value={snapshot.market_status} kind="market" /></td></tr>)}</tbody></table></div> : <div className="empty-compact">No snapshots recorded.</div>}</section>

          <section className="panel"><div className="panel-heading"><div><p className="eyebrow">Change log</p><h2>Detected events</h2></div></div>{events.length ? <div className="timeline">{events.map((event) => <div className="timeline-item" key={event.id}><span /><div><strong>{titleCase(event.event_type)}</strong><small>{dateLabel(event.detected_at)}</small></div></div>)}</div> : <div className="empty-compact">No change events beyond the current snapshot.</div>}</section>
        </div>

        <aside className="detail-aside">
          <section className="panel"><div className="panel-heading"><div><p className="eyebrow">Kitchen & access</p><h2>Known facts</h2></div></div><div className="fact-list"><Fact label="Type 1 hood" value={listing.type1_hood} /><Fact label="Grease trap" value={listing.grease_trap} /><Fact label="Walk-in cooler" value={listing.walk_in_cooler} /><Fact label="Parking" value={listing.parking} /><Fact label="Loading access" value={listing.loading_access} /></div></section>
          <section className="panel missing-panel"><div className="panel-heading"><div><p className="eyebrow">Confidence guardrail</p><h2>Missing information</h2></div></div><p>Unknown facts do not count as zero. They reduce completeness and remain explicit.</p><div className="tag-cloud">{score.missing_information.map((item) => <span key={item}>{titleCase(item)}</span>)}</div></section>
          <section className="panel"><div className="panel-heading"><div><p className="eyebrow">Deal workflow</p><h2>Operator review</h2></div></div><form action={saveListing} className="workflow-form"><input type="hidden" name="id" value={listing.id} /><label><span>Pipeline status</span><select name="status" defaultValue={listing.status}>{["NEW", "REVIEWING", "CONTACT_BROKER", "DUE_DILIGENCE", "PASSED", "REJECTED", "SOLD", "OFF_MARKET"].map((status) => <option value={status} key={status}>{titleCase(status)}</option>)}</select></label><label><span>Notes</span><textarea name="notes" defaultValue={listing.notes ?? ""} placeholder="Record broker questions, lease concerns, or next steps…" rows={5} /></label><button type="submit" className="primary-button">Save review</button></form></section>
        </aside>
      </div>
    </div>
  );
}
