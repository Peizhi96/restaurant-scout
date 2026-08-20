import Link from "next/link";

import { StatusPill } from "@/components/status-pill";
import { getBizBuySellEmailSyncStatus, getExternalLeads } from "@/lib/api";
import { dateLabel, titleCase } from "@/lib/format";
import type { BizBuySellEmailSyncStatus, ExternalLead } from "@/lib/types";
import { addExternalLead, saveExternalLead, syncBizBuySellLinks } from "./actions";

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
const officialSearches = [
  {
    label: "San Mateo County restaurants",
    href: "https://www.bizbuysell.com/california/san-mateo-county/restaurants-and-food-established-businesses-for-sale/",
  },
  {
    label: "Santa Clara County restaurants",
    href: "https://www.bizbuysell.com/california/santa-clara-county/restaurants-and-food-businesses-for-sale/",
  },
];

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
  let syncStatus: BizBuySellEmailSyncStatus | null = null;
  try {
    [leads, syncStatus] = await Promise.all([
      getExternalLeads(query.toString()),
      getBizBuySellEmailSyncStatus(),
    ]);
  } catch {
    unavailable = true;
  }

  return (
    <div className="page-wrap external-leads-page">
      <header className="page-header compact-header">
        <div>
          <p className="eyebrow">Link-only marketplace discovery</p>
          <h1>Marketplace link feed</h1>
          <p>
            BizBuySell saved-search emails supply individual listing links automatically.
            Restaurant Scout stores and deduplicates those links without opening or copying
            the source listing pages.
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
      {first(search.synced) ? (
        <div className="success-notice"><strong>Email alerts synced.</strong><span>{first(search.created) || "0"} new links were added.</span></div>
      ) : null}

      <section className="panel marketplace-sync-panel">
        <div className="panel-heading">
          <div><p className="eyebrow">Automatic discovery</p><h2>BizBuySell saved searches</h2></div>
          <span className={`connection-badge ${syncStatus?.enabled && syncStatus.configured ? "connected" : "not-connected"}`}>
            {syncStatus?.enabled && syncStatus.configured ? "Connected" : "Setup required"}
          </span>
        </div>
        <p className="guardrail-copy">
          Open the official restaurant searches below, choose your filters, and use
          BizBuySell&apos;s Save Search feature. Its notification emails go to a dedicated
          mailbox; the daily scheduler extracts only individual listing URLs.
        </p>
        <div className="official-search-links">
          {officialSearches.map((searchLink) => <a className="secondary-button" href={searchLink.href} target="_blank" rel="noreferrer" key={searchLink.href}>{searchLink.label} ↗</a>)}
        </div>
        {syncStatus?.enabled && syncStatus.configured ? (
          <div className="sync-actions">
            <form action={syncBizBuySellLinks}><button className="primary-button" type="submit">Sync email alerts now</button></form>
            {syncStatus.latest_run ? <p>Last sync {dateLabel(syncStatus.latest_run.completed_at ?? syncStatus.latest_run.started_at)} · {syncStatus.latest_run.leads_created} new · {syncStatus.latest_run.leads_existing} already saved</p> : <p>Connected. The first sync has not run yet.</p>}
          </div>
        ) : (
          <div className="setup-note"><strong>Email intake is implemented but not connected.</strong><span>Configure the `BIZBUYSELL_IMAP_*` values in the private environment file, then enable `BIZBUYSELL_EMAIL_ALERTS_ENABLED`.</span></div>
        )}
      </section>

      <details className="panel manual-fallback">
        <summary>Manually add a missed link</summary>
        <p className="guardrail-copy">Use this only when an individual BizBuySell or LoopNet link did not arrive through the automatic feed.</p>
        <form action={addExternalLead} className="external-add-form">
          <label><span>Listing URL</span><input name="source_url" type="url" required placeholder="https://www.bizbuysell.com/Business-Opportunity/…" /></label>
          <label><span>Target city</span><select name="city" defaultValue=""><option value="">Unknown / confirm later</option>{cities.map((city) => <option value={city} key={city}>{city}</option>)}</select></label>
          <label><span>Internal note</span><textarea name="notes" rows={3} placeholder="Why this missed link is worth reviewing." /></label>
          <button className="primary-button" type="submit">Save missed link</button>
        </form>
      </details>

      <section className="section-block">
        <div className="section-heading">
          <div><p className="eyebrow">Link-only review queue</p><h2>Discovered marketplace links</h2></div>
          <p>Links are reviewable, but source facts are not copied or scored.</p>
        </div>
        <form className="filter-bar external-filter" action="/external-leads">
          <label><span>Source</span><select name="source" defaultValue={first(search.source)}><option value="">Both sources</option><option value="BIZBUYSELL">BizBuySell</option><option value="LOOPNET">LoopNet</option></select></label>
          <label><span>Status</span><select name="status" defaultValue={first(search.status)}><option value="">Any status</option>{statuses.map((status) => <option value={status} key={status}>{titleCase(status)}</option>)}</select></label>
          <label><span>City</span><select name="city" defaultValue={first(search.city)}><option value="">All / unknown</option>{cities.map((city) => <option value={city} key={city}>{city}</option>)}</select></label>
          <button className="primary-button" type="submit">Apply filters</button>
          <Link className="clear-link" href="/external-leads">Clear</Link>
        </form>
        <div className="results-meta"><p><strong>{leads.length}</strong> marketplace links</p><span>Link-only records are not scored.</span></div>

        {unavailable ? (
          <div className="notice"><strong>The external lead API is unavailable.</strong><span>Start the backend service and refresh.</span></div>
        ) : leads.length ? (
          <div className="external-lead-list">
            {leads.map((lead) => (
              <article className="panel external-lead-card" key={lead.id}>
                <div className="external-lead-heading">
                  <div>
                    <p className="eyebrow">{sourceLabel(lead)} · {lead.discovery_method === "EMAIL_ALERT" ? "Email alert" : "Manual fallback"} · {lead.city ?? "City unknown"}</p>
                    <h3>{sourceLabel(lead)} listing link</h3>
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
          <div className="empty-state"><strong>No marketplace links yet</strong><p>After the dedicated mailbox receives a BizBuySell saved-search alert, the scheduler will add its individual listing links here automatically.</p></div>
        )}
      </section>
    </div>
  );
}
