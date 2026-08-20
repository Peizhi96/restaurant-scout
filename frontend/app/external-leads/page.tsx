import Link from "next/link";

import { StatusPill } from "@/components/status-pill";
import { getExternalLeads } from "@/lib/api";
import { dateLabel, titleCase } from "@/lib/format";
import type { ExternalLead } from "@/lib/types";
import { addExternalLead, saveExternalLead } from "./actions";

export const dynamic = "force-dynamic";

type Search = Record<string, string | string[] | undefined>;

const cities = [
  "San Mateo",
  "San Carlos",
  "Redwood City",
  "Palo Alto",
  "Mountain View",
  "Sunnyvale",
];
const statuses = ["NEW", "REVIEWING", "CONTACT_BROKER", "PASSED"];

function first(value: string | string[] | undefined): string {
  return Array.isArray(value) ? value[0] ?? "" : value ?? "";
}

function sourceLabel(lead: ExternalLead): string {
  return lead.source === "BIZBUYSELL" ? "BizBuySell" : "LoopNet";
}

export default async function ExternalLeadsPage({
  searchParams,
}: {
  searchParams: Promise<Search>;
}) {
  const search = await searchParams;
  const query = new URLSearchParams();
  for (const name of ["source", "status", "city"]) {
    const value = first(search[name]);
    if (value) query.set(name, value);
  }
  query.set("limit", "200");

  let leads: ExternalLead[] = [];
  let unavailable = false;
  try {
    leads = await getExternalLeads(query.toString());
  } catch {
    unavailable = true;
  }

  return (
    <div className="page-wrap external-leads-page">
      <header className="page-header compact-header">
        <div>
          <p className="eyebrow">Link-only discovery</p>
          <h1>External leads</h1>
          <p>
            Keep BizBuySell and LoopNet opportunities in view without copying source
            listing facts into Restaurant Scout.
          </p>
        </div>
        <Link className="secondary-button" href="/dashboard">Back to overview</Link>
      </header>

      {first(search.error) ? (
        <div className="notice"><strong>Could not save lead.</strong><span>{first(search.error)}</span></div>
      ) : null}
      {first(search.added) ? (
        <div className="success-notice"><strong>Lead added.</strong><span>The source link is ready for review.</span></div>
      ) : null}
      {first(search.saved) ? (
        <div className="success-notice"><strong>Review saved.</strong><span>Status and internal notes are up to date.</span></div>
      ) : null}

      <section className="panel external-add-panel">
        <div className="panel-heading">
          <div><p className="eyebrow">Paste, then review</p><h2>Add an external lead</h2></div>
        </div>
        <p className="guardrail-copy">
          Paste an individual BizBuySell or LoopNet listing URL. Restaurant Scout stores
          the link and your internal workflow only; it does not fetch the source page.
        </p>
        <form action={addExternalLead} className="external-add-form">
          <label>
            <span>Listing URL</span>
            <input name="source_url" type="url" required placeholder="https://www.bizbuysell.com/Business-Opportunity/…" />
          </label>
          <label>
            <span>Target city</span>
            <select name="city" defaultValue="">
              <option value="">Unknown / confirm later</option>
              {cities.map((city) => <option value={city} key={city}>{city}</option>)}
            </select>
          </label>
          <label>
            <span>Internal note</span>
            <textarea name="notes" rows={3} placeholder="Why this link is worth reviewing; do not copy the source listing description." />
          </label>
          <button className="primary-button" type="submit">Add external lead</button>
        </form>
      </section>

      <section className="section-block">
        <div className="section-heading">
          <div><p className="eyebrow">Review queue</p><h2>Saved links</h2></div>
          <p>These records are intentionally separate from scored canonical listings.</p>
        </div>
        <form className="filter-bar external-filter" action="/external-leads">
          <label><span>Source</span><select name="source" defaultValue={first(search.source)}><option value="">Both sources</option><option value="BIZBUYSELL">BizBuySell</option><option value="LOOPNET">LoopNet</option></select></label>
          <label><span>Status</span><select name="status" defaultValue={first(search.status)}><option value="">Any status</option>{statuses.map((status) => <option value={status} key={status}>{titleCase(status)}</option>)}</select></label>
          <label><span>City</span><select name="city" defaultValue={first(search.city)}><option value="">All / unknown</option>{cities.map((city) => <option value={city} key={city}>{city}</option>)}</select></label>
          <button className="primary-button" type="submit">Apply filters</button>
          <Link className="clear-link" href="/external-leads">Clear</Link>
        </form>
        <div className="results-meta"><p><strong>{leads.length}</strong> external leads</p><span>Link-only records are not scored.</span></div>

        {unavailable ? (
          <div className="notice"><strong>The external lead API is unavailable.</strong><span>Start the backend service and refresh.</span></div>
        ) : leads.length ? (
          <div className="external-lead-list">
            {leads.map((lead) => (
              <article className="panel external-lead-card" key={lead.id}>
                <div className="external-lead-heading">
                  <div>
                    <p className="eyebrow">{sourceLabel(lead)} · {lead.city ?? "City unknown"}</p>
                    <h3>{sourceLabel(lead)} external opportunity</h3>
                    <a href={lead.source_url} target="_blank" rel="noreferrer" className="external-url">{lead.source_url}</a>
                  </div>
                  <div className="external-lead-meta"><StatusPill value={lead.status} /><span>Discovered {dateLabel(lead.discovered_at)}</span></div>
                </div>
                <a className="secondary-button external-open-button" href={lead.source_url} target="_blank" rel="noreferrer">Open source listing ↗</a>
                <form action={saveExternalLead} className="external-review-form">
                  <input type="hidden" name="id" value={lead.id} />
                  <label><span>Pipeline status</span><select name="status" defaultValue={lead.status}>{statuses.map((status) => <option value={status} key={status}>{titleCase(status)}</option>)}</select></label>
                  <label><span>Target city</span><select name="city" defaultValue={lead.city ?? ""}><option value="">Unknown</option>{cities.map((city) => <option value={city} key={city}>{city}</option>)}</select></label>
                  <label><span>Internal notes</span><textarea name="notes" rows={3} defaultValue={lead.notes ?? ""} placeholder="Record your own review, broker follow-up, or next action." /></label>
                  <button className="primary-button" type="submit">Save review</button>
                </form>
              </article>
            ))}
          </div>
        ) : (
          <div className="empty-state"><strong>No external leads yet</strong><p>Paste a BizBuySell or LoopNet listing link above to start the queue.</p></div>
        )}
      </section>
    </div>
  );
}
