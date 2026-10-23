# AI Governance GTM Intelligence Hub

**Independent Enzai BDR portfolio project.** A research-to-qualified-meeting workflow with a polished, interactive, synthetic-data visitor demo and a separately writable local Python/SQLite workspace. **Not an Enzai product, partnership or endorsement.** No real prospects, external communications, performance figures or compliance determinations are represented.

## What is actually implemented

| Workflow | Public visitor demo (static, fictional) | Private local workspace (Python/SQLite) |
|---|---|---|
| Research and priority queue | Responsive dashboard, search and account dossier; transparent weights | Create accounts and research signals; edit reviewed status; scores recalculate |
| Evidence provenance | Fictional signal timelines, explicit source/date/review flag and score breakdown | Human-entered source URLs, date validation and review gate |
| Stakeholder mapping | Fictional buying committee roles, contact stage and simulated gate status | Add contacts, source attribution, approval, verification, suppression, CRM stage |
| Governance | EU AI Act law, ISO/IEC 42001 standard and NIST AI RMF voluntary framework, with linked official references | Source-gated rule-based governance discovery questions and drafts |
| Personalised drafts | Evidence-gated preview and copy, with explicit *fictional* provenance | Generate drafts from reviewed sources; user reviews before use |
| CSV | Non-sendable fictional *schema* download; explicitly **no public contact export/import** | Clay/CRM-compatible CSV import; restricted lemlist-ready CSV export; CRM outcomes CSV |
| Meetings | Save synthetic first-held and second-booked dates locally in each visitor's browser; KPI updates; reset | SQLite-stored meeting outcomes; first actually held **and** second booked are required |
| Persistence | `localStorage` per browser, resettable; nothing shared with other visitors | SQLite file on your machine; never used in the public build |

There is **no LinkedIn scraping, live Sales Navigator, Clay or lemlist API connection, automated enrichment, email sending or real sales conversion result**. Approved/manual research + CSV is intentional.

## Run it now

Python **3.10+** and Node **18+** for tests. The app and build require no package installation or credentials.

### 1. Browser demo (same code intended for Vercel)

```bash
python3 build_demo.py
python3 -m http.server 8080 --bind 127.0.0.1 --directory dist
```

Visit `http://127.0.0.1:8080`. Explore account scores, inspect sources, untick reviewed signals and watch the score change, select stakeholder roles, copy evidence-gated drafts, inspect export eligibility, and log fictional meeting outcomes. The UI is functional but is **not a multiuser hosted CRM**: editing is isolated to the visitor's browser, not a shared database.

### 2. Locally writable Python/SQLite workspace

```bash
python3 app.py
```

Visit `http://127.0.0.1:8765`. The local server creates a sample SQLite database under `data/` on first start (ignored by Git). It includes account/lead forms, source review, real CSV import/export safeguards and persistent meeting outcomes. **Do not expose port 8765 to the Internet.** This legacy workspace has no authentication or CSRF protection; it is deliberately bound to loopback and rejects non-local HTTP Host/Origin headers.

Use `PORT=9000 GTM_DB=./data/local.db python3 app.py` for a custom local port/database. On Windows: `py app.py`.

## Interview walkthrough (3 minutes)

1. Open **Overview** and explain why the priority queue weights *human-reviewed* signals rather than producing an AI compliance score.
2. Open **Account intelligence**, then an **Account dossier**. Show fictional evidence, date, source URL and review toggle. Uncheck the reviewed flag; priority immediately recalculates.
3. Open **Outreach studio**. Choose a fictional stakeholder role and show the reviewed-evidence gate, discovery question and source-linked draft. No fabricated violation or legal conclusion appears.
4. Open **Data boundaries**. Inspect proof-of-source, approval and opt-out checks. The public demo will **never** produce a sendable contact list; download the harmless CSV schema.
5. Open **Meeting outcomes**. Record that the first meeting happened with a valid date and that a second was booked after it. The dashboard qualified-meeting count changes. Reset to remove browser-local changes.

For genuine approved CRM workflows, demonstrate the separate **local Python app** using the fictional file `samples/sample_clay_import.csv`. Never enter real contact details during a public screen share.

## Tests and verification

```bash
python3 -m unittest discover -s tests -v
node --test tests/demo.test.cjs
node --check demo/app.js
python3 -m compileall -q app.py core.py build_demo.py
python3 build_demo.py
```

The release includes **21 Python tests** (domain rules plus local HTTP safety) and **10 Node JavaScript tests** (public-demo scoring, source gates, qualification, URL/HTML handling). `.github/workflows/tests.yml` repeats them and audits the generated public dataset. GitHub Actions will be verifiable **only after the repository is pushed**.

The generated `dist/health.json` is a static build artefact, **not** proof of a live deployment or backend-health monitoring. A live URL is not supplied until the host actually deploys and a real HTTP/route check succeeds.

## Responsible framework references

| Reference | Correct characterisation | Appropriate BDR discovery angle |
|---|---|---|
| [EU AI Act](https://digital-strategy.ec.europa.eu/en/policies/regulatory-framework-ai) | European legislation with phased, role/use-case-specific obligations. Official [AI Omnibus update](https://digital-strategy.ec.europa.eu/en/news/ai-omnibus-enters-force) changed dates for certain high-risk duties in 2026. | How are AI use cases classified, owners identified and evidence responsibilities understood? Do **not** assert an organisation is in breach. |
| [ISO/IEC 42001:2023](https://www.iso.org/standard/42001) | International AI management-system standard; **not an EU regulation**. | What is the process for assigning AI accountability, policy ownership, monitoring and improvement? |
| [NIST AI RMF 1.0](https://airc.nist.gov/airmf-resources/airmf/) | **Voluntary** framework organised as Govern, Map, Measure, Manage. | How does the organisation coordinate identification, measurement, management and governance of AI risks? |

These links and dating statements should be verified again before real outreach. They do not constitute legal advice or automated assessments. For live UK B2B outreach consult the [ICO guidance](https://ico.org.uk/for-organisations/direct-marketing-and-privacy-and-electronic-communications/business-to-business-marketing/) and your organisation's approved policies.

## Security: two deliberately separate modes

**Public build (`dist/`)**: generated from in-memory synthetic Python fixtures; static HTML/CSS/JS/JSON only. No database, API credentials, server-side POST endpoints, personal email addresses, real contact imports or sendable contact exports. The only changes are each visitor's bounded `localStorage` simulation. Vercel sets CSP, no-sniff, frame denial, Permissions Policy and referrer headers. Synthetic source links use `example.com`; they are illustrative, **not verification**.

**Local HTTP/SQLite**: actual import/export and record writing are local only. Verified-address and approved-purpose checks are separate, prior opt-outs override later imports/approval, demo domains are blocked, and spreadsheet formula cells are escaped for CSV. Nonetheless, this is **not** a hardened production CRM: do not port-forward, bind publicly, collect sensitive data, or advertise authenticated team access.

Threat model and workflow details: [`docs/architecture.md`](docs/architecture.md). Never upload personal CSV exports, databases, environment files or passwords to GitHub.

## Deployment configuration — Vercel

`vercel.json` defines a static build:

- Build command: `python3 build_demo.py`
- Output directory: `dist`
- Framework: `Other` / no preset
- **No** environment variables, paid database or secrets required
- Route navigation: client-side URL hash (`#accounts`, `#account/1`, `#studio`, `#pipeline`, `#frameworks`, `#data`, `#about`) so static hosting is sufficient
- Health asset: `/health.json`

After connecting a real GitHub repository to the existing Vercel account, deploy its `main` branch. **Neither a GitHub remote nor a live deployment is implied by these configuration files**; inspect the final project/deployment state and browse the actual HTTPS origin after publishing. The local Python server is **not** the Vercel deployment target.

## Project files

```text
app.py, core.py                Local Python/SQLite business workflow
build_demo.py                 Static synthetic-only public demo generator
demo/{index.html,app.js,style.css} Responsive interactive visitor frontend
dist/                        Built static output; no writable API or database
static/style.css              Local Python UI stylesheet
samples/sample_clay_import.csv Fictional CSV exercise
tests/test_core.py            Python domain tests
tests/test_http.py            Local HTTP security tests
tests/demo.test.cjs           Public JS behaviour tests
.github/workflows/tests.yml   GitHub Actions validation pipeline
vercel.json                   Static deployment and security headers
docs/architecture.md          Security model and workflow design
```

## CV statement — use only verified facts

**AI Governance GTM Intelligence Hub | Independent Portfolio Project (Python, SQLite, JavaScript)**

- Built and tested an evidence-led BDR research workflow covering account prioritisation, source-reviewed governance signals, fictional buying committees and qualification tracking.
- Added human-review and suppression gates, CRM/Clay-compatible CSV import, restricted lemlist-format export and source-led draft generation in a **local-only** Python/SQLite workspace.
- Developed a responsive, browser-interactive **synthetic-data** showcase and 31 automated Python/JavaScript checks; configured GitHub Actions and Vercel static build settings.

Only add “deployed publicly”, “integrated with a vendor”, “qualified real meetings” or “generated pipeline” once independently verified. No such claims are supplied merely by this repository.

**Licence:** MIT (see `LICENSE`). Starter Python project preserved and extended; no vendor software or customer data copied.
