"""Design resolution: required global layer, optional product + session layers, fixed precedence rules."""
import copy

from conftest import GLOBAL
from lib import design, paths


def resolve(st, job):
    st.run("design", job)
    return st.read(f"output/{job.name}/design/design.resolved.json")


def log(resolved, path, applied):
    return [e for e in resolved["resolution_log"] if e["path"] == path and e["applied"] is applied]


def test_global_design_is_required(st):
    job = st.job()
    assert "no global design system" in st.fails("design", job)


def test_no_product_design_falls_back_to_global(st):
    st.global_design()
    r = resolve(st, st.job())
    assert r["style"] == GLOBAL["style"]
    assert [m["name"] for m in r["mockups"]] == ["catalog", "lifestyle"]
    assert [l["present"] for l in r["layers"]] == [True, False, False]
    assert r["resolution_log"] == []


def test_no_mockups_anywhere_gives_one_default(st):
    g = copy.deepcopy(GLOBAL)
    del g["mockups"]
    st.write("design/global.json", g)
    r = resolve(st, st.job())
    assert [(m["name"], m["type"], m["variations"]) for m in r["mockups"]] == [("main", "hero", 1)]


def test_product_overrides_unlocked_fields_and_logs_them(st):
    st.global_design()
    r = resolve(st, st.job(design={"style": {"lighting": "hard noon sun", "props": "a wool throw"}}))
    assert r["style"]["lighting"] == "hard noon sun" and r["style"]["props"] == "a wool throw"
    assert r["style"]["background"] == GLOBAL["style"]["background"]  # untouched fields stay global
    entry = log(r, "style.lighting", True)[0]
    assert (entry["layer"], entry["from"], entry["to"]) == ("product", GLOBAL["style"]["lighting"], "hard noon sun")


def test_locked_fields_keep_the_global_value(st):
    st.global_design()
    r = resolve(st, st.job(design={"style": {"palette": {"accent": ["#FF0000"]}}, "generation": {"max_attempts": 9}}))
    assert r["style"]["palette"] == GLOBAL["style"]["palette"]
    assert r["generation"]["max_attempts"] == 2
    assert log(r, "style.palette", False)[0]["rejected"] == {"accent": ["#FF0000"]}
    assert log(r, "generation.max_attempts", False)


def test_objects_merge_key_by_key(st):
    st.global_design(locked=[])
    r = resolve(st, st.job(design={"style": {"palette": {"accent": ["#FF0000"]}}}))
    assert r["style"]["palette"] == {**GLOBAL["style"]["palette"], "accent": ["#FF0000"]}


def test_avoid_and_identity_lists_only_grow(st):
    st.global_design()
    r = resolve(st, st.job(design={"must_avoid": ["plants", "Watermarks"], "identity_constraints": ["Keep the brass rivets."]}))
    assert r["must_avoid"] == ["watermarks", "plants"]
    assert r["identity_constraints"] == [*GLOBAL["identity_constraints"], "Keep the brass rivets."]


def test_a_layer_cannot_set_locks(st):
    st.global_design()
    assert "only the global design system" in st.fails("design", st.job(design={"locked": []}))


def test_layer_typos_are_rejected(st):
    st.global_design()
    assert "unknown key 'ligthing'" in st.fails("design", st.job(design={"style": {"ligthing": "soft"}}))


def test_product_mockups_replace_the_global_list(st):
    st.global_design()
    r = resolve(st, st.job(design={"mockups": [{"name": "on-model", "type": "lifestyle", "variations": 3,
                                                "style": {"people": "one model, seated"}, "must_avoid": ["children"]}]}))
    (m,) = r["mockups"]
    assert (m["name"], m["variations"], m["style"]["people"]) == ("on-model", 3, "one model, seated")
    assert m["must_avoid"] == ["watermarks", "children"]
    assert "people" not in r["style"]  # a mockup's style stays on that mockup


def test_locked_mockups_cannot_be_replaced(st):
    st.global_design(locked=["mockups"])
    r = resolve(st, st.job(design={"mockups": [{"name": "other"}]}))
    assert [m["name"] for m in r["mockups"]] == ["catalog", "lifestyle"]
    assert log(r, "mockups", False)


def test_locks_apply_inside_product_mockups_but_not_to_the_global_files_own(st):
    g = copy.deepcopy(GLOBAL)
    g["mockups"] = [{"name": "dark", "style": {"palette": {"background": "#000000"}}}]
    st.write("design/global.json", g)
    assert resolve(st, st.job("001-a"))["mockups"][0]["style"]["palette"]["background"] == "#000000"
    r = resolve(st, st.job("002-b", design={"mockups": [{"name": "red", "style": {"palette": {"background": "#FF0000"}}}]}))
    assert r["mockups"][0]["style"]["palette"]["background"] == "#F5F2EC"


def test_session_layer_beats_product_layer(st):
    st.global_design()
    job = st.job(design={"style": {"lighting": "product light", "mood": "product mood"}})
    st.write(f"output/{job.name}/design/session.json", {"style": {"lighting": "session light"}})
    r = resolve(st, job)
    assert (r["style"]["lighting"], r["style"]["mood"]) == ("session light", "product mood")


def test_changing_only_the_aspect_drops_the_inherited_size(st):
    st.global_design()
    r = resolve(st, st.job(design={"style": {"output": {"aspect": "4:5"}}}))
    assert r["style"]["output"] == {"aspect": "4:5"}


def test_changing_only_the_size_rederives_the_aspect(st):
    st.global_design()
    r = resolve(st, st.job(design={"style": {"output": {"width": 1080, "height": 1350}}}))
    assert r["style"]["output"] == {"aspect": "4:5", "width": 1080, "height": 1350}


def test_locked_aspect_blocks_a_contradicting_size(st):
    st.global_design(locked=["style.output.aspect"])
    r = resolve(st, st.job(design={"style": {"output": {"width": 1080, "height": 1350}}}))
    assert r["style"]["output"] == GLOBAL["style"]["output"]
    assert log(r, "style.output", False)
    # a size that keeps the locked aspect is fine
    r = resolve(st, st.job("002-b", design={"style": {"output": {"width": 800, "height": 800}}}))
    assert r["style"]["output"] == {"aspect": "1:1", "width": 800, "height": 800}


def test_inconsistent_output_is_an_error(st):
    g = copy.deepcopy(GLOBAL)
    g["style"]["output"] = {"aspect": "16:9", "width": 400, "height": 400}
    st.write("design/global.json", g)
    assert "does not match aspect" in st.fails("design", st.job())


def test_duplicate_mockup_names_are_an_error(st):
    st.global_design()
    assert "duplicate mockup" in st.fails("design", st.job(design={"mockups": [{"name": "a"}, {"name": "a"}]}))


def test_style_text_that_mentions_an_avoided_thing_is_flagged(st):
    st.global_design()
    r = resolve(st, st.job(design={"must_avoid": ["no people", "plants"],
                                   "style": {"props": "a model's hand, two people chatting", "environment": "bright room without plants"}}))
    assert {(w["path"], w["term"]) for w in r["warnings"]} == {("style.props", "no people")}


def test_resolving_twice_is_stable_and_staleness_is_detected(st):
    st.global_design()
    job = st.job(design={"style": {"mood": "calm"}})
    prod = paths.resolve(str(job))
    assert "no design.resolved.json" in design.stale_reason(prod)
    resolve(st, job)
    first = (job.parent.parent / f"output/{job.name}/design/design.resolved.json").read_bytes()
    resolve(st, job)
    assert (job.parent.parent / f"output/{job.name}/design/design.resolved.json").read_bytes() == first
    assert design.stale_reason(prod) is None
    st.write(f"assets/{job.name}/design.json", {"style": {"mood": "loud"}})
    assert "product design layer" in design.stale_reason(prod)


def test_loose_photo_job_uses_a_sibling_design_file(st):
    st.global_design()
    photo = st.image("assets/003-mug.png")
    st.write("assets/003-mug.design.json", {"style": {"mood": "cosy"}})
    st.run("design", photo)
    r = st.read("output/003-mug/design/design.resolved.json")
    assert r["style"]["mood"] == "cosy" and r["layers"][1] == {**r["layers"][1], "file": "assets/003-mug.design.json", "present": True}


def test_brief_can_point_at_another_design_system(st):
    st.global_design()
    st.write("design/winter.json", {**copy.deepcopy(GLOBAL), "name": "winter"})
    job = st.job(brief="# Brief\n\n## Subject\n- Design system: design/winter.json\n")
    assert resolve(st, job)["name"] == "winter"
