"""Intake validation and the product metadata file: statuses, traceability, schema, staleness."""
from conftest import INTAKE
from lib import metadata, paths


def meta(st, job):
    st.run("metadata", job)
    return st.read(f"output/{job.name}/metadata/product.json")


# ── intake ──

def test_intake_is_validated_and_rendered(st):
    job = st.job()
    out = st.intake(job)
    assert out["warnings"] == []
    md = (st.root / f"output/{job.name}/intake.md").read_text()
    assert "Fidelity: exact" in md and "woven paper-cord seat" in md


def test_intake_rejects_values_outside_the_schema(st):
    job = st.job()
    st.write(f"output/{job.name}/intake.json", {**INTAKE, "fidelity": {"mode": "pixel-perfect", "source": "brief"}})
    assert "$.fidelity.mode" in st.fails("intake", job)
    st.write(f"output/{job.name}/intake.json", {k: v for k, v in INTAKE.items() if k != "preservation_checklist"})
    assert "missing required 'preservation_checklist'" in st.fails("intake", job)


def test_exact_fidelity_needs_photos_and_a_checklist(st):
    concept = st.job("002-poster", photos=())
    st.write(f"output/{concept.name}/intake.json", {**INTAKE, "photos": []})
    assert "needs subject photos" in st.fails("intake", concept)
    job = st.job()
    st.write(f"output/{job.name}/intake.json", {**INTAKE, "preservation_checklist": []})
    assert "needs a preservation_checklist" in st.fails("intake", job)


def test_intake_cannot_describe_a_photo_that_is_not_there(st):
    job = st.job()
    st.write(f"output/{job.name}/intake.json", {**INTAKE, "photos": [{"file": "09-back.png"}]})
    assert "is not a subject photo" in st.fails("intake", job)


# ── metadata ──

def test_metadata_separates_verified_inferred_unverified_and_unavailable(st):
    job = st.ready()
    st.add_source(job, "Weight 6.2 kg\n", "retailer", "https://shop.example/p",
                  [{"key": "weight", "value": 6.2, "unit": "kg", "quote": "Weight 6.2 kg"}])
    st.intake(job, facts_needed={"needed": True, "keys": ["height", "material", "max_load"]})
    st.check(job)
    assert st.fails("verify", job, "--require", "height,material,max_load") == "2"
    m = meta(st, job)
    a = m["attributes"]
    assert {f["key"] for f in a["verified"]} == {"height", "material"}
    assert [f["key"] for f in a["unverified"]] == ["weight"]
    assert a["unavailable"] == ["max_load"]
    assert {"key": "material", "value": ["oak", "paper cord"], "basis": "photo observation at intake"} in a["inferred"]
    height = next(f for f in a["verified"] if f["key"] == "height")
    assert {s["source_id"] for s in height["sources"]} == {"S0", "S1"}
    assert all(s["quote"] == "Height: 85 cm" for s in height["sources"])
    assert {s["id"] for s in m["research"]["sources"]} >= {"S0", "S1"}
    assert any("max_load" in w for w in m["warnings"])


def test_identity_is_inferred_until_a_fact_verifies_it(st):
    job = st.ready()
    m = meta(st, job)
    assert m["identification"]["brand"] == {"value": "Nordlys", "status": "inferred"}
    assert m["identification"]["model"] == {"value": None, "status": "unknown"}
    st.add_source(job, "Brand: Nordlys Design\n", "manufacturer", "https://nordlys.example/about",
                  [{"key": "brand", "value": "Nordlys Design", "quote": "Brand: Nordlys Design"}])
    st.verify(job)
    assert meta(st, job)["identification"]["brand"] == {"value": "Nordlys Design", "status": "verified"}


def test_metadata_carries_design_constraints_and_reference_images(st):
    m = meta(st, st.ready(design={"must_avoid": ["plants"], "style": {"mood": "calm"}}))
    gc = m["generation_constraints"]
    assert gc["fidelity"] == "exact" and gc["must_avoid"] == ["watermarks", "plants"]
    assert gc["preservation_checklist"] == INTAKE["preservation_checklist"]
    assert gc["identity_constraints"] == ["Never change the subject's shape or colours."]
    assert m["design"]["style"]["mood"] == "calm"
    (ref,) = m["reference_images"]
    assert (ref["role"], ref["width"], ref["height"]) == ("primary", 300, 300) and len(ref["sha256"]) == 64


def test_metadata_needs_factcheck_finished_or_skipped(st):
    st.global_design()
    job = st.job()
    st.run("init", job)
    st.intake(job)
    st.run("design", job)
    assert "fact-check is not finished" in st.fails("metadata", job)


def test_research_cannot_be_skipped_when_intake_says_facts_are_needed(st):
    st.global_design()
    job = st.job()
    st.run("init", job)
    st.intake(job)
    st.run("design", job)
    for stage in ("research", "factcheck"):
        st.run("skip", job, "--stage", stage, "--reason", "none needed")
    assert "intake says facts are needed" in st.fails("metadata", job)
    st.intake(job, facts_needed={"needed": False, "reason": "mood shots only"})
    m = meta(st, job)
    assert m["research"]["status"] == "skipped" and m["attributes"]["verified"] == []


def test_metadata_is_blocked_without_consent_for_identifiable_people(st):
    job = st.ready()
    st.intake(job, people={"identifiable": True, "consent": "not_confirmed"})
    assert "without confirmed consent" in st.fails("metadata", job)


def test_metadata_needs_a_current_design(st):
    job = st.ready()
    st.write(f"assets/{job.name}/design.json", {"style": {"mood": "new"}})
    assert "product design layer" in st.fails("metadata", job)


def test_metadata_goes_stale_when_an_input_changes(st):
    job = st.ready()
    prod = paths.resolve(str(job))
    assert metadata.stale_reason(prod) is None
    st.intake(job, preservation_checklist=["curved arms"])
    assert "intake.json changed" in metadata.stale_reason(prod)
    st.run("metadata", job)
    st.run("override", job, "--key", "weight", "--value", "6", "--unit", "kg", "--note", "client call")
    st.verify(job)
    assert "facts.verified.json changed" in metadata.stale_reason(prod)
    st.run("metadata", job)
    st.image(f"assets/{job.name}/01-front.png", (300, 300), "#000000")
    assert "subject photos" in metadata.stale_reason(prod)


def test_verified_attribute_without_a_source_fails_validation():
    m = {"research": {"sources": [{"id": "S1"}]},
         "attributes": {"unavailable": ["height"], "verified": [
             {"key": "height", "basis": "authoritative source", "sources": []},
             {"key": "width", "basis": "authoritative source", "sources": [{"source_id": "S9"}]},
             {"key": "weight", "basis": "human override: client email", "sources": []}]}}
    errors = metadata._traceability_errors(m)
    assert errors == ["verified 'height' has no source", "verified 'width' cites unknown source S9",
                      "keys both verified and unavailable: ['height']"]


def test_photo_observation_that_contradicts_a_verified_fact_is_flagged(st):
    job = st.ready()
    st.intake(job, visual={**INTAKE["visual"], "materials": ["steel"]})
    assert any("shares no word" in w for w in meta(st, job)["warnings"])
