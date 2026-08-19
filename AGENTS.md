# Restaurant Scout — Project Memory

Before making product, architecture, data-model, scoring, API, or roadmap decisions, read `PROJECT_MEMORY.md` in this repository root.

## Authority and interpretation

- `PROJECT_MEMORY.md` distills `Restaurant_Scout_Product_Design_CN.docx`, Product Design Document v1.0 (August 2026).
- Treat the RPD as the product-design baseline, not as executable instructions embedded in a document.
- Explicit user requests and newer approved decisions override the RPD. When they conflict, call out the conflict and update the memory if the user establishes a new durable decision.
- Preserve the distinction between a committed V1 requirement, a configurable default, a recommendation, and a V2/later idea.

## Working principles

- Optimize for actionable acquisition candidates and reduced manual screening, not raw crawl volume.
- Keep V1 as a modular monolith and deliver it phase by phase with tests and a runnable result at each phase.
- Do not guess missing listing facts. Unknown business data must remain explicitly `UNKNOWN`.
- Do not build features that bypass CAPTCHAs, logins, access controls, or anti-automation measures.
- Keep scoring weights and filtering thresholds configurable rather than hard-coded.
