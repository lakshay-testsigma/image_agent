"""Gates around generation, QA and export: what must hold before an image is made, approved or shipped."""
import copy

from conftest import GLOBAL


def canvas_overlay(st, job, base, size=(400, 400), elements=()):
    out = base.with_name(base.stem + "-final.png")
    s = st.write("scratch/canvas.json", {"base": str(base), "output": str(out), "elements": list(elements),
                                         "canvas": {"width": size[0], "height": size[1], "base_fit": "cover"}})
    st.run("overlay", job, "--spec", s)
    return out


# ── before generating ──

def test_preflight_needs_valid_current_metadata(st):
    st.global_design()
    job = st.job()
    st.run("init", job)
    assert "no metadata/product.json" in st.fails("preflight", job, "--shot", "catalog")
    job = st.ready("002-ready")
    st.intake(job, preservation_checklist=["only this"])
    assert "intake.json changed" in st.fails("preflight", job, "--shot", "catalog")
    assert "intake.json changed" in st.fails("register", job, "--shot", "catalog", "--image", st.image("scratch/x.png"), "--prompt", "p")


def test_preflight_returns_what_the_image_tool_needs(st):
    job = st.ready()
    pf = st.run("preflight", job, "--shot", "catalog")
    assert (pf["attempt"], pf["attempts_allowed"], pf["fidelity"]) == (1, 2, "exact")
    assert pf["output"] == {"aspect": "1:1", "width": 400, "height": 400}
    assert pf["reference_images"] == [str(job / "01-front.png")]
    assert pf["prompt_file"].endswith("creative/prompts/catalog.md")


def test_only_planned_mockups_can_be_rendered(st):
    job = st.ready()
    assert "is not a planned mockup" in st.fails("preflight", job, "--shot", "cafe-quickie")
    assert "is not a planned mockup" in st.fails("register", job, "--shot", "cafe-quickie", "--image", st.image("scratch/x.png"), "--prompt", "p")
    # the way in: add it to the session layer, re-resolve, rebuild metadata
    st.write(f"output/{job.name}/design/session.json", {"mockups": [{"name": "cafe-quickie", "type": "lifestyle"}]})
    st.run("design", job)
    st.run("metadata", job)
    st.write(f"output/{job.name}/creative/prompts/cafe-quickie.md", "prompt")
    assert st.run("preflight", job, "--shot", "cafe-quickie")["shot"] == "cafe-quickie"


def test_preflight_needs_a_prompt_file(st):
    job = st.ready()
    (st.root / f"output/{job.name}/creative/prompts/catalog.md").unlink()
    assert "no prompt for this shot" in st.fails("preflight", job, "--shot", "catalog")


def test_exact_fidelity_needs_a_subject_photo_reference(st):
    job = st.ready()
    assert "needs at least one subject photo" in st.fails("preflight", job, "--shot", "catalog", "--no-product-refs")


def test_attempt_budget_stops_the_retry_loop(st):
    job = st.ready()
    st.render(job, "catalog")
    assert st.run("status", job)["mockup_attempts"]["catalog"] == {"used": 1, "allowed": 2, "left": 1, "extra_approved": []}
    st.render(job, "catalog")
    assert "attempt budget for 'catalog' is used up (2 of 2)" in st.fails("preflight", job, "--shot", "catalog")
    assert st.run("preflight", job, "--shot", "lifestyle")["attempt"] == 1  # budgets are per mockup
    pf = st.run("preflight", job, "--shot", "catalog", "--extra-attempt", "user: try once more with the label smaller")
    assert (pf["attempt"], pf["attempts_allowed"]) == (3, 3)
    assert st.read(f"output/{job.name}/renders/catalog/attempts.json")[0]["reason"].startswith("user: try once more")


def test_extra_attempt_is_ignored_while_budget_remains(st):
    job = st.ready()
    pf = st.run("preflight", job, "--shot", "catalog", "--extra-attempt", "just in case")
    assert (pf["attempt"], pf["attempts_allowed"]) == (1, 2)


def test_render_past_the_budget_is_logged_but_can_never_be_approved(st):
    job = st.ready()
    for _ in range(3):
        img = st.render(job, "catalog", preflight=False)
    log = st.read(f"output/{job.name}/renders/catalog/v3.json")
    assert log["over_budget"] is True and log["attempt"] == 3
    entry = st.approve(job, img)
    assert entry["approved"] is False and entry["blocked_by"] == ["attempt_budget"]


# ── QA ──

def test_wrong_delivery_size_blocks_approval_until_resized(st):
    job = st.ready()
    raw = st.render(job, "catalog", size=(256, 256))
    entry = st.approve(job, raw)
    assert entry["approved"] is False and entry["blocked_by"] == ["delivery_size"]
    assert entry["checks"]["delivery_size"] == {"ok": False, "expected": "400x400", "actual": "256x256",
                                                "fix": "resize with an overlay `canvas` of 400x400"}
    assert st.approve(job, canvas_overlay(st, job, raw))["approved"] is True


def test_aspect_only_output_checks_the_aspect(st):
    g = copy.deepcopy(GLOBAL)
    g["style"]["output"] = {"aspect": "4:5"}
    st.write("design/global.json", g)
    job = st.ready()
    assert st.approve(job, st.render(job, "catalog", size=(800, 1000)))["approved"] is True
    assert st.approve(job, st.render(job, "catalog", size=(800, 800)))["blocked_by"] == ["delivery_size"]


def test_failed_gate_says_retry_then_escalate(st):
    job = st.ready()
    first = st.approve(job, st.render(job, "catalog"), visual="fail")
    assert first["approved"] is False and first["next"].startswith("retry") and "attempt 2 of 2" in first["next"]
    second = st.approve(job, st.render(job, "catalog"), visual="fail")
    assert second["next"].startswith("escalate")


def test_factual_gate_cannot_be_skipped_when_facts_are_drawn(st):
    job = st.ready()
    final = canvas_overlay(st, job, st.render(job, "catalog"), elements=[{"type": "text", "fact": "height", "x": 0.1, "y": 0.1}])
    assert "--factual na is not allowed" in st.fails("qa-mark", job, final, "--factual", "na", "--visual", "pass", "--creative", "pass")
    assert st.approve(job, final, factual="pass")["approved"] is True


def test_drawn_fact_that_no_longer_matches_blocks_approval(st):
    job = st.ready()
    final = canvas_overlay(st, job, st.render(job, "catalog"), elements=[{"type": "text", "fact": "height", "x": 0.1, "y": 0.1}])
    st.run("override", job, "--key", "height", "--value", "86", "--unit", "cm", "--note", "client corrected it")
    st.verify(job)
    st.run("metadata", job)
    entry = st.approve(job, final, factual="pass")
    assert entry["blocked_by"] == ["overlay_facts"] and "re-run `overlay`" in entry["checks"]["overlay_facts"]["fix"]


# ── export ──

def approved_set(st, job):
    images = [st.render(job, shot) for shot in ("catalog", "lifestyle")]
    for img in images:
        st.approve(job, img)
    return images


def test_export_needs_an_approved_image(st):
    job = st.ready()
    img = st.render(job, "catalog")
    assert "nothing to export" in st.fails("export", job)
    assert "has not passed QA" in st.fails("export", job, "--image", img)


def test_image_changed_after_review_must_be_reviewed_again(st):
    job = st.ready()
    images = approved_set(st, job)
    st.run("qa-set", job, "--consistency", "pass")
    st.image(str(images[0].relative_to(st.root)), (400, 400), "#FF0000")  # e.g. the overlay was re-run
    assert "changed since it was reviewed" in st.fails("export", job, "--image", images[0], "--image", images[1])


def test_two_or_more_images_need_a_passing_set_verdict(st):
    job = st.ready()
    approved_set(st, job)
    assert "no set-level verdict" in st.fails("export", job)
    st.run("qa-set", job, "--consistency", "fail", "--notes", "lifestyle is much warmer than catalog")
    assert "failed the consistency review" in st.fails("export", job)
    st.run("qa-set", job, "--consistency", "pass")
    assert len(st.run("export", job)["images"]) == 2


def test_set_verdict_must_cover_the_images_being_exported(st):
    job = st.ready()
    st.approve(job, st.render(job, "catalog"))
    st.run("qa-set", job, "--consistency", "pass")
    st.approve(job, st.render(job, "lifestyle"))
    assert "does not cover" in st.fails("export", job)


def test_missing_mockups_need_partial(st):
    job = st.ready()
    st.approve(job, st.render(job, "catalog"))
    assert "planned mockups without an approved image: lifestyle" in st.fails("export", job)
    out = st.run("export", job, "--partial")
    assert out["missing_mockups"] == ["lifestyle"] and out["forced"] is False


def test_force_is_recorded_in_the_listing(st):
    job = st.ready()
    img = st.render(job, "catalog")
    st.run("export", job, "--image", img, "--force")
    listing = st.read(f"output/{job.name}/final/listing.json")
    assert listing["forced"] is True and "has not passed QA" in listing["qa_problems_overridden"][0]
