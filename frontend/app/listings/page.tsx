import Link from "next/link";

import { ListingTable } from "@/components/listing-table";
import { enrichListings, getListings } from "@/lib/api";
import type { EnrichedListing } from "@/lib/types";

export const dynamic = "force-dynamic";

type Search = Record<string, string | string[] | undefined>;

function first(value: string | string[] | undefined): string {
  return Array.isArray(value) ? value[0] ?? "" : value ?? "";
}

export default async function ListingsPage({ searchParams }: { searchParams: Promise<Search> }) {
  const search = await searchParams;
  const query = new URLSearchParams();
  for (const name of ["city", "status", "max_monthly_rent", "min_overall_score", "sort_by"]) {
    const value = first(search[name]);
    if (value) query.set(name, value);
  }
  if (first(search.type1_hood) === "true") query.set("type1_hood", "true");
  query.set("limit", "200");

  let listings: EnrichedListing[] = [];
  let unavailable = false;
  try {
    listings = await enrichListings(await getListings(query.toString()));
    if (first(search.sort_by) === "score") {
      listings.sort((a, b) => Number(b.overall_score ?? -1) - Number(a.overall_score ?? -1));
    }
  } catch {
    unavailable = true;
  }

  return (
    <div className="page-wrap">
      <header className="page-header compact-header"><div><p className="eyebrow">Opportunity pipeline</p><h1>All listings</h1><p>Filter the corridor, compare economics, and move the right deals forward.</p></div><Link className="secondary-button" href="/dashboard">Back to overview</Link></header>
      <form className="filter-bar" action="/listings">
        <label><span>City</span><select name="city" defaultValue={first(search.city)}><option value="">All target cities</option>{["San Mateo", "San Carlos", "Redwood City", "Palo Alto", "Mountain View", "Sunnyvale"].map((city) => <option value={city} key={city}>{city}</option>)}</select></label>
        <label><span>Pipeline</span><select name="status" defaultValue={first(search.status)}><option value="">Any status</option>{["NEW", "REVIEWING", "CONTACT_BROKER", "DUE_DILIGENCE", "PASSED"].map((status) => <option value={status} key={status}>{status.replaceAll("_", " ")}</option>)}</select></label>
        <label><span>Maximum rent</span><input name="max_monthly_rent" inputMode="numeric" placeholder="$8,000" defaultValue={first(search.max_monthly_rent)} /></label>
        <label><span>Minimum score</span><input name="min_overall_score" inputMode="numeric" placeholder="70" defaultValue={first(search.min_overall_score)} /></label>
        <label><span>Sort</span><select name="sort_by" defaultValue={first(search.sort_by) || "recent"}><option value="recent">Most recent</option><option value="score">Highest score</option></select></label>
        <label className="check-label"><input type="checkbox" name="type1_hood" value="true" defaultChecked={first(search.type1_hood) === "true"} /><span>Type 1 only</span></label>
        <button className="primary-button" type="submit">Apply filters</button>
        <Link className="clear-link" href="/listings">Clear</Link>
      </form>
      <div className="results-meta"><p><strong>{listings.length}</strong> opportunities</p><span>Scores with low completeness should be treated as preliminary.</span></div>
      {unavailable ? <div className="notice"><strong>The listing API is unavailable.</strong><span>Start the backend service and refresh.</span></div> : <div className="panel"><ListingTable listings={listings} /></div>}
    </div>
  );
}
