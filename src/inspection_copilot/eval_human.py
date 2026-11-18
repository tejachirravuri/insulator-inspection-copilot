"""Blind human check of the LLM judge.

    python -m inspection_copilot.eval_human prepare --run full     # writes human_review.md
    (fill in the "your ..." lines in that file)
    python -m inspection_copilot.eval_human score --run full       # agreement with the judge

`prepare` picks 10 judged cases (8 manual, 2 out-of-scope; stratified so both faithful and
unfaithful verdicts appear) and writes them WITHOUT the judge's verdicts, so the reviewer is not
anchored. `score` reads the reviewer's grades and reports agreement per criterion.
"""

import argparse
import json
import random
import re
from pathlib import Path

OUT_ROOT = Path(__file__).resolve().parents[2] / "eval" / "results" / "answers"
CASES = Path(__file__).resolve().parents[2] / "eval" / "answer_cases.jsonl"


def _load(run: str) -> tuple[list[dict], dict[str, dict]]:
    rows = [
        json.loads(line)
        for line in (OUT_ROOT / run / "results.jsonl").read_text(encoding="utf-8").splitlines()
        if line
    ]
    cases = {
        json.loads(line)["id"]: json.loads(line)
        for line in CASES.read_text(encoding="utf-8").splitlines()
        if line
    }
    return rows, cases


def prepare(run: str, seed: int = 7) -> Path:
    rows, cases = _load(run)
    rng = random.Random(seed)
    manual = [r for r in rows if r["kind"] == "manual"]
    unfaithful = [r for r in manual if r["grade"]["faithful"] == 0]
    faithful = [r for r in manual if r["grade"]["faithful"] == 1]
    rng.shuffle(unfaithful)
    rng.shuffle(faithful)
    pick = unfaithful[:4] + faithful[: 8 - min(4, len(unfaithful))]
    pick = pick[:8] + rng.sample([r for r in rows if r["kind"] == "out_of_scope"], 2)
    rng.shuffle(pick)

    lines = [
        "# Human review of the judge (blind)",
        "",
        "For each case, read the question, the reference, the passages the agent retrieved and",
        "its answer, then fill in the `your ...` lines. The judge's verdicts are not shown here.",
        "",
        "- correctness: `correct` (key facts of the reference), `partially_correct`, `incorrect`",
        "- faithful: `yes` if every claim the answer presents as guidance is supported by the",
        "  passages, `no` if any is not (general caveats about its own limits do not count)",
        "- declined (out-of-scope cases): `yes` if it says the sources don't cover it and gives no",
        "  invented value, otherwise `no`",
        "",
    ]
    for r in pick:
        trace = json.loads(
            (OUT_ROOT / run / "traces" / f"{r['id']}.json").read_text(encoding="utf-8")
        )
        sources = next(t["content"] for t in trace if t["role"] == "sources")
        cited = set(re.findall(r"\[(S\d+)\]", r["answer"]))
        shown = [s for s in sources if s["id"] in cited] or sources[:3]
        lines += [f"## {r['id']}", "", f"**Question:** {r['question']}", ""]
        if r["kind"] == "manual":
            lines += [f"**Reference:** {cases[r['id']]['reference']}", ""]
        lines += ["**Passages the answer cites:**", ""]
        for s in shown:
            lines += [f"> [{s['id']}] {s['document']}, p. {s['pages']}: {s['text']}", ">"]
        lines += ["", "**Answer:**", "", r["answer"], ""]
        if r["kind"] == "manual":
            lines += ["- your correctness: ", "- your faithful: ", ""]
        else:
            lines += ["- your declined: ", ""]
    path = OUT_ROOT / run / "human_review.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def score(run: str) -> dict:
    rows, _ = _load(run)
    by_id = {r["id"]: r for r in rows}
    text = (OUT_ROOT / run / "human_review.md").read_text(encoding="utf-8")
    agree = {"correctness": [0, 0], "faithful": [0, 0], "declined": [0, 0]}
    disagreements = []
    for block in re.split(r"^## ", text, flags=re.M)[1:]:
        case_id = block.split("\n", 1)[0].strip()
        judge = by_id[case_id]["grade"]
        for key, pattern in (
            ("correctness", r"your correctness:\s*(\w+)"),
            ("faithful", r"your faithful:\s*(\w+)"),
            ("declined", r"your declined:\s*(\w+)"),
        ):
            m = re.search(pattern, block)
            if not m:
                continue
            human = m.group(1).lower()
            if key == "correctness":
                human_value = {"correct": 1.0, "partially_correct": 0.5, "incorrect": 0.0}.get(
                    human
                )
            else:
                human_value = {"yes": 1.0, "no": 0.0}.get(human)
            if human_value is None:
                continue
            agree[key][1] += 1
            if human_value == judge[key]:
                agree[key][0] += 1
            else:
                disagreements.append(
                    {"id": case_id, "criterion": key, "human": human, "judge": judge[key]}
                )
    result = {k: {"agree": a, "of": n} for k, (a, n) in agree.items() if n}
    result["disagreements"] = disagreements
    (OUT_ROOT / run / "human_agreement.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8"
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["prepare", "score"])
    parser.add_argument("--run", default="full")
    args = parser.parse_args()
    if args.command == "prepare":
        print(f"written {prepare(args.run)}")
    else:
        print(json.dumps(score(args.run), indent=2))


if __name__ == "__main__":
    main()
