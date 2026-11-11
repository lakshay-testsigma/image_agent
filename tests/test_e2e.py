"""End to end through the real CLI: every stage, with the agent's parts (and the image tool) faked."""
import copy

from conftest import BRIEF, GLOBAL, INTAKE, MANUFACTURER_FACTS, MANUFACTURER_PAGE


def test_product_job_from_photo_to_listing(st):
    st.global_design()
    job = st.job(design={"style": {"mood": "late afternoon calm"}, "must_avoid": ["plants"],
                         "mockups": [{"name": "catalog", "type": "catalog"},
                                     {"name": "story", "type": "social", "style": {"output": {"width": 360, "height": 640}}}]})
    name = job.name
    assets_before = {f.name: f.read_bytes() for f in job.iterdir()}

    # 1 intake
    init = st.run("init", job)
    assert (init["product_id"], init["client_source"]) == (name, "S0")
    assert st.run("status", job)["next_stage"] == "intake"
    st.intake(job)

    # 2 research: manufacturer page + two retailers that disagree on weight
    st.add_source(job, MANUFACTURER_PAGE, "manufacturer", "https://nordlys.example/chair", MANUFACTURER_FACTS)
    st.add_source(job, "Chair, weight 6.2 kg\n", "retailer", "https://shop-a.example/chair",
                  [{"key": "weight", "value": 6.2, "unit": "kg", "quote": "weight 6.2 kg"}])
    st.add_source(job, "Chair, weight 7 kg, seat height 45 cm\n", "retailer", "https://shop-b.example/chair",
                  [{"key": "weight", "value": 7, "unit": "kg", "quote": "weight 7 kg"},
                   {"key": "seat_height", "value": 45, "unit": "cm", "quote": "seat height 45 cm"}])
    st.extract(job, "S0", [{"key": "height", "label": "Height", "value": 85, "unit": "cm", "quote": "Height: 85 cm"}])
    assert st.run("status", job)["next_stage"] == "factcheck"

    # 3 fact-check
    v = st.verify(job, "--require", "height,material")
    assert v["summary"] == {"verified": 2, "needs_review": 1, "conflict": 1, "rejected": 0}
    assert st.run("status", job)["next_stage"] == "design"

    # 4 design + metadata
    resolved = st.run("design", job)
    assert [(m["name"], m["output"]) for m in resolved["mockups"]] == [
        ("catalog", {"aspect": "1:1", "width": 400, "height": 400}), ("story", {"aspect": "9:16", "width": 360, "height": 640})]
    assert resolved["generations_planned"] == 2 and resolved["overrides_blocked"] == []
    summary = st.run("metadata", job)
    assert summary["attributes"] == {"verified": ["height", "material"], "unverified": ["seat_height"], "conflicting": ["weight"],
                                     "rejected": [], "inferred": ["shape", "material", "color", "finish"], "unavailable": []}
    status = st.run("status", job)
    assert status["metadata_ready"] is True and status["next_stage"] == "creative"

    # 5 creative (the agent writes these)
    st.write(f"output/{name}/creative/shot-plan.md", "# Shot plan")
    for shot in ("catalog", "story"):
        st.write(f"output/{name}/creative/prompts/{shot}.md", f"Images 1 shows the exact chair. Shot: {shot}.")

    # 6 render: catalog needs a second attempt
    bad = st.render(job, "catalog")
    assert st.approve(job, bad, visual="fail")["next"].startswith("retry")
    catalog = st.render(job, "catalog")
    story_raw = st.render(job, "story", size=(512, 512))

    # 7 overlay: a verified fact + approved copy, resized to the story's delivery size
    spec = st.write(f"output/{name}/creative/overlays/story.json", {
        "base": str(story_raw), "output": str(story_raw.with_name("v1-1-story.png")),
        "canvas": {"width": 360, "height": 640, "base_fit": "cover"},
        "elements": [{"type": "text", "fact": "height", "template": "{value}", "x": 0.1, "y": 0.1, "size": 0.04},
                     {"type": "text", "copy": "Handcrafted in Portugal", "x": 0.1, "y": 0.9, "size": 0.04}]})
    story = st.root / st.run("overlay", job, "--spec", spec)["output"]
    conflict_spec = st.write("scratch/bad.json", {"base": str(story_raw), "elements": [{"type": "text", "fact": "weight", "x": 0, "y": 0}]})
    assert "not verified" in st.fails("overlay", job, "--spec", conflict_spec)

    # 8 QA
    assert st.approve(job, catalog)["approved"] is True
    assert st.approve(job, story, factual="pass")["approved"] is True
    st.run("contact-sheet", job)
    st.run("qa-set", job, "--consistency", "pass", "--notes", "same light and palette; angle and crop differ")

    # 9 export
    out = st.run("export", job)
    assert out["excluded_unverified"] == ["seat_height", "weight"] and out["missing_mockups"] == [] and out["forced"] is False
    listing = st.read(f"output/{name}/final/listing.json")
    assert [(f["key"], f["value"]) for f in listing["facts"]] == [("height", 85), ("material", "solid white oak")]
    assert all(f["sources"] for f in listing["facts"])
    assert listing["identity"]["brand"] == {"value": "Nordlys", "status": "inferred"}
    assert listing["design_system"]["name"] == "test-system"
    by_shot = {i["shot"]: i for i in listing["images"]}
    assert by_shot["catalog"]["attempt"] == 2 and by_shot["catalog"]["engine"] == "test+fake"
    assert by_shot["story"]["overlay"]["copy_rendered"] == ["Handcrafted in Portugal"]
    assert by_shot["story"]["mockup"]["style"]["mood"] == "late afternoon calm"
    assert by_shot["story"]["mockup"]["must_avoid"] == ["watermarks", "plants"]
    final = st.root / f"output/{name}/final"
    assert sorted(f.name for f in final.iterdir()) == [f"{name}-catalog-01.png", f"{name}-story-02.png", "listing.json", "product.json"]
    assert st.read(f"output/{name}/final/product.json")["schema_version"] == "1.0"

    status = st.run("status", job)
    assert status["next_stage"] is None and status["stages_skipped"] == {}
    events = [e["stage"] for e in st.read(f"output/{name}/manifest.json")["events"]]
    for stage in ("init", "intake", "research", "factcheck", "design", "metadata", "preflight:catalog", "render:catalog", "overlay", "qa", "qa-set", "export"):
        assert stage in events
    assert {f.name: f.read_bytes() for f in job.iterdir()} == assets_before  # assets/ is never modified


def test_concept_job_without_photos_research_or_product_design(st):
    """No subject photo, no facts, no per-product design: the global design system alone must be enough."""
    g = copy.deepcopy(GLOBAL)
    del g["mockups"]
    st.write("design/global.json", g)
    job = st.job("004-launch-poster", photos=(), brief=BRIEF.replace("exact", "none"))
    st.run("init", job)
    st.intake(job, fidelity={"mode": "none", "source": "brief"}, photos=[], facts_needed={"needed": False, "reason": "poster, approved copy only"})
    for stage in ("research", "factcheck"):
        st.run("skip", job, "--stage", stage, "--reason", "no factual claims")
    assert [m["name"] for m in st.run("design", job)["mockups"]] == ["main"]
    assert st.run("metadata", job)["research"] == "skipped"
    st.write(f"output/{job.name}/creative/prompts/main.md", "A Swiss-style poster.")
    assert st.run("preflight", job, "--shot", "main", "--no-product-refs")["reference_images"] == []
    img = st.render(job, "main")
    assert st.approve(job, img)["approved"] is True
    out = st.run("export", job)
    assert len(out["images"]) == 1 and out["excluded_unverified"] == []
    status = st.run("status", job)
    assert status["stages_skipped"] == {"research": "no factual claims", "factcheck": "no factual claims"}
    assert status["next_stage"] == "creative"  # no shot-plan.md was written in this test
