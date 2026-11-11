"""Fact-check policy: what counts as verified, what is a conflict, and that nothing unsupported slips through."""
import pytest

from lib.factcheck import canon, same_value, value_in_quote

H = {"key": "height", "label": "Height", "value": 85, "unit": "cm", "quote": "Height: 85 cm"}
PAGE = "Lounge chair\nHeight: 85 cm\nFrame: oak\n"


def job_with(st, *sources, brief="# Brief\n"):
    """sources: (tier, url, text, facts[, same_product])"""
    job = st.job(brief=brief)
    st.run("init", job)
    for tier, url, text, facts, *rest in sources:
        st.add_source(job, text, tier, url, facts, *rest)
    return job


# ── value comparison ──

@pytest.mark.parametrize("a, b, same", [
    ((85, "cm"), (850, "mm"), True),
    ((85, "cm"), (33.5, "in"), True),       # 85.09 cm, inside the 2% tolerance
    ((85, "cm"), (90, "cm"), False),
    ((85, "cm"), (85, "kg"), False),        # different dimension
    (("solid white oak", None), ("White oak, solid", None), True),
    (("oak", None), ("oak veneer", None), False),
    (("cotton", None), ("60% cotton 40% polyester", None), False),
])
def test_same_value(a, b, same):
    assert same_value(canon(*a), canon(*b)) is same


def test_value_must_occur_in_its_quote():
    assert value_in_quote(85, "Height: 85 cm")
    assert not value_in_quote(85, "Height: 185 cm")
    assert value_in_quote("solid white oak", "Frame: solid white oak")
    assert not value_in_quote("walnut", "Frame: solid white oak")


# ── status per fact ──

def test_single_manufacturer_source_verifies(st):
    job = job_with(st, ("manufacturer", "https://brand.example/p", PAGE, [H]))
    f = st.fact(st.verify(job), "height")
    assert f["status"] == "verified" and "manufacturer: brand.example" in f["basis"]
    assert f["evidence"][0]["quote"] == "Height: 85 cm" and f["evidence"][0]["url"] == "https://brand.example/p"


def test_single_retailer_source_needs_review(st):
    job = job_with(st, ("retailer", "https://shop.example/p", PAGE, [H]))
    assert st.fact(st.verify(job), "height")["status"] == "needs_review"


def test_two_retailers_on_different_domains_verify(st):
    job = job_with(st, ("retailer", "https://shop.example/p", PAGE, [H]),
                   ("distributor", "https://trade.example/p", PAGE + "x", [H]))
    f = st.fact(st.verify(job), "height")
    assert f["status"] == "verified" and "2 independent" in f["basis"]


def test_two_pages_of_the_same_domain_do_not_corroborate(st):
    job = job_with(st, ("retailer", "https://shop.example/a", PAGE, [H]), ("retailer", "https://www.shop.example/b", PAGE + "x", [H]))
    assert st.fact(st.verify(job), "height")["status"] == "needs_review"


def test_other_tier_sources_never_verify_however_many_agree(st):
    job = job_with(st, ("other", "https://forum.example/t", PAGE, [H]), ("other", "https://blog.example/r", PAGE + "x", [H]),
                   ("other", "https://reviews.example/r", PAGE + "y", [H]))
    f = st.fact(st.verify(job), "height")
    assert f["status"] == "needs_review" and "other" in f["basis"]


def test_sources_without_a_url_do_not_corroborate(st):
    job = job_with(st, ("retailer", None, PAGE, [H]), ("retailer", None, PAGE + "x", [H]))
    assert st.fact(st.verify(job), "height")["status"] == "needs_review"


def test_unclear_product_match_demotes_a_manufacturer_source(st):
    job = job_with(st, ("manufacturer", "https://brand.example/family", PAGE, [H], "unclear"))
    assert st.fact(st.verify(job), "height")["status"] == "needs_review"


def test_source_about_another_product_is_rejected(st):
    job = job_with(st, ("manufacturer", "https://brand.example/other", PAGE, [H], "no"))
    assert st.fact(st.verify(job), "height")["status"] == "rejected"


def test_disagreeing_secondary_sources_are_a_conflict(st):
    other = {**H, "value": 90, "quote": "Height: 90 cm"}
    job = job_with(st, ("retailer", "https://a.example/p", PAGE, [H]), ("retailer", "https://b.example/p", "Height: 90 cm\n", [other]))
    f = st.fact(st.verify(job), "height")
    assert f["status"] == "conflict" and sorted(c["value"] for c in f["conflicts"]) == [85, 90]


def test_text_values_that_only_overlap_are_a_conflict(st):
    oak = {"key": "material", "value": "oak", "quote": "Frame: oak"}
    veneer = {"key": "material", "value": "oak veneer", "quote": "Frame: oak veneer"}
    job = job_with(st, ("retailer", "https://a.example/p", PAGE, [oak]), ("retailer", "https://b.example/p", "Frame: oak veneer\n", [veneer]))
    assert st.fact(st.verify(job), "material")["status"] == "conflict"


def test_client_value_settles_a_conflict(st):
    other = {**H, "value": 90, "quote": "Height: 90 cm"}
    job = job_with(st, ("retailer", "https://a.example/p", "Height: 90 cm\n", [other]), brief="# Brief\n\n## Known facts\n- Height: 85 cm\n")
    st.extract(job, "S0", [H])
    f = st.fact(st.verify(job), "height")
    assert (f["status"], f["value"], f["basis"].split(";")[0]) == ("verified", 85, "client-approved brief")
    assert f["conflicts"][0]["value"] == 90


def test_variants_are_kept_apart(st):
    m = {"key": "chest", "value": 100, "unit": "cm", "variant": "M", "quote": "M: chest 100 cm"}
    l = {"key": "chest", "value": 108, "unit": "cm", "variant": "L", "quote": "L: chest 108 cm"}
    job = job_with(st, ("manufacturer", "https://brand.example/p", "M: chest 100 cm\nL: chest 108 cm\n", [m, l]))
    v = st.verify(job)
    assert (st.fact(v, "chest", "M")["value"], st.fact(v, "chest", "L")["value"]) == (100, 108)
    assert v["summary"]["conflict"] == 0


# ── nothing unsupported gets through ──

def test_quote_that_is_not_in_the_source_is_rejected(st):
    job = job_with(st, ("manufacturer", "https://brand.example/p", PAGE, [{**H, "value": 120, "quote": "Height: 120 cm"}]))
    v = st.verify(job)
    assert st.fact(v, "height")["status"] == "rejected"
    assert v["rejected_claims"][0]["checks"]["quote_found"] is False


def test_value_that_is_not_in_its_quote_is_rejected(st):
    job = job_with(st, ("manufacturer", "https://brand.example/p", PAGE, [{**H, "value": 58}]))
    assert st.fact(st.verify(job), "height")["status"] == "rejected"


@pytest.mark.parametrize("verdict", [
    {"verdict": "not_found", "evidence": ""},
    {"verdict": "contradicted", "evidence": "Height: 85 cm", "correct_value": "85 cm"},
    {"verdict": "supported", "evidence": "Height is eighty-five centimetres"},   # evidence not in the source
])
def test_claim_the_independent_checker_does_not_support_is_rejected(st, verdict):
    job = job_with(st, ("manufacturer", "https://brand.example/p", PAGE, [H]))
    assert st.fact(st.verify(job, verdicts={"F1": verdict}), "height")["status"] == "rejected"


def test_verify_refuses_without_a_verdict_for_every_claim(st):
    job = job_with(st, ("manufacturer", "https://brand.example/p", PAGE, [H]))
    st.run("verify", job, "--prepare")
    st.write(f"output/{job.name}/factcheck/verdicts.json", {"verdicts": []})
    assert "no verdict yet for 1 claim" in st.fails("verify", job)


def test_verify_refuses_when_the_draft_changed_after_prepare(st):
    job = job_with(st, ("manufacturer", "https://brand.example/p", PAGE, [H]))
    st.check(job)
    st.add_source(job, "Weight 6 kg\n", "retailer", "https://a.example/p", [{"key": "weight", "value": 6, "unit": "kg", "quote": "Weight 6 kg"}])
    assert "changed since `verify --prepare`" in st.fails("verify", job)


def test_checker_never_sees_the_extractors_quotes(st):
    job = job_with(st, ("manufacturer", "https://brand.example/p", PAGE, [H]))
    st.run("verify", job, "--prepare")
    assert "quote" not in st.read(f"output/{job.name}/factcheck/claims.json")["sources"][0]["claims"][0]


def test_without_the_independent_check_nothing_but_client_facts_is_verified(st):
    job = job_with(st, ("manufacturer", "https://brand.example/p", PAGE, [H]))
    st.run("verify", job, "--deterministic-only")
    assert st.fact(st.read(f"output/{job.name}/factcheck/facts.verified.json"), "height")["status"] == "needs_review"


def test_missing_required_fact_exits_non_zero_but_still_writes_the_report(st):
    job = job_with(st, ("manufacturer", "https://brand.example/p", PAGE, [H]))
    st.check(job)
    assert st.fails("verify", job, "--require", "height,weight") == "2"
    v = st.read(f"output/{job.name}/factcheck/facts.verified.json")
    assert (v["required"], v["missing_required"]) == (["height", "weight"], ["weight"])


def test_human_override_is_recorded_as_such(st):
    job = job_with(st, ("retailer", "https://shop.example/p", PAGE, [H]))
    st.run("override", job, "--key", "weight", "--value", "6.2", "--unit", "kg", "--note", "client email 2026-11-06")
    st.run("override", job, "--key", "height", "--reject", "--note", "wrong model")
    v = st.verify(job)
    assert st.fact(v, "weight")["basis"] == "human override: client email 2026-11-06"
    assert (st.fact(v, "weight")["status"], st.fact(v, "height")["status"]) == ("verified", "rejected")
