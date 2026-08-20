import Link from "next/link";
import { notFound } from "next/navigation";

import { StatusPill } from "@/components/status-pill";
import { getDueDiligence, getDueDiligenceEvents, getListing } from "@/lib/api";
import { dateLabel, money, titleCase } from "@/lib/format";
import type { DueDiligenceProfile } from "@/lib/types";
import {
  addFinancialMetric,
  saveDueDiligenceProfile,
  verifyFinancialMetric,
} from "./actions";

export const dynamic = "force-dynamic";

function triState(value: boolean | null | undefined): string {
  return value === true ? "YES" : value === false ? "NO" : "UNKNOWN";
}

function ProfileForm({ id, profile }: { id: string; profile: DueDiligenceProfile | null }) {
  return (
    <form action={saveDueDiligenceProfile} className="dd-form">
      <input type="hidden" name="id" value={id} />
      <div className="dd-form-grid">
        <label><span>Access method</span><select name="access_method" defaultValue={profile?.access_method ?? "UNKNOWN"}>{["UNKNOWN", "EXTERNAL_NDA", "BROKER_CONTACT"].map((value) => <option value={value} key={value}>{titleCase(value)}</option>)}</select></label>
        <label><span>Data status</span><select name="access_status" defaultValue={profile?.access_status ?? "UNKNOWN"}>{["UNKNOWN", "NDA_REQUIRED", "REQUESTED", "RECEIVED_UNVERIFIED", "VERIFIED", "NOT_PROVIDED"].map((value) => <option value={value} key={value}>{titleCase(value)}</option>)}</select></label>
        <label className="span-2"><span>Official NDA / handoff URL</span><input name="external_url" type="url" defaultValue={profile?.external_url ?? ""} placeholder="https://broker.example/nda/..." /></label>
        <label><span>Broker name</span><input name="broker_contact_name" defaultValue={profile?.broker_contact_name ?? ""} /></label>
        <label><span>Broker email</span><input name="broker_contact_email" type="email" defaultValue={profile?.broker_contact_email ?? ""} /></label>
        <label><span>Broker phone</span><input name="broker_contact_phone" defaultValue={profile?.broker_contact_phone ?? ""} /></label>
        <label><span>Inventory included</span><select name="inventory_included" defaultValue={triState(profile?.inventory_included)}>{["UNKNOWN", "YES", "NO"].map((value) => <option value={value} key={value}>{titleCase(value)}</option>)}</select></label>
        <label><span>FF&amp;E included</span><select name="ffe_included" defaultValue={triState(profile?.ffe_included)}>{["UNKNOWN", "YES", "NO"].map((value) => <option value={value} key={value}>{titleCase(value)}</option>)}</select></label>
        <label className="span-2"><span>Confidential review notes</span><textarea name="notes" rows={5} defaultValue={profile?.notes ?? ""} placeholder="Record NDA status, document questions, and verification notes…" /></label>
      </div>
      <button className="primary-button" type="submit">Save due diligence profile</button>
    </form>
  );
}

export default async function DueDiligencePage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  let listing;
  try {
    listing = await getListing(id);
  } catch {
    notFound();
  }
  const [summary, events] = await Promise.all([getDueDiligence(id), getDueDiligenceEvents(id)]);
  const canAddMetrics = summary.profile?.access_status === "RECEIVED_UNVERIFIED" || summary.profile?.access_status === "VERIFIED";

  return (
    <div className="page-wrap dd-page">
      <div className="breadcrumb"><Link href={`/listings/${id}`}>← {listing.title}</Link><span>/</span><span>Due diligence</span></div>
      <header className="page-header compact-header"><div><p className="eyebrow">Protected workspace · confidential</p><h1>Due diligence</h1><p>Track only authorized NDA handoffs and received financial facts. This area never fetches gated pages or guesses missing values.</p></div><StatusPill value={summary.profile?.access_status ?? "UNKNOWN"} /></header>

      <section className="panel section-block"><div className="panel-heading"><div><p className="eyebrow">Access &amp; handoff</p><h2>NDA and broker workflow</h2></div>{summary.profile ? <span className="calculated-label">Updated by {summary.profile.updated_by} · {dateLabel(summary.profile.updated_at)}</span> : null}</div><ProfileForm id={id} profile={summary.profile} /></section>

      <section className="panel section-block"><div className="panel-heading"><div><p className="eyebrow">Received data only</p><h2>Financial metrics</h2></div></div>{summary.metrics.length ? <div className="table-scroll"><table><thead><tr><th>Metric</th><th>Amount</th><th>Period</th><th>Source</th><th>Verification</th><th /></tr></thead><tbody>{summary.metrics.map((metric) => <tr key={metric.id}><td><strong>{titleCase(metric.metric_type)}</strong></td><td>{money(metric.amount)}</td><td>{metric.period_start ?? "Unknown"} – {metric.period_end ?? "Unknown"}</td><td>{metric.source}<small className="table-note">{metric.source_reference ?? "No reference"}</small></td><td><StatusPill value={metric.verification_status} /></td><td>{metric.verification_status === "UNVERIFIED" ? <form action={verifyFinancialMetric}><input type="hidden" name="id" value={id} /><input type="hidden" name="metric_id" value={metric.id} /><button className="secondary-button" type="submit">Mark verified</button></form> : null}</td></tr>)}</tbody></table></div> : <div className="empty-compact">No financial metrics recorded.</div>}
        <div className="dd-divider" />
        {canAddMetrics ? <form action={addFinancialMetric} className="dd-form"><input type="hidden" name="id" value={id} /><div className="dd-form-grid"><label><span>Metric</span><select name="metric_type">{["GROSS_REVENUE", "CASH_FLOW", "SDE", "EBITDA", "INVENTORY_VALUE", "FFE_VALUE"].map((value) => <option value={value} key={value}>{titleCase(value)}</option>)}</select></label><label><span>Amount</span><input name="amount" type="number" step="0.01" required /></label><label><span>Currency</span><input name="currency" defaultValue="USD" minLength={3} maxLength={3} required /></label><label><span>Source</span><input name="source" placeholder="Broker package, tax return…" required /></label><label><span>Period start</span><input name="period_start" type="date" /></label><label><span>Period end</span><input name="period_end" type="date" /></label><label className="span-2"><span>Source reference</span><input name="source_reference" placeholder="File name, page, or authorized external reference" /></label><label className="span-2"><span>Notes</span><textarea name="metric_notes" rows={3} /></label></div><button className="primary-button" type="submit">Add unverified metric</button></form> : <div className="notice"><strong>Data gate active.</strong><span>Set the profile to Received unverified or Verified before recording financial metrics.</span></div>}
      </section>

      <section className="panel section-block"><div className="panel-heading"><div><p className="eyebrow">Immutable audit trail</p><h2>Activity</h2></div></div>{events.length ? <div className="timeline">{events.map((event) => <div className="timeline-item" key={event.id}><span /><div><strong>{titleCase(event.event_type)}</strong><small>{event.actor} · {dateLabel(event.created_at)}</small></div></div>)}</div> : <div className="empty-compact">No due diligence activity yet.</div>}</section>
    </div>
  );
}
