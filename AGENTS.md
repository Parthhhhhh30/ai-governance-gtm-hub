# Agent Instructions — AI Governance GTM Intelligence Hub

Applies to every task using this handoff. Read the accompanying numbered documents before editing files.

## Instruction priority and orchestration

1. Obey system/developer instructions and the user's **pre-existing rules in the destination normal chat** regarding Codex, connected GitHub, PR strategy, deployment platform, secrets, branch protection, commit style, approvals, UI rules and testing. The user explicitly says those settings already exist. **Do not invent or override their content.**
2. Execute the project end-to-end using available connected tools. This handoff is a spec, not a claim that GitHub or deployment has already occurred.
3. Inspect the starter under `starter/ai-governance-gtm-hub/` and preserve working behavior and tests wherever suitable. Choosing a different stack is allowed only where needed for secure, deployable implementation or the destination-chat rules; document decisions.
4. Default repo name, only if not otherwise specified: `ai-governance-gtm-hub`. Do not overwrite unrelated existing files or repositories.
5. Prefer working code and verification over lengthy plans or speculative architecture. Make reasonable decisions without requesting redundant confirmation.
6. If an essential credential, authorization, account permission, or platform capability is missing, continue all feasible work; report the exact blocked operation. Never claim a push/deploy succeeded if it was not verified.

## Non-negotiable product requirements

- A **working** BDR research-to-qualified-meeting pipeline, not static mockups.
- Beautiful, professional, responsive UI with robust empty/error/loading states and keyboard accessibility.
- Include synthetic demonstration data only in public demo; clearly label fabricated companies, people, results and scores.
- Every account buying signal has kind, brief evidence text, source URL, observed date, and human-reviewed status. Unreviewed signals must not contribute to priority scores or customized messaging.
- Clearly distinguish **EU AI Act (legislation)**, **ISO/IEC 42001 (management system standard)**, **NIST AI RMF (voluntary framework)**; official links, suitable discovery questions, context/caveats. No automated legal verdicts.
- Lead/stakeholder mapping and controlled CSV import/export. No unauthorized scraping, real email transmission, or false live-platform integration claims.
- Opt-out/suppression persists and overrides re-import and apparent approval; seed/demo contacts must not be eligible for real outbound export.
- Qualified meeting counted only if first meeting occurred and **a second meeting is booked**; implement date/business-rule validation.
- Account-priority score is a transparent **outreach-priority heuristic**, not an AI risk score, predicted purchase probability, or legal-compliance rating.
- CI and useful automated tests; smoke-tested deployment URL, if deployment possible.

## Public deployment security boundary

Starter uses stdlib `ThreadingHTTPServer`, local SQLite, unauthenticated POST routes, no CSRF or role separation. **Do not make it publicly writable as-is.** For a safe publicly linked portfolio, either:
- Deploy an interactive **demo-only** experience using non-sensitive sample records, with safe isolation/rate limits and no ability to leak data, OR
- Expose a **read-only public showcase** backed by fictional content, retaining fully editable capabilities locally or in a properly authenticated workspace.

Choose the simplest solution that is demonstrably secure and meets the user's deployment conventions. Do not imply a public demo means enterprise-production readiness. Secrets go in platform secret management only; never log/store/commit them.

## Quality and handoff

- Run baseline tests, add tests for new features, run lint/type checks if used, and verify production build/deployment.
- Protect against XSS/HTML injection, CSV formula injection, malformed URLs/input, unauthorized writes, opt-out bypass, duplicate contacts, exposed data exports, and unsafe redirect behavior.
- Commit/push per user's rules. CI should run in GitHub Actions or the user's specified CI platform.
- README must accurately describe implemented integrations (CSV vs API), actual hosting, what works, what requires credentials, security boundaries, exact run/test commands, and synthetic demo data.
- Provide truthful completion report, exact links, evidence of test runs, and any blockers.
