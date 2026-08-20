# BizBuySell and LoopNet Source Feasibility Audit

Audit date: 2026-08-19

This is an engineering and product-access assessment, not legal advice. Restaurant
Scout must not activate either integration until the operator has permission that
specifically covers automated access and storage in the Restaurant Scout database.

## Executive decision

| Source | Public-page crawl | Authorized feed/export adapter | Current status |
|---|---|---|---|
| BizBuySell | Not approved for V1 | Implemented | Disabled pending permission and feed |
| LoopNet | Not approved for V1 | Implemented | Disabled pending permission and feed |

Both brands are operated by CoStar Realty Information, Inc. Their current official
terms prohibit, without express written permission, scraping or using robots/data
extraction tools to monitor or copy the product. The terms also prohibit storing or
exporting product content into a database or other software program. A permissive
robots path is therefore not sufficient authorization to build a listing database.

Official sources reviewed:

- [BizBuySell robots.txt](https://www.bizbuysell.com/robots.txt)
- [BizBuySell Terms of Use](https://www.bizbuysell.com/terms-of-use/)
- [LoopNet robots.txt](https://www.loopnet.com/robots.txt)
- [LoopNet Terms of Use](https://www.loopnet.com/solutions/LoopNetTerms-of-Use)

## BizBuySell findings

- The general robots rules do not disallow every public listing path and specify a
  crawl delay, but they block several member, broker, tracking, handler, and API
  paths.
- The Terms of Use are the controlling implementation boundary. They prohibit
  scraping, automatic or manual extraction for monitoring/copying, and storage in a
  database without express written permission.
- No public buyer-facing listing API or feed with storage rights was identified in
  the official materials reviewed.

Decision: do not crawl search or detail pages. `BizBuySellCollector` accepts only an
explicitly configured JSON feed or export obtained under separate authorization.
Until that authorization exists, BizBuySell opportunities may be saved only as
link-only `ExternalLead` records for operator review. Restaurant Scout does not open
the source page or copy its listing facts.

## LoopNet findings

- The robots rules disallow query-string URLs, location, map, search-service, and
  several other routes while exposing listing sitemaps.
- Sitemap visibility does not grant data reuse rights. The official Terms of Use
  prohibit scraping, robots/data extraction, database creation, and storing or
  exporting product content without express written permission.
- CoStar offers commercial products and licensed access, but no public listing API
  with general-purpose ingestion and storage rights was identified in the official
  materials reviewed.

Decision: do not crawl search pages, detail pages, sitemaps, maps, or internal
services. `LoopNetCollector` accepts only an explicitly configured JSON feed or
export obtained under separate authorization.
Until that authorization exists, LoopNet opportunities may be saved only as
link-only `ExternalLead` records for operator review. They remain outside canonical
listing scoring and source-history tracking.

## Authorized feed contract

The configured URL must return `application/json`. The document may be a JSON list or
an object with an `items` list:

```json
{
  "items": [
    {
      "external_id": "source-stable-id",
      "source_url": "https://www.bizbuysell.com/Business-Opportunity/example/123/",
      "collected_at": "2026-08-19T12:00:00Z",
      "payload": {
        "title": "Restaurant asset sale",
        "description": "Facts supplied by the authorized feed",
        "address": null,
        "city": "San Mateo",
        "asking_price": "250000",
        "monthly_rent": null,
        "size_sqft": null,
        "type1_hood": null,
        "market_status": "active"
      }
    }
  ]
}
```

Unknown facts remain `null`; the adapter does not infer them. Items outside the six
configured P0 cities and items without an explicit positive food-service classification
are skipped. Known non-food categories are explicitly rejected. Source URLs must belong
to the corresponding source domain. A bearer token is optional and is read only from
environment configuration.

`*_FEED_IS_COMPLETE` must remain `false` unless the provider guarantees that every
run is a complete current snapshot. Only a complete feed may reconcile missing source
records and eventually mark them off market.

## Activation checklist

1. Obtain written permission or a contract covering automated access and database
   storage for the intended internal use.
2. Obtain or build an authorized JSON feed/export matching the contract above.
3. Keep `*_DATA_LICENSE_CONFIRMED=false` until steps 1 and 2 are complete.
4. Test the feed with mocked or non-production data before enabling scheduling.
5. Set `*_FEED_IS_COMPLETE=true` only when completeness is contractually and
   technically guaranteed.
6. Record the permission owner, effective date, and any retention or redistribution
   restrictions outside the public repository.
