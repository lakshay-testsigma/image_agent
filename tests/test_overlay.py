"""Overlay guards: only verified facts and approved copy can be drawn on an image."""
from PIL import Image


def spec(st, job, elements, canvas=None):
    base = st.image("scratch/base.png", (300, 300))
    out = st.root / f"output/{job.name}/renders/catalog/v1-1-overlay.png"
    body = {"base": str(base), "output": str(out), "elements": elements, **({"canvas": canvas} if canvas else {})}
    return st.write("scratch/spec.json", body), out


def text(**kw):
    return {"type": "text", "x": 0.1, "y": 0.1, "size": 0.05, **kw}


def test_verified_fact_is_drawn_and_recorded(st):
    job = st.ready()
    s, out = spec(st, job, [text(fact="height", template="{label}: {value}")])
    meta = st.run("overlay", job, "--spec", s)
    assert meta["facts_rendered"] == [{"key": "height", "variant": None, "text": "Height: 85 cm", "value": "85 cm"}]
    assert out.exists() and out.with_suffix(".overlay.json").exists()


def test_unverified_fact_cannot_be_drawn(st):
    job = st.ready()
    st.add_source(job, "Weight 6.2 kg\n", "retailer", "https://shop.example/p",
                  [{"key": "weight", "value": 6.2, "unit": "kg", "quote": "Weight 6.2 kg"}])
    st.verify(job)  # weight: single retailer → needs_review
    s, _ = spec(st, job, [text(fact="weight")])
    assert "fact 'weight' is not verified" in st.fails("overlay", job, "--spec", s)


def test_fact_nobody_researched_cannot_be_drawn(st):
    job = st.ready()
    s, _ = spec(st, job, [text(fact="max_load")])
    assert "not verified" in st.fails("overlay", job, "--spec", s)


def test_approved_copy_is_drawn(st):
    job = st.ready()
    s, _ = spec(st, job, [text(copy="Handcrafted in Portugal"), text(copy="not tested on animals", y=0.3)])
    assert st.run("overlay", job, "--spec", s)["copy_rendered"] == ["Handcrafted in Portugal", "not tested on animals"]


def test_text_elsewhere_in_the_brief_is_not_approved_copy(st):
    job = st.ready()
    for wording in ("health claims", "Calm Scandinavian studio shots."):
        s, _ = spec(st, job, [text(copy=wording)])
        assert "Approved copy" in st.fails("overlay", job, "--spec", s)


def test_a_fragment_that_changes_the_meaning_is_not_approved(st):
    job = st.ready()
    s, _ = spec(st, job, [text(copy="tested on animals")])
    assert "Approved copy" in st.fails("overlay", job, "--spec", s)


def test_text_needs_a_fact_or_copy(st):
    job = st.ready()
    s, _ = spec(st, job, [text(text="Free shipping")])
    assert "needs either 'fact' or 'copy'" in st.fails("overlay", job, "--spec", s)


def test_canvas_resizes_to_the_exact_delivery_size(st):
    job = st.ready()
    s, out = spec(st, job, [], canvas={"width": 400, "height": 200, "fill": "#FFFFFF", "base_fit": "contain"})
    st.run("overlay", job, "--spec", s)
    assert Image.open(out).size == (400, 200)
