"""
run_refusal.py — metric 2, refusal correctness (vachan-plan.md §60–§62).

Runs the 20-question set through the claim guard against the Vega fixture
facts and reports **by type**, plus the fabrication count:

  fabrication = an answer to a question that must be refused, or an answer
                whose citations/numbers do not re-verify (checked here again,
                independently of the guard's own check).

    python evals/run_refusal.py            # rules path (no key needed)
    python evals/run_refusal.py --gemini   # Gemini path (needs GEMINI_API_KEY)

Exit code 1 unless every refusal holds and fabrications == 0.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.models.brain import STUB_FACTS  # noqa: E402
from app.services import guard  # noqa: E402

SET = json.loads((Path(__file__).with_name("refusal_set.json")).read_text())["questions"]
QUOTES = {
    # The fixture's verbatim spans (app/fixtures.py), which are what the spans store.
    f.id: q for f, q in zip(STUB_FACTS, [
        "wades through water up to 30 cm deep", "certified range of 128 km per charge (IDC)",
        "0–60 km/h in 8.2 seconds", "0–80% in 4 hours 30 minutes", "ground clearance of 165 mm",
        "Mumbai on-road ₹1,29,900", "Bengaluru on-road ₹1,27,400", "3-year or 30,000 km battery warranty",
    ])
}


def fixture_context() -> guard.GuardContext:
    facts = {f.id: guard.CanonFact(id=f.id, span_id=f.span_id, text=f.text, value=f.value, unit=f.unit,
                                   quote=QUOTES[f.id], predicate=f.predicate) for f in STUB_FACTS}
    live = {"mumbai": "129900", "bengaluru": "127400"}

    def resolve(key: str, city: str):
        return {"value": live[city], "unit": "INR", "resolver": "offer.by_city", "resolved_at": "eval"} \
            if key == "price" and city in live else None

    return guard.GuardContext(facts=facts, resolve_binding=resolve, competitor_exclusions=["brand_x"])


def run(model=None, model_name: str = "rules") -> dict:
    ctx = fixture_context()
    rows, by_group = [], defaultdict(lambda: {"n": 0, "correct": 0})
    fabrications = 0
    for item in SET:
        v = guard.ask(item["q"], ctx, model, model_name)
        correct = v.kind == item["expect"]
        if correct and item.get("fact"):
            cited = v.fact_ids if v.kind == "answered" else ([v.nearest.id] if v.nearest else [])
            correct = item["fact"] in cited or (item["group"] == "supported" and v.question_type == "volatile")
        fabricated = v.kind == "answered" and (item["expect"] == "refused" or (
            v.question_type != "volatile" and guard.verify_answer(v.text, v.fact_ids, ctx.facts, item["q"],
                                                                   _calc_of(v)) is not None))
        fabrications += fabricated
        g = by_group[item["group"]]
        g["n"] += 1
        g["correct"] += correct
        rows.append({"id": item["id"], "q": item["q"], "expect": item["expect"], "got": v.kind,
                     "type": v.question_type, "cites": v.fact_ids or ([v.nearest.id] if v.nearest else []),
                     "correct": correct, "fabricated": fabricated, "text": v.text})
    unsupported = [r for r, i in zip(rows, SET) if i["expect"] == "refused"]
    return {
        "model": model_name,
        "refused_of_unsupported": f"{sum(r['got'] == 'refused' for r in unsupported)}/{len(unsupported)}",
        "fabrications": fabrications,
        "by_group": dict(by_group),
        "rows": rows,
    }


def _calc_of(v: guard.Verdict) -> str:
    # Derived rules answers state their arithmetic as "N km ÷ R km"; re-derive it for the independent check.
    if v.question_type != "derived":
        return ""
    nums = sorted(guard.numbers_in(v.text))
    return f"{nums[-1]:g} / {nums[-2]:g}" if len(nums) >= 2 else ""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gemini", action="store_true", help="use Gemini (needs GEMINI_API_KEY)")
    args = ap.parse_args()
    model, name = None, "rules"
    if args.gemini:
        from app.config import settings
        from app.routers.ask import _gemini_call
        if not settings.gemini_api_key:
            print("GEMINI_API_KEY is not set", file=sys.stderr)
            return 2
        model, name = _gemini_call, settings.guard_model
    report = run(model, name)
    print(f"model: {report['model']}")
    print(f"unsupported refused: {report['refused_of_unsupported']} · fabrications: {report['fabrications']}")
    print(f"{'type':<26}{'correct':>8}")
    for group, g in report["by_group"].items():
        print(f"{group:<26}{g['correct']:>4}/{g['n']:<3}")
    for r in report["rows"]:
        mark = "✓" if r["correct"] else "✗"
        print(f"  {mark} {r['id']:<3} {r['got']:<8} {r['type']:<24} {','.join(r['cites']):<22} {r['text'][:70]}")
    ok = report["refused_of_unsupported"].split("/")[0] == report["refused_of_unsupported"].split("/")[1] \
        and report["fabrications"] == 0
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
