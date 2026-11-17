# AAVA GRC Intelligence

Angular 18 + FastAPI implementation of the AAVA GRC module: regulatory search,
clause-level rule detail, rulebooks, obligations, compliance maps with a D3
Sankey, and regulatory change management.

```
aava-grc-platform/
├── backend/          FastAPI + Python 3.11
│   ├── app/
│   │   ├── api/routes/        catalog · maps · changes
│   │   ├── core/config.py     similarity thresholds (legacy parity)
│   │   ├── data/
│   │   │   ├── datasets/      YOUR four compliance-map datasets
│   │   │   ├── rule_html/     YOUR rule-detail HTML
│   │   │   └── seed/          demo rules, controls, policies, risks, issues
│   │   ├── models/schemas.py  the API contract
│   │   └── services/          sankey · map builder · obligations · change · export
│   │                          semantic_map_service (rule→policy clause) · ask_service (Ask AAVA)
│   └── tests/test_api.py      58 tests, all green
└── frontend/         Angular 18 standalone + Tailwind + d3-sankey
    └── src/app/
        ├── core/              models, api service, shared state
        ├── shared/sankey/     the Sankey component
        └── features/          reg-search · rule-detail · rulebooks ·
                               obligations · library · compliance-map · reg-change
```

## Stakeholder coordination (new)

A change is only handled when the right people know, say so and sign off. `collaboration_service`
turns a change's impact into a RACI routing: the owner of each affected **policy is Accountable**,
owners of affected **controls and open issues are Responsible**, Legal is Consulted, Risk and
Internal Audit are Informed, and the CCO is Accountable when impact ≥ 70. Each person gets a
notification on their channels with a reply-by time; silent Accountable/Responsible people are
escalated to their manager; one thread per change carries comments, `@mentions` and the approval,
and only the named approver can decide. Every notice, message, escalation and decision is written
to the audit trail, which is **hash-chained** (`/api/audit/verify`).

Ask it: *"Who needs to be told about the HKMA change and who must sign it off?"*

## Hierarchy and data quality

`hierarchy_service` places every rule at jurisdiction › regulator › instrument › part and validates
it (duplicate citations, unknown jurisdictions, unrecognised instruments, and, where source markup
exists, that the real Title / Part / Section breadcrumb agrees with the citation). Only rules with
source markup are marked *verified*; the rest are derived from the citation and reported as such.
`map_validator_service` checks compliance-map datasets for dangling links, non-numeric values,
duplicate ids and orphan nodes. The side nav opens to the regulator level; the search table loads
ungrouped and groups by dragging column headings.

## Ask AAVA (new)

`POST /api/ask` takes a question and returns one structured, auditable **run**: the
agents that ran (with tool, knowledge base, output, gate), the evidence, and the answer.
The Angular `/ask` page only renders it; nothing in the client decides anything.

| Scenario | What it shows |
| --- | --- |
| Does our policy cover this rule? | Clause-to-clause mapping with key phrases, semantic bridges ("legal entity customer" ≈ "UBO register"), four-axis score and plain-language reasons |
| Generate the compliance report | Coverage score, coverage matrix (rule matter × country), mitigation plan |
| A regulator changed the rule | Redline, new obligation, impact score, Gate 3 CCO approval |
| Fix a Critical issue | Finds that the policy *contradicts* the rule, seven-step plan with evidence to close |
| Risks above appetite | Residual vs appetite, weak controls, next action |
| Watch | Standing subscription |

`semantic_map_service` scores a policy clause against an obligation:

```
score = .40 concepts + .25 actions + .20 timing + .15 jurisdiction
```

Concepts match by meaning, actions by verb family (a clause that *captures* an owner does
not satisfy a rule that says *verify*), timing as a duration, and a clause that contradicts
the rule is a **Conflict** that always wins selection. Policy clause text lives in
`data/seed/policy_clauses.json` (client-owned content). Modes: **Ask** reads, **Act** drafts and
creates tasks behind a gate, **Watch** subscribes. A write intent escalates Ask to Act and is audited.
Unanswerable questions abstain and are logged as knowledge gaps.

Swap `concept_hits` for embeddings and `route` for an LLM classifier; keep the run shape and the gates.

---

## Run it

Two terminals.

```bash
# 1 — backend  (http://localhost:8000, docs at /docs)
cd backend
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# 2 — frontend (http://localhost:4200)
cd frontend
npm install
npm start
```

`npm start` runs `ng serve --proxy-config proxy.conf.json`, so `/api` is proxied
to port 8000 and there is no CORS to configure in development.

Run the backend tests with `cd backend && pytest -q`.

---

## What was carried over from your existing implementation

Your `script.js` / `d3Sankey.js` pair encodes several decisions that are easy to
lose in a rewrite. They are all preserved, and the tests pin them down.

| Legacy behaviour | Where it lives now |
| --- | --- |
| Dataset shape: a list of layers, each node carrying `other_kps_ds2` | unchanged — `backend/app/data/datasets/*.json` load as-is |
| Unmapped next-layer nodes attached to the first node of the previous layer at **weight 0.001**, so every node still gets a column | `sankey_service.ComplianceGraph._build`, pass 3. Flagged `placeholder: true`; the client draws them at 7% opacity and they never count as coverage |
| Similarity bands at 0.75 / 0.60 / 0.40 → Strong / Partial / Minimal | `core/config.py`, asserted in `test_bands_match_the_legacy_thresholds` |
| Red triangle on `impactedRule` | `SankeyComponent`, now on any impacted node in any layer, not only layer 0 |
| Click a node, light everything connected both ways, dim the rest | `GET /maps/{id}/connected/{uid}` + `applyFocus()` |
| Label before the first column, after every other column | `SankeyComponent` text anchors |
| Export to Excel and PDF | server-side now: `openpyxl` and `reportlab`, so the export contains the whole map rather than what the browser had rendered |
| Dynamic canvas height by node count | `SankeyComponent.render()` |

### Four things that were fixed or added

1. **Duplicate `unique_id` no longer collapses nodes.** `best-execution.json`
   has three rule nodes sharing `pn0`; the old `nodeMap[x.unique_id]` kept only
   the last. Every node now keeps its own uid and the collision is reported at
   `GET /maps/{id}/summary` → `duplicateSourceIds`.
2. **Risks and Issues are first-class layers.** A generated map runs
   Rule → Obligation → Policy → Control → Risk → Issue. A risk above appetite
   with no issue raised gets an explicit terminal node, so a governance gap is
   visible instead of being an absence.
3. **Drill-down.** Clicking a node returns the fully traced paths through it
   (`GET /maps/{id}/drill/{uid}`), which is the grouped parent-to-child table
   under the diagram.
4. **The clause tree is server-side** — see below.

---

## Rule detail: the clause tree

Your rule-detail page shipped HTML and rebuilt the hierarchy in jQuery by
string-matching dotted element ids. That works on the page, but the structure
only exists in the DOM, so nothing else can use it.

`rule_detail_service.py` parses the same markup **once, on the server**, into a
clause tree:

```
12:8.0.2.1.3.0.1.12_b          (b) Preservation of records
  12:8.0.2.1.3.0.1.12_b.1      (1) Applications. For 25 months …
    12:8.0.2.1.3.0.1.12_b.1.i  (i) Any application that it receives …
```

It keeps what the HTML had — the Title / Volume / Chapter / Part / Section
breadcrumb, the part authority with its USC links, the `bg-warning` flag, the
`[76 FR 79445 …]` amendment history — and adds what it only implied:

- `parentId` / `childIds`, so selection is exact rather than a prefix match;
- **trigger phrases** (`shall`, `must`, `may`) with character offsets and a duty
  classification — this is what the obligation extractor keys on;
- **deadlines** (`For 25 months`, `within 30 days`) as their own spans;
- **cross references** (`§ 1002.5(a)(4)`) detected and made clickable.

Because the clause id is now a stable address, the same id anchors the
obligation it produced, the node in a compliance map, and the before/after in a
change diff. That is what makes clause-level traceability possible rather than
section-level.

To add another rule's source HTML: drop it in `backend/app/data/rule_html/<key>.html`
and set `detailKey: "<key>"` on the rule in `app/data/seed/rules.json`. Rules
without one fall back to a single synthetic clause, so the client only ever
implements one view.

---

## Regulatory change management

`GET /api/changes` is the horizon-scan feed; each item carries a clause-level
diff. `GET /api/changes/{id}/impact` scores it on three separate axes rather
than one opaque number, because the reviewer has to be able to argue with it:

- **materiality** — how severe the affected rules are
- **gapSeverity** — how weak the current coverage of those rules is
- **urgency** — how little time is left before the effective date

`impactScore = 0.40·materiality + 0.35·gapSeverity + 0.25·urgency`

The response also lists the affected obligations, policies, controls, risks and
open issues, plus recommended actions with an owner and a reason. Status moves
are written to the audit trail (`GET /api/audit`).

---

## API surface

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/reference` | jurisdictions, frameworks, rule matters, rule types, domain tabs |
| GET | `/api/search` | `q`, `juris`, `framework`, `ruleMatter`, `ruleType` → hits + keyword map + concepts |
| GET | `/api/rules/{id}` | one rule |
| GET | `/api/rules/{id}/detail` | breadcrumb, authority, clause tree, spans, history |
| GET | `/api/rules/{id}/detail/clause/{clauseId}/family` | ancestors + descendants |
| GET/POST | `/api/rulebooks` | list / create |
| POST | `/api/rulebooks/seed` | one-click cross-border rulebook |
| GET | `/api/obligations` | by `rulebookId` or `ruleId` |
| GET | `/api/obligations/{id}/validate` | deterministic checks + `gate: auto\|human` |
| POST | `/api/obligations/{id}/approve` | sign-off, audited |
| GET | `/api/controls` `/policies` `/risks` `/issues` | the library |
| GET | `/api/maps` | imported datasets + generated maps |
| POST | `/api/maps/build` | build from a rulebook |
| GET | `/api/maps/{id}` | the full graph (`?layer=N` hides a layer) |
| GET | `/api/maps/{id}/summary` | coverage by layer + duplicate source ids |
| GET | `/api/maps/{id}/connected/{uid}` | the connected sub-graph |
| GET | `/api/maps/{id}/drill/{uid}` | traced paths through a node |
| GET | `/api/maps/{id}/export.csv\|xlsx\|pdf` | exports |
| GET | `/api/changes` · `/pipeline` · `/{id}/impact` | reg change |
| POST | `/api/changes/{id}/status` | move it through the pipeline |
| GET | `/api/sources` | the content source registry (`?juris=` / `?licence=`) |
| GET | `/api/audit` | who approved what, when |
| POST | `/api/ask` | Ask AAVA run: `{question, mode}` → steps, evidence, answer |
| POST | `/api/ask/approve` | record a gate decision (audited) |
| GET | `/api/hierarchy` · `/api/hierarchy/validate` | jurisdiction › regulator › instrument › part › rule tree; consistency check |
| GET | `/api/rules/{id}/path` | breadcrumb for one rule |
| GET | `/api/maps/{id}/validate` | data-quality report for a compliance-map dataset |
| GET | `/api/audit/verify` | re-computes the audit hash chain; reports the first broken entry |
| GET | `/api/stakeholders` | people, roles, channels, managers |
| GET | `/api/changes/{id}/routing` | who must hear about a change, with RACI and reasons |
| POST | `/api/changes/{id}/notify` | send the notifications (idempotent), open the thread |
| GET | `/api/changes/{id}/coordination` | thread, approval state and notification status |
| POST | `/api/notifications/{id}/ack` · `/api/changes/{id}/escalate` | acknowledge · escalate silent owners to their manager |
| POST | `/api/threads/{subject}/comments` | comment; `@Legal` or `@Meera` notifies that person |
| POST | `/api/threads/{subject}/approval` · `/decision` | request approval · approve / reject / request changes (note required, only named approvers) |
| GET | `/api/ask/scenarios` | the seven demo prompts |
| POST | `/api/map/obligation` | one rule → best policy clause, with reasons |
| GET | `/api/policies/{id}/clauses` | clause-level policy text |

---

## Where the content comes from

`backend/app/data/seed/sources.json` is the content engine's plan of record,
served at `GET /api/sources`. It separates three sourcing problems that are
easy to conflate:

| Content | Who owns it | How we get it |
| --- | --- | --- |
| Regulations and guidance | The regulator, publicly | Crawl or licence. This is the build |
| Control frameworks | Standards bodies | Some free and machine-readable, some must be bought |
| Policies, controls, risks, issues | **The client** | Ingested from their GRC tool or SharePoint — never sourced externally |

Of the 33 regulatory sources registered, **9 have real machine-readable access
and 24 are crawlers you have to write and maintain**:

| Source | Access | Licence |
| --- | --- | --- |
| [eCFR](https://www.ecfr.gov/developers) | REST API + bulk XML | public domain |
| [Federal Register](https://www.federalregister.gov/developers/api/v1) | REST API | public domain |
| [GovInfo](https://www.govinfo.gov/developers) | REST API (free key) | public domain |
| [legislation.gov.uk](https://www.legislation.gov.uk/developer) | REST API, CLML XML | Open Government Licence |
| [EUR-Lex / Cellar](https://eur-lex.europa.eu/content/help/data-reuse/reuse-contents-eurlex-details.html) | SPARQL + REST | re-use with attribution |
| [NIST OSCAL content](https://github.com/usnistgov/oscal-content) | JSON / XML / YAML | public domain |
| [Secure Controls Framework](https://securecontrolsframework.com/scf-download) | XLSX download | free, ~1,200 controls pre-mapped to 250+ frameworks |

Everything else — FCA, PRA, RBI, SEBI, HKMA, MAS, JFSA, PBoC, CAC, FSC, SAMA,
SARB, FIC, CBN — is HTML and PDF. The US, UK-legislation, EU and NIST endpoints
above were confirmed on 13 November 2026; the APAC and Africa entries in
`sources.json` are marked `verified: false` and must be checked source by
source before a crawler is written against them.

### The licensing field, and why it matters

Each entry carries a `licence` that the ingest pipeline must honour:

- `public-domain` — store and display freely
- `open-attribution` — store and display with attribution
- `permission-required` — **public but governed.** The FCA Handbook is the
  live example: re-use runs through a formal request under the Re-use of Public
  Sector Information Regulations 2015, the FCA advises of applicable charges,
  and Register extracts need a licence and a fee. Treat it as a lead-time item
- `licensed` — ISO/IEC 27002, COBIT, COSO. **Never redistribute the text in the
  product.** Map to the control identifier, show the client their own wording,
  and let the client hold the licence
- `client-owned` — ingested under the customer contract only

`GET /api/sources?licence=permission-required` returns exactly the set that
needs a legal conversation before a crawler is pointed at it. Two tests pin
the FCA and ISO positions down so a future refactor cannot quietly relax them.

---

## Where to plug the real thing in

Everything below is deliberately isolated so you can replace one piece at a time.

| Swap this | For this | File |
| --- | --- | --- |
| `_score()` keyword scoring | hybrid vector + keyword retrieval | `services/search_service.py` |
| `extract()` regex extraction | an LLM call — keep the output shape and the `validate()` checks, they decide the human gate | `services/obligation_service.py` |
| matter + jurisdiction matching | embedding similarity, then an LLM coverage judge against a written rubric | `services/map_builder_service.py` |
| `store.py` JSON loaders | SQLAlchemy repositories | `services/store.py` |
| the static `changes.json` feed | the horizon-scan crawler | `services/change_service.py` |

The scoring in `map_builder_service.build()` is intentionally explainable:

```
0.50  the policy/control addresses the same rule matter
+0.25 it is deployed in the rule's jurisdiction
+0.10 the control was tested and found effective
+0.05 the control is automated
```

A policy or control that addresses the matter but is **not deployed in that
jurisdiction** produces no link at all. That is on purpose — it is the most
common real gap, and scoring it as a weak match hides it.

---

## Notes

- The seed data is illustrative, for demonstrating the platform. It is not legal
  content and must not be relied on as a statement of any regulation.
- `large-volume.json` (109 rules × 1,000 policies, one real match) is the layout
  stress case. It renders 1,109 nodes; node padding drops automatically above
  400 nodes.
- Every AI-proposed obligation and mapping carries a confidence score and is
  subject to reviewer sign-off before it is treated as evidence. The gates are
  the product, not a formality.


## Added in the latest update
- **Inbox and bell** (`/inbox`): notifications, comments with @mentions, and approvals per regulatory change. Unread count shows on the bell in the top bar.
- **Scope** (`/scope`): choose the rules, policies and controls you care about; add your own. Endpoints `/api/scope/*`.
- **Assess** (`/api/assess`, `/api/assess/report.html`), **Act** (`/api/actions`, `/api/actions/fix-plan`), **Watch** (`/api/posture`), **Share** (`/api/shares`, `/api/shares/{id}/verify`).
- **Compliance map**: Download mapping (CSV), Download impact and mitigation plan (`/api/maps/{id}/export-plan.html`), and Rebuild.
- Pinning uses a pin icon; the table header no longer floats over the first row.

## Four map views, standards and industries (latest)
- **Compliance map views**: Layered trace (default), Coverage matrix, Roll-up and Flow, with a detail table below. Drag any column heading into *Group by*; sort, filter and download the table as CSV. Component: `features/compliance-map/map-views.component.ts`.
- **Standards and certifications** (`/api/frameworks`, `/api/domains`, `POST /api/assess/framework`, `POST /api/assess/framework/report.html`): SOC 2, ISO 9001, ISO 27001, PCI DSS, HIPAA, GDPR, SOX, ISO 22301, food and product safety, logistics and cold chain, e-commerce, ISO 14001 and ESG. Each criterion lists what an auditor will ask for. Result is a readiness view, not an audit opinion.
- **Industries**: banking, insurance, retail, e-commerce, supply chain, logistics, healthcare, CPG, technology, manufacturing. Each lists the usual standards, regulators and what to watch. Data lives in `data/seed/packs.json`.
- **Subject kinds**: application, product, platform, process, vendor, site, business unit, whole organisation, industry. A framework subject id is `fw:<framework>|<name>|<kind>`, so share, fix plan and report all work for it.
- Extra illustrative evidence for the new matters (access control, change management, backup, quality, CAPA, product safety, PHI, and more) was added to the seed data. Scope a subject to the controls that really apply to it before relying on a score.

## Roles, named approvers and the audit room
- **Acting as** switcher in the top bar. Every API call carries `X-AAVA-User` (in production this comes from single sign-on). The server enforces it; the UI shows the server's reason when a check says no.
- **Roles**: administrator, CCO, compliance officer, risk manager, control or policy owner, internal auditor, external auditor, regulator, executive. Role = what you can do (`/api/access/roles`).
- **Named approvers**: Gate 1, 2 and 3 are attributes of a person (`PUT /api/access/users/{id}`, administrator only). To approve you need a role that can approve, a name on the gate, and you must not be the person who raised it.
- **Guard rails**: at least one administrator and one Gate 3 approver always exist; auditors cannot be named approvers; a comment or decision can only be recorded as yourself; audit entries record the actor and role.
- **Audit room**: external auditors and regulators see only reports released to them (`GET /api/shares`). The demo has a dedicated Audit room page. The Angular app enforces the same rule on the server but has no dedicated page yet.
- Page: `/access` (Angular) and *Roles and access* (demo).

## Worked example (leadership story)
One regulatory change (HKMA AML/CFT amendment, CHG-01) followed end to end across Watch, Ask and Act, with a 90-second narration, before/after targets, USP and the problems the platform solves. Content lives in `backend/app/data/seed/story.json`, served at `GET /api/story`, shown at `/story` in the Angular app and as "Worked example" in the single-file demo. All names and figures are illustrative.
