# Architecture, acceptance boundaries, and risk decisions

## Split architecture

The primary deliverable has **two deliberately different environments**:

1. **Browser demo (`demo/`, built via `build_demo.py` to `dist/`).** The generator calls the original Python domain functions against `:memory:` SQLite and serialises only a synthetic, minimised data projection. Vercel serves static HTML/CSS/JS/JSON. There is no backend to write to, no shared client data, no contact imports, and no sendable export. Visitor choices are stored locally in their own browser and can be reset.
2. **Private/local workspace (`app.py`, `core.py`, `static/`).** Python standard-library HTTP handling plus on-disk SQLite. Writable accounts, researched signals, stakeholders and meeting outcomes; approved CSV import/export. Binds to `127.0.0.1`; unsafe external Host/Origin rejected. **No authentication or CSRF** means it is **not fit for public hosting**.

This avoids pretending an unauthenticated SQLite CRUD demo is a secure hosted multiuser SaaS. The trade-off is that public visitors cannot create shared records or import contacts; they can still demonstrate the core research -> committee -> governance hypothesis -> draft -> permission checks -> simulated qualification workflow.

## Dataflow and controls

`Account -> reviewed source-linked signal -> explainable weighted account score -> fictional / permitted stakeholder -> framework-aware discovery question -> source-based draft -> eligibility check -> local CSV (only authorised contacts) -> meeting outcome`.

- Source is researcher-entered, **not automatically verified**. Human-reviewed is an attestation, not a guarantee of truth.
- Only one signal per type contributes to priority; signals decay with age. Priority is neither a propensity model nor a legal-compliance score.
- Unreviewed signals earn **zero** score and do not support an email draft.
- Buying roles and contact identities are clearly fictional on public pages.
- Drafts never assert that a customer is noncompliant, certified, or ready to buy. Source statements are explicitly labelled reported and fictional in the public environment.
- Suppression is independent of and overrides import, address verification, or outreach approval; `.example` and reserved sample addresses never become export eligible.
- A *qualified* meeting requires a held first meeting with a valid non-future date **and** a second meeting booked on a later date; a merely scheduled first meeting never counts.
- Real sending happens nowhere in the application. lemlist export is CSV-only and requires private/local approval controls.

## Public build's security properties

- Only the synthetic `dist/{index.html,style.css,app.js,data.json,health.json}` is published. No `.db`, `.env`, source CRM, or personal emails are included.
- No public write API, authentication cookie, open proxy, native SDK, or secret store exists. Per-visitor changes are constrained to fictional IDs/flags/dates with a versioned `localStorage` key. This is **not a robust security boundary for real personal data**, which is never loaded.
- Strings interpolated into HTML are escaped. Outbound hyperlinks are constrained to HTTPS. Public CSV contains a fictional schema, never approved real recipients.
- Vercel header configuration includes CSP, clickjacking prevention, nosniff, Permissions Policy, and referrer limits.
- Build determinism: Python source provides the signal weights/framework questions and creates the same fictional account set; no live scraping or network dependency at build time. Date changes may change decayed scores, which is disclosed as a heuristic.

## Local HTTP constraints and residual risk

- The local Python app handles writes and CSV downloads **without login or anti-CSRF tokens**. It is bound to loopback with external Host/Origin rejection and should be treated as a single-user development tool on a trusted machine.
- Source URL validation rejects private/loopback hosts, but the code does **not fetch** input URLs. Escaped HTML and spreadsheet-formula handling reduce injection risk; they do not turn the system into an audited production-grade CRM.
- Do not save real contact data in a shared workstation, sync its SQLite file to a public drive, or advertise legal marketing compliance. Verified, approved, and not suppressed are *technical* export gates, not independent legal determinations.

## Governance wording

- EU AI Act: law. Check actual role, AI system scope and **current, amended** dates before asking a question; no automatic legal conclusion.
- ISO/IEC 42001:2023: AI management-system standard, not an EU legal mandate.
- NIST AI RMF 1.0: voluntary framework (Govern / Map / Measure / Manage), not a statutory certification requirement.
- All three guide *hypothesis and questions*, not legal advice, conformity assessments, or certification evidence.

## Acceptance verification and release limitations

- Python domain and local HTTP tests: `python3 -m unittest discover -s tests -v`.
- JS business-rule tests: `node --test tests/demo.test.cjs`.
- Build: `python3 build_demo.py` followed by a fixture and output audit in GitHub Actions.
- Screenshots and Playwright navigation checked against local compiled static assets; **not** a deployed web host. Validate the actual domain, CSP, mobile layout, JS console, routes and interaction after Vercel deployment.
- GitHub Actions configuration exists but **passing hosted CI requires a successful push**. A Vercel build command is not evidence of a live deployment.
