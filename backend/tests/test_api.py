"""End-to-end checks against the bundled datasets.

Run:  pytest -q
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import sankey_service, store

client = TestClient(app)


@pytest.fixture(autouse=True)
def _clean():
    store.reset()
    yield


def test_health():
    assert client.get("/health").json()["status"] == "ok"


def test_reference_has_taxonomy():
    r = client.get("/api/reference").json()
    assert "AML / CFT" in r["ruleMatters"]
    assert "Master Direction" in r["ruleTypes"]
    assert r["domains"][1]["enabled"] is False          # privacy stays disabled
    assert r["counts"]["rules"] > 50


def test_search_filters_and_keyword_map():
    r = client.get("/api/search", params={"q": "verify beneficial owner before onboarding"}).json()
    assert r["total"] > 0
    assert any(h["rule"]["cite"] == "31 CFR 1010.230" for h in r["results"])
    assert r["keywordMap"], "the keyword map drives the concept graph"
    assert any(c["root"] == "beneficial owner" for c in r["concepts"])

    filtered = client.get("/api/search", params={"ruleMatter": "KYC and CDD", "ruleType": "Regulation"}).json()
    assert all(h["rule"]["ruleMatter"] == "KYC and CDD" for h in filtered["results"])
    assert all(h["rule"]["ruleType"] == "Regulation" for h in filtered["results"])


def test_obligation_extraction_is_traceable():
    rule = next(r for r in store.rules() if r["cite"] == "31 CFR 1010.230")
    obs = client.get("/api/obligations", params={"ruleId": rule["id"]}).json()
    assert obs
    first = obs[0]
    assert first["trigger"].lower() in rule["text"].lower()
    assert first["confidence"] >= 40
    v = client.get(f'/api/obligations/{first["id"]}/validate').json()
    assert set(v["checks"]) >= {"citationPresent", "modalPresent"}
    assert v["gate"] in ("auto", "human")


# --------------------------------------------------------------- rule detail
def test_rule_detail_parses_the_legacy_html():
    rule = next(r for r in store.rules() if r["cite"] == "12 CFR 1002.12")
    d = client.get(f'/api/rules/{rule["id"]}/detail').json()
    levels = [b["level"] for b in d["breadcrumb"]]
    assert levels == ["title", "volume", "chapter", "part", "section"]
    assert "1002.12" in d["section"]
    assert d["authority"]["links"], "part authority USC links are kept"
    assert d["stats"]["clauses"] > 15
    assert d["stats"]["dutyClauses"] > 0
    assert any(c["flagged"] for c in d["clauses"])


def test_clause_family_does_not_confuse_i_and_ii():
    rule = next(r for r in store.rules() if r["cite"] == "12 CFR 1002.12")
    rid = rule["id"]
    fam = client.get(f"/api/rules/{rid}/detail/clause/12:8.0.2.1.3.0.1.12_b.1.i/family").json()
    # _b.1.ii must NOT be picked up as a descendant of _b.1.i
    assert not any(x.endswith("_b.1.ii") for x in fam["descendants"])
    assert "12:8.0.2.1.3.0.1.12_b.1" in fam["ancestors"]
    assert "12:8.0.2.1.3.0.1.12_b" in fam["ancestors"]


# ------------------------------------------------------------ imported maps
@pytest.mark.parametrize(
    "map_id,layer_types",
    [
        ("code-of-ethics", ["Rule", "Policy", "Control", "Issue"]),
        ("anti-corruption", ["Rule Book", "Policy", "Control"]),
        ("best-execution", ["Rule Book", "Policy"]),
        ("large-volume", ["Rule Book", "Policy"]),
    ],
)
def test_bundled_datasets_load(map_id, layer_types):
    g = client.get(f"/api/maps/{map_id}").json()
    assert [l["type"] for l in g["layers"]] == layer_types
    assert g["nodes"] and g["links"]


def test_placeholder_links_keep_every_node_in_its_column():
    """The legacy 0.001 trick: 1,000 policies, one real match, all laid out."""
    g = client.get("/api/maps/large-volume").json()
    policies = [n for n in g["nodes"] if n["layer"] == 1]
    assert len(policies) == 1000
    targeted = {l["target"] for l in g["links"]}
    assert all(p["uid"] in targeted for p in policies), "every node needs an inbound link"
    real = [l for l in g["links"] if not l["placeholder"]]
    assert len(real) == 1
    assert all(l["value"] == pytest.approx(0.001) for l in g["links"] if l["placeholder"])


def test_duplicate_source_ids_are_not_collapsed():
    """best-execution has three rule nodes sharing unique_id 'pn0'."""
    s = client.get("/api/maps/best-execution/summary").json()
    assert "pn0" in s["duplicateSourceIds"]
    g = sankey_service.get_graph("best-execution")
    pn0 = [n for n in g.nodes if n.sourceId == "pn0" and n.layer == 0]
    assert len(pn0) >= 3, "duplicates must each keep a node"
    assert len({n.uid for n in pn0}) == len(pn0), "uids must stay distinct"


def test_bands_match_the_legacy_thresholds():
    g = sankey_service.get_graph("code-of-ethics")
    for link in g.links:
        if link.placeholder:
            continue
        if link.value >= 0.75:
            assert link.band == "Strong"
        elif link.value >= 0.60:
            assert link.band == "Partial"
        elif link.value >= 0.40:
            assert link.band == "Minimal"


def test_connected_walks_both_directions():
    g = sankey_service.get_graph("code-of-ethics")
    # pick a middle-layer node that has both parents and children
    node = next(n for n in g.nodes if n.layer == 1 and n.inDegree and n.outDegree)
    res = client.get(f"/api/maps/code-of-ethics/connected/{node.uid}").json()
    assert res["upstream"], "must reach the rules above"
    assert res["downstream"], "must reach the controls below"
    assert node.uid in res["nodes"]


def test_drill_returns_full_chains():
    g = sankey_service.get_graph("code-of-ethics")
    node = next(n for n in g.nodes if n.layer == 0 and n.outDegree)
    res = client.get(f"/api/maps/code-of-ethics/drill/{node.uid}").json()
    assert res["columns"][0] == "Rules"
    assert res["rows"]
    assert res["rows"][0]["cells"]["Rules"]["uid"] == node.uid


# ------------------------------------------------------------ generated map
def _build_map():
    book = client.post("/api/rulebooks/seed").json()
    return client.post(
        "/api/maps/build",
        json={"name": "Test map", "rulebookId": book["id"],
              "policyIds": [], "controlIds": [], "includeObligations": True},
    ).json()


def test_build_map_from_rulebook():
    g = _build_map()
    assert [l["type"] for l in g["layers"]] == [
        "Rule", "Obligation", "Policy", "Control", "Risk", "Issue"
    ]
    assert g["summary"]["totalNodes"] > 40
    assert g["summary"]["realLinks"] > 0
    assert any(n["impacted"] for n in g["nodes"]), "amended rules must raise a triangle"


def test_generated_map_exposes_real_gaps():
    g = _build_map()
    unmapped = [n for n in g["nodes"] if n["band"] == "Unmapped"]
    assert unmapped, "a jurisdiction with no deployed control must show as a gap"


def test_exports():
    g = _build_map()
    mid = g["mapId"]
    csv = client.get(f"/api/maps/{mid}/export.csv")
    assert csv.status_code == 200 and b"Rules" in csv.content
    xlsx = client.get(f"/api/maps/{mid}/export.xlsx")
    assert xlsx.status_code in (200, 503)
    if xlsx.status_code == 200:
        assert xlsx.content[:2] == b"PK"
    pdf = client.get(f"/api/maps/{mid}/export.pdf")
    assert pdf.status_code in (200, 503)
    if pdf.status_code == 200:
        assert pdf.content[:4] == b"%PDF"


# -------------------------------------------------------------- reg change
def test_change_feed_and_impact():
    feed = client.get("/api/changes").json()
    assert feed and feed[0]["daysToComply"] >= 0
    imp = client.get("/api/changes/CHG-01/impact").json()
    assert 0 <= imp["impactScore"] <= 100
    assert imp["affectedRules"]
    assert imp["recommendedActions"]
    for key in ("materiality", "gapSeverity", "urgency"):
        assert 0 <= imp[key] <= 100


def test_change_status_transition_is_audited():
    client.post("/api/changes/CHG-04/status", json={"status": "Triaged", "note": "picked up"})
    feed = {c["id"]: c for c in client.get("/api/changes").json()}
    assert feed["CHG-04"]["status"] == "Triaged"
    trail = client.get("/api/audit").json()
    assert any(a["action"] == "change.status" for a in trail)


def test_reg_b_change_reaches_the_retention_rule():
    """CHG-05 touches 12 CFR 1002.12, which is the clause-level rule."""
    imp = client.get("/api/changes/CHG-05/impact").json()
    rules = [store.rule_by_id(r) for r in imp["affectedRules"]]
    assert any(r["cite"] == "12 CFR 1002.12" for r in rules)
    assert imp["affectedControls"], "retention controls must be picked up"


# ------------------------------------------------------------ content sources
def test_source_registry():
    r = client.get("/api/sources").json()
    assert r["summary"]["regulatorySources"] > 25
    assert r["summary"]["machineReadable"] >= 5
    ids = {s["id"] for s in r["regulatory"]}
    assert {"us-ecfr", "uk-legislation", "eu-eurlex", "in-rbi", "hk-hkma"} <= ids
    # the licensing position is the point of the registry, so pin it down
    fca = next(s for s in r["regulatory"] if s["id"] == "uk-fca-handbook")
    assert fca["licence"] == "permission-required"
    iso = next(f for f in r["controlFrameworks"] if f["id"] == "iso27002")
    assert iso["licence"] == "licensed"
    scf = next(f for f in r["controlFrameworks"] if f["id"] == "scf")
    assert scf["priority"] == 1 and scf["licence"] == "open-attribution"


def test_source_registry_filters():
    uk = client.get("/api/sources", params={"juris": "uk"}).json()
    assert all(s["juris"] == "uk" for s in uk["regulatory"])
    gated = client.get("/api/sources", params={"licence": "permission-required"}).json()
    assert gated["summary"]["permissionRequired"] == len(gated["regulatory"])


# ----------------------------------------------------------------- Ask AAVA
def test_semantic_bridge_and_missing_verify():
    """'legal entity customer' meets 'UBO register' by meaning; 'capture' is not 'verify'."""
    m = client.post("/api/map/obligation", json={"ruleId": "31 CFR 1010.230", "focus": ["beneficial owner"]}).json()
    assert m["match"]["policyId"] == "POL-02" and m["match"]["clauseSec"] == "4.3"
    assert any(not b["identical"] and b["concept"] == "beneficial owner" for b in m["match"]["bridges"])
    assert any("verify" in r for r in m["match"]["reasons"])
    assert m["verdict"] == "Partial" and m["gate"] == "human" and m["draft"]


def test_contradiction_is_a_conflict_and_wins():
    m = client.post("/api/map/obligation", json={"ruleId": "DPSS.CO.PD.No.1810"}).json()
    assert m["verdict"] == "Conflict" and m["match"]["clauseSec"] == "2.1"


def test_vague_deadline_is_flagged():
    m = client.post("/api/map/obligation", json={"ruleId": "31 CFR 1020.320"}).json()
    assert m["verdict"] == "Partial"
    assert any("promptly" in r for r in m["match"]["reasons"])


def test_ask_map_run_shape():
    r = client.post("/api/ask", json={"question": "Do our policies cover beneficial ownership in the US, UK and Hong Kong?"}).json()
    assert r["intent"] == "map" and len(r["data"]["mappings"]) == 3
    assert all(m["verdict"] != "Covered" for m in r["data"]["mappings"])
    assert r["gates"], "gate steps must be visible in the run"
    assert any(a["action"] == "ask.run" for a in client.get("/api/audit").json())


def test_ask_report_change_issue_risks_watch():
    rep = client.post("/api/ask", json={"question": "Generate the compliance report"}).json()
    assert 0 <= rep["data"]["coverageScore"] <= 100 and rep["data"]["matrix"] and rep["data"]["plan"]
    chg = client.post("/api/ask", json={"question": "What changed at the HKMA?"}).json()
    assert chg["mode"] == "Act" and any(m["isNew"] for m in chg["data"]["mappings"])
    iss = client.post("/api/ask", json={"question": "payment tokens replicated to a non-Indian DR region"}).json()
    assert iss["data"]["mappings"][0]["verdict"] == "Conflict" and len(iss["data"]["plan"]) == 7
    rk = client.post("/api/ask", json={"question": "Which risks are above appetite?"}).json()
    assert all(x["residual"] != x["appetite"] for x in rk["data"]["risks"])
    assert client.post("/api/ask", json={"question": "tell me when AML rules change"}).json()["intent"] == "watch"


def test_ask_abstains_and_logs():
    r = client.post("/api/ask", json={"question": "what is the weather"}).json()
    assert r["abstained"] and not r["data"]
    assert any(a["action"] == "ask.abstain" for a in client.get("/api/audit").json())


def test_write_intent_escalates_and_approval_is_audited():
    r = client.post("/api/ask", json={"question": "payment tokens replicated to a non-Indian DR region"}).json()
    assert r["mode"] == "Act"
    client.post("/api/ask/approve", json={"runId": r["runId"], "gate": "gate2", "subject": "ISS-03 plan"})
    trail = client.get("/api/audit").json()
    assert any(a["action"] == "gate2.approve" for a in trail)
    assert any(a["action"] == "mode.escalate" for a in trail)


# --------------------------------------------------------- map data quality
def test_duplicate_source_nodes_keep_their_own_links():
    """Legacy bug: links of every duplicate source id landed on the last duplicate."""
    g = sankey_service.get_graph("best-execution")
    raw = sankey_service.raw_layers("best-execution")[0]
    nxt = {str(n["unique_id"]) for n in sankey_service.raw_layers("best-execution")[1]}
    for i, node in enumerate(raw):
        want = {k["id"] for k in node.get("other_kps_ds2") or [] if k["id"] in nxt and k["value"] > 0.001}
        uid = [n for n in g.nodes if n.layer == 0][i].uid
        got = {l.target.split(":", 1)[1].split("~")[0] for l in g.links if l.source == uid and not l.placeholder}
        assert got == want, f"node {i} ({uid})"


@pytest.mark.parametrize("map_id", ["code-of-ethics", "anti-corruption", "best-execution", "large-volume"])
def test_bundled_datasets_have_no_errors(map_id):
    r = client.get(f"/api/maps/{map_id}/validate").json()
    assert r["errors"] == 0 and r["ok"]
    assert 0 <= r["qualityScore"] <= 100


def test_validator_reports_what_is_really_there():
    be = client.get("/api/maps/best-execution/validate").json()
    assert any(f["code"] == "duplicate_unique_id" for f in be["findings"])
    lv = client.get("/api/maps/large-volume/validate").json()
    assert any(f["code"] == "unmapped_nodes" for f in lv["findings"])


def test_validator_catches_broken_data():
    from app.services import map_validator_service as v
    bad = [[{"unique_id": "a", "dsName": "A", "quote": "q", "other_kps_ds2": [{"id": "zzz", "value": 0.9}, {"id": "b", "value": 7}, {"id": "b", "value": "x"}]}],
           [{"unique_id": "b", "dsName": "B", "quote": ""}]]
    codes = {f["code"] for f in v.validate_layers(bad)["findings"]}
    assert {"dangling_link", "value_out_of_range", "non_numeric_value", "empty_quote"} <= codes


def test_engine_survives_bad_values():
    from app.services.sankey_service import ComplianceGraph
    g = ComplianceGraph("t", "t", [[{"unique_id": "a", "dsName": "A", "other_kps_ds2": [{"id": "b", "value": "oops"}, {"id": "c", "value": 5}]}],
                                   [{"unique_id": "b", "dsName": "B"}, {"unique_id": "c", "dsName": "C"}]])
    assert g.sanitised["nonNumeric"] == 1 and g.sanitised["clamped"] == 1
    assert all(0 <= l.value <= 1 for l in g.links)


# ------------------------------------------------- hierarchy, ledger, coordination
def test_hierarchy_tree_and_validation():
    tree = client.get("/api/hierarchy").json()
    assert tree and tree[0]["children"]
    v = client.get("/api/hierarchy/validate").json()
    assert v["ok"] and v["rules"] == 68
    us = client.get("/api/search", params={"regulator": "FinCEN"}).json()
    assert us["total"] > 0 and all(r["rule"]["regulator"] == "FinCEN" for r in us["results"])
    assert client.get("/api/rules/RUL-106/path").json()[-1]["id"] == "RUL-106"


def test_audit_ledger_detects_tampering():
    client.post("/api/changes/CHG-01/notify")
    assert client.get("/api/audit/verify").json()["ok"] is True
    store.AUDIT[0]["detail"]["tampered"] = True
    assert client.get("/api/audit/verify").json()["ok"] is False


def test_change_notifies_the_right_people_once():
    r = client.post("/api/changes/CHG-01/notify").json()
    assert r["created"] >= 4 and r["priority"] in ("critical", "high")
    roles = {n["to"]["short"]: n["raci"] for n in r["notifications"]}
    assert "CCO" in roles and "Legal" in roles and "Internal Audit" in roles
    assert roles["Internal Audit"] == "I" and roles["Legal"] == "C"
    again = client.post("/api/changes/CHG-01/notify").json()
    assert again["created"] == 0
    assert client.post("/api/changes/NOPE/notify").status_code == 404


U = lambda uid: {"X-AAVA-User": uid}


def test_comment_mention_approval_and_escalation():
    client.post("/api/changes/CHG-01/notify")
    c = client.post("/api/threads/CHG-01/comments", json={"authorId": "SH-02", "text": "Needs a decision. @Legal can you confirm the 5 day wording?"}, headers=U("SH-02")).json()
    assert c["message"]["mentions"] == ["SH-09"] and len(c["mentionNotifications"]) == 1
    assert client.post("/api/threads/CHG-01/comments", json={"authorId": "SH-02", "text": "  "}, headers=U("SH-02")).status_code == 400
    assert client.post("/api/threads/CHG-01/comments", json={"authorId": "NOPE", "text": "x"}, headers=U("SH-02")).status_code == 403   # you can only comment as yourself
    ap = client.post("/api/threads/CHG-01/approval", json={"gate": "gate3", "summary": "Approve remediation plan"}).json()
    assert [r["id"] for r in ap["required"]] == ["SH-01"]
    assert client.post("/api/threads/CHG-01/decision", json={"approverId": "SH-02", "decision": "approve"}, headers=U("SH-02")).status_code == 403
    assert client.post("/api/threads/CHG-01/decision", json={"approverId": "SH-01", "decision": "reject"}, headers=U("SH-01")).status_code == 400
    ok = client.post("/api/threads/CHG-01/decision", json={"approverId": "SH-01", "decision": "approve", "note": "ok"}, headers=U("SH-01")).json()
    assert ok["status"] == "approved"
    esc = client.post("/api/changes/CHG-01/escalate", params={"hoursAhead": 100}).json()
    assert esc["escalated"] and all(e["escalatedTo"] for e in esc["escalated"])
    co = client.get("/api/changes/CHG-01/coordination").json()
    assert co["status"]["approval"] == "approved" and any(m["type"] == "escalation" for m in co["messages"])
    assert client.get("/api/audit/verify").json()["ok"]


def test_ask_coordinates_stakeholders():
    r = client.post("/api/ask", json={"question": "Who needs to be told about the HKMA change and who must sign it off?"}).json()
    assert r["intent"] == "coordinate" and r["mode"] == "Act"
    d = r["data"]
    assert d["routing"] and d["approval"]["status"] == "pending" and d["thread"]["messages"]
    assert any(x["raci"] == "A" for x in d["routing"])
    assert client.post("/api/ask", json={"question": "What changed at the HKMA and what do we need to do?"}).json()["intent"] == "change"


# ------------------------------------------------- scope, assess, act, share
def test_assess_is_rule_based_and_scoped():
    full = client.post("/api/assess", json={"subject": "org"}).json()
    assert full["counts"]["total"] >= 12 and full["rows"][0]["status"] in ("Not compliant", "Partial")
    assert full["rows"][0]["standards"] and full["rows"][0]["fix"]
    sc = client.post("/api/assess", json={"subject": "org", "scope": {"policies": ["POL-01"], "controls": ["CTRL-02"], "rules": []}}).json()
    assert sc["scope"]["scoped"] and sc["counts"]["total"] < full["counts"]["total"]
    assert client.post("/api/assess", json={"subject": "nope"}).status_code == 404


def test_custom_control_starts_untested_and_is_audited():
    c = client.post("/api/scope/controls", json={"name": "Customer risk rating review", "owner": "KYC Utility", "ruleMatter": "KYC and CDD", "jurisdictions": ["us"]}).json()
    assert c["testResult"] == "Not tested" and c["id"] == "CTRL-C1"
    ids = [x["id"] for g in client.get("/api/scope/catalog").json()["controls"] for x in g["items"]]
    assert "CTRL-C1" in ids
    assert client.post("/api/scope/controls", json={"name": "x", "owner": "y", "ruleMatter": "KYC and CDD", "jurisdictions": []}).status_code == 422
    assert any(a["action"] == "scope.add" for a in client.get("/api/audit").json())


def test_fix_plan_waits_for_approval_and_external_share_needs_cco():
    q = client.post("/api/actions/fix-plan", json={"subject": "platform"}).json()
    assert q and all(a["status"] == "pending" for a in q)
    again = client.post("/api/actions/fix-plan", json={"subject": "platform"}).json()
    assert len(client.get("/api/actions").json()) == len(q) == len(again)
    sh = client.post("/api/shares", json={"subject": "platform", "recipients": ["SH-01", "X-1"]}, headers=U("SH-02")).json()
    assert sh["status"] == "awaiting CCO approval" and len(sh["fingerprint"]) == 64
    gate = next(a for a in client.get("/api/actions").json() if a["key"] == "shr-" + sh["id"])
    assert client.post(f"/api/actions/{gate['id']}/decision", json={"decision": "approved"}, headers=U("SH-01")).json()["status"] == "approved"
    assert next(s for s in client.get("/api/shares").json() if s["id"] == sh["id"])["status"] == "sent"
    assert client.post(f"/api/actions/{gate['id']}/decision", json={"decision": "approved"}, headers=U("SH-01")).status_code == 400
    assert client.post(f"/api/shares/{sh['id']}/verify").json()["matches"] is True
    internal = client.post("/api/shares", json={"subject": "org", "recipients": ["SH-02"]}).json()
    assert internal["status"] == "sent"
    assert client.post("/api/shares", json={"subject": "org", "recipients": []}).status_code == 400
    assert client.get("/api/audit/verify").json()["ok"]


def test_posture_and_report_download():
    p = client.get("/api/posture").json()
    assert 0 <= p["coverageScore"] <= 100
    r = client.post("/api/assess/report.html", json={"subject": "vendor"})
    assert r.status_code == 200 and "Compliance assessment" in r.text and "attachment" in r.headers["content-disposition"]


def test_map_impact_and_mitigation_plan_downloads():
    r = client.get("/api/maps/code-of-ethics/export-plan.html")
    assert r.status_code == 200 and "Mitigation plan" in r.text and "attachment" in r.headers["content-disposition"]
    assert client.get("/api/maps/nope/export-plan.html").status_code == 404


def test_frameworks_and_domains():
    r = client.get("/api/frameworks").json()
    ids = {f["id"] for f in r["frameworks"]}
    assert {"soc2", "iso9001", "iso27001", "pcidss", "hipaa", "gdpr"} <= ids and "Application" in r["kinds"]
    doms = {d["id"]: d for d in client.get("/api/domains").json()}
    assert {"banking", "retail", "ecommerce", "supply", "logistics", "health", "cpg"} <= set(doms)
    assert all(f in ids for d in doms.values() for f in d["frameworks"])


def test_framework_assess_soc2_and_iso9001():
    a = client.post("/api/assess/framework", json={"framework": "soc2", "subject": "Customer app", "kind": "Application", "domain": "tech"}).json()
    assert a["counts"]["total"] == 12 and a["readiness"] and a["evidenceRequests"]
    assert all(r["request"] and r["criterion"] for r in a["rows"])
    q = client.post("/api/assess/framework", json={"framework": "iso9001"}).json()
    assert q["counts"]["total"] == 11 and q["score"] != a["score"] or q["rows"] != a["rows"]
    assert client.post("/api/assess/framework", json={"framework": "nope"}).status_code == 404


def test_framework_scope_marks_not_assessed_and_report():
    body = {"framework": "soc2", "scope": {"policies": [], "controls": ["CTRL-33"], "rules": None}}
    a = client.post("/api/assess/framework", json=body).json()
    assert a["notAssessed"] and a["counts"]["total"] < 12
    h = client.post("/api/assess/framework/report.html", json={"framework": "iso9001", "subject": "Plant 3", "kind": "Site or facility"})
    assert h.status_code == 200 and "readiness: Plant 3" in h.text and "not an audit opinion" in h.text


def test_new_matter_without_policy_is_not_compliant():
    a = client.post("/api/assess/framework", json={"framework": "iso14001"}).json()
    r = next(x for x in a["rows"] if x["matter"] == "Environmental and sustainability")
    assert r["status"] == "Not compliant" and "No policy" in r["why"]


def test_framework_subject_share_and_fix_plan():
    sid = "fw:soc2|Customer app|Application"
    fx = client.post("/api/actions/fix-plan", json={"subject": sid}).json()
    assert fx and all("SOC 2" not in x["title"] or x["title"].startswith("Fix plan:") for x in fx)
    sh = client.post("/api/shares", json={"subject": sid, "recipients": ["SH-01"]}).json()
    assert sh["fingerprint"] and client.post(f"/api/shares/{sh['id']}/verify").json()["matches"]


def test_roles_listing_and_me():
    r = client.get("/api/access/roles").json()
    assert {"cco", "internal_audit", "external_auditor", "admin"} <= {x["id"] for x in r["roles"]} and "approve" in r["permissions"]
    me = client.get("/api/access/me", headers=U("SH-10")).json()
    assert me["role"] == "internal_audit" and me["readOnly"] and "share" not in me["perms"]
    assert len(client.get("/api/access/users").json()) >= 14


def test_read_only_roles_cannot_change_anything():
    for uid in ("SH-10", "X-1", "E-1"):
        assert client.post("/api/actions/fix-plan", json={"subject": "platform"}, headers=U(uid)).status_code == 403
        assert client.post("/api/shares", json={"subject": "org", "recipients": ["SH-02"]}, headers=U(uid)).status_code == 403
        assert client.post("/api/scope/save", json={}, headers=U(uid)).status_code == 403
    assert client.post("/api/assess", json={"subject": "org"}, headers=U("X-1")).status_code == 403
    assert client.post("/api/assess", json={"subject": "org"}, headers=U("SH-10")).status_code == 200
    assert client.get("/api/audit/verify", headers=U("SH-10")).status_code == 200


def test_gate_approval_needs_named_person_and_separation_of_duties():
    q = client.post("/api/actions/fix-plan", json={"subject": "org"}, headers=U("SH-02")).json()
    g3 = next(a for a in q if a["gate"] == "Gate 3")
    assert client.post(f"/api/actions/{g3['id']}/decision", json={"decision": "approved"}, headers=U("SH-02")).status_code == 403   # not named for Gate 3
    assert client.post(f"/api/actions/{g3['id']}/decision", json={"decision": "approved"}, headers=U("SH-10")).status_code == 403   # auditor cannot approve
    own = client.post("/api/actions/fix-plan", json={"subject": "vendor"}, headers=U("SH-01")).json()
    mine = next(a for a in own if a["by"] == "SH-01")
    assert "Separation of duties" in client.post(f"/api/actions/{mine['id']}/decision", json={"decision": "approved"}, headers=U("SH-01")).json()["detail"]
    assert client.post(f"/api/actions/{g3['id']}/decision", json={"decision": "approved"}, headers=U("SH-01")).status_code == 200


def test_admin_changes_roles_with_guard_rails_and_audit():
    assert client.put("/api/access/users/SH-04", json={"role": "compliance_officer"}, headers=U("SH-01")).status_code == 403
    r = client.put("/api/access/users/SH-04", json={"role": "risk_manager", "approves": ["Gate 2"]}, headers=U("A-1")).json()
    assert r["role"] == "risk_manager" and r["approves"] == ["Gate 2"]
    assert client.put("/api/access/users/SH-10", json={"approves": ["Gate 2"]}, headers=U("A-1")).status_code == 400            # an auditor cannot approve
    assert client.put("/api/access/users/A-1", json={"role": "executive"}, headers=U("A-1")).status_code == 400                  # last admin
    assert client.put("/api/access/users/SH-06", json={"approves": []}, headers=U("A-1")).status_code == 200
    assert client.put("/api/access/users/SH-01", json={"approves": []}, headers=U("A-1")).status_code == 400                     # nobody left on Gate 3
    last = [a for a in client.get("/api/audit").json() if a["action"] == "access.change"]
    assert last and last[-1]["actorId"] == "A-1"


def test_audit_room_sees_only_what_was_released_to_them():
    sh = client.post("/api/shares", json={"subject": "platform", "recipients": ["X-1"]}, headers=U("SH-02")).json()
    assert client.get("/api/shares", headers=U("X-1")).json() == []                                  # still awaiting approval
    gate = next(a for a in client.get("/api/actions").json() if a["key"] == "shr-" + sh["id"])
    client.post(f"/api/actions/{gate['id']}/decision", json={"decision": "approved"}, headers=U("SH-01"))
    assert [s["id"] for s in client.get("/api/shares", headers=U("X-1")).json()] == [sh["id"]]
    assert client.get("/api/shares", headers=U("X-2")).json() == []


def test_story_worked_example():
    r = client.get("/api/story")
    assert r.status_code == 200
    s = r.json()
    assert s["trigger"]["ref"] == "CHG-01"
    assert len(s["steps"]) == 8 and len(s["narration"]) >= 4 and s["problems"]
    assert "Illustrative" in s["disclaimer"]
