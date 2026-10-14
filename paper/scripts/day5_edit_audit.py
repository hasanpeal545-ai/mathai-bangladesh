"""Day 5 / Task C: audit the Groq math-notation-fix edits (backend/data/comparison/
bn_page_N.json "changes": before -> after) against Peal's hand-verified ground truth,
for the 3 verified Bangla pages.

How each edit is matched back to a ground-truth position:
The JSON's "changes" list does not store word-index positions, only the before/after
strings -- but it was generated (in backend/ingestion/pdf_extractor.py's
compute_changes()) by running difflib.SequenceMatcher(None, raw_words, fixed_words)
and keeping every non-'equal' opcode, in order. That's a deterministic function of
the "raw" and "fixed" strings, both of which are also stored in the same JSON --
so re-running the identical SequenceMatcher call reproduces the exact same opcode
list (verified: for all 3 pages, the regenerated before/after list matches the
stored "changes" list exactly, word for word). This gives back the (i1,i2) word range
in raw and (j1,j2) word range in fixed for every edit.

To find "what does the ground truth say at that place" for 'before' and 'after'
independently:
  1. Align raw_words -> gt_words and fixed_words -> gt_words separately (two
     word-level SequenceMatcher alignments, same technique as elsewhere in this
     project).
  2. For an edit's raw range (i1,i2), union the GT word-ranges of every raw<->GT
     opcode that overlaps (i1,i2) to get the GT snippet "at that place" for 'before'.
     Same for the edit's fixed range (j1,j2) against the fixed<->GT alignment, for
     'after'.
  3. Compare (after whitespace-removal + NFC normalisation, same as day5_cer.py):
       before_matches_gt = before == snippet_from_raw_alignment (and snippet non-empty)
       after_matches_gt  = after  == snippet_from_fixed_alignment (and snippet non-empty)
     label:
       "fixed"            if after_matches_gt and not before_matches_gt
       "harmful"          if before_matches_gt and not after_matches_gt
       "neutral/unclear"  otherwise (covers: both match, neither match, or the
                           snippet was empty/ambiguous -- i.e. exactly the
                           "when uncertain, choose unclear, never guess fixed" rule)

A failure mode found and fixed while building this: when the src<->GT alignment is
poor in the *neighbourhood* of a tiny 1-2 word edit (other garbled words nearby,
reordering), difflib can fold that edit into one huge opcode spanning many
unrelated words, making the unioned "snippet at that place" many times longer than
the edit -- comparing a 1-word 'after' against a 10-word unrelated snippet always
fails and was defaulting to a false "harmful" label. Fixed with a bound: if the
unioned GT snippet is more than ~3x the edit's own word count, it's treated as
unreliable (empty), which correctly falls through to "neutral/unclear" instead of
a wrong "harmful" guess.
"""
import csv
import difflib
import json
import os
import re
import sys
import unicodedata

sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GT_DIR = os.path.join(ROOT, "paper", "ground_truth")
COMPARISON_DIR = os.path.join(ROOT, "backend", "data", "comparison")
OUT_CSV = os.path.join(ROOT, "paper", "results", "day5_edit_audit.csv")

PAGES = [30, 36, 44]


def norm(text):
    return re.sub(r"\s+", "", unicodedata.normalize("NFC", text))


def read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def regenerate_changes_with_positions(raw_words, fixed_words):
    matcher = difflib.SequenceMatcher(None, raw_words, fixed_words)
    changes = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        changes.append(
            {
                "before": " ".join(raw_words[i1:i2]),
                "after": " ".join(fixed_words[j1:j2]),
                "raw_range": (i1, i2),
                "fixed_range": (j1, j2),
            }
        )
    return changes


def gt_snippet_for_range(src_words, gt_words, src_range, max_snippet_words):
    """Aligns src_words -> gt_words and returns the GT word snippet corresponding
    to src_range = (lo, hi), by unioning the GT ranges of every alignment opcode
    that overlaps src_range. Returns '' if nothing overlaps (ambiguous/no match).

    Guard against a real failure mode: when the src<->GT alignment is poor in the
    *neighbourhood* of this edit (e.g. other garbled words nearby, or reordering),
    difflib can fold a tiny 1-2 word edit into one huge 'replace' opcode spanning
    many unrelated words on both sides. Unioning that opcode's GT range would then
    hand back a snippet many times longer than the edit itself -- clearly not "the
    ground truth at that place", just alignment noise. If the snippet is more than
    max_snippet_words long, treat it as unreliable and return '' (which, in
    audit_page, correctly falls through to "neutral/unclear" rather than being
    compared -- this is the mechanism implementing DAY5.md's "when uncertain,
    choose unclear, never guess fixed")."""
    lo, hi = src_range
    matcher = difflib.SequenceMatcher(None, src_words, gt_words)
    gt_lo, gt_hi = None, None
    for tag, a1, a2, b1, b2 in matcher.get_opcodes():
        if a2 <= lo or a1 >= hi:
            continue  # no overlap with the edit's src range
        gt_lo = b1 if gt_lo is None else min(gt_lo, b1)
        gt_hi = b2 if gt_hi is None else max(gt_hi, b2)
    if gt_lo is None:
        return ""
    if (gt_hi - gt_lo) > max_snippet_words:
        return ""
    return " ".join(gt_words[gt_lo:gt_hi])


def audit_page(page):
    gt_text = read(os.path.join(GT_DIR, f"bn_page_{page}.txt"))
    cmp_json = json.load(open(os.path.join(COMPARISON_DIR, f"bn_page_{page}.json"), encoding="utf-8"))
    raw_words = cmp_json["raw"].split()
    fixed_words = cmp_json["fixed"].split()
    gt_words = gt_text.split()

    changes = regenerate_changes_with_positions(raw_words, fixed_words)
    # Sanity check: must reproduce the stored changes list exactly (verified
    # manually before writing this script; re-checked here defensively).
    stored = cmp_json["changes"]
    regen_pairs = [{"before": c["before"], "after": c["after"]} for c in changes]
    if regen_pairs != stored:
        print(f"  [WARNING] page {page}: regenerated changes list does NOT match stored JSON -- audit positions may be unreliable for this page")

    results = []
    for c in changes:
        edit_word_count = max(len(c["before"].split()), len(c["after"].split()), 1)
        # Small additive buffer for tokenisation slop, floored at 4 so a 1-word edit
        # still gets a little local context (word-level alignment near a short
        # fragment often needs +-1-2 words of slack even when it's a clean match).
        max_snippet_words = max(edit_word_count + 2, 4)
        snippet_raw = gt_snippet_for_range(raw_words, gt_words, c["raw_range"], max_snippet_words)
        snippet_fixed = gt_snippet_for_range(fixed_words, gt_words, c["fixed_range"], max_snippet_words)

        before_n, after_n = norm(c["before"]), norm(c["after"])
        snippet_raw_n, snippet_fixed_n = norm(snippet_raw), norm(snippet_fixed)

        # A side only counts as "confidently resolved" if its GT snippet survived
        # the size guard above (non-empty). An unreliable/empty snippet means we
        # genuinely don't know whether that side matches GT -- that must NOT be
        # silently treated as "doesn't match" (which is what a plain `bool(x) and
        # x==y` check would do), or an unconfirmed 'after' falls through to a
        # false "harmful" via the elif below. Both sides must be confident before
        # fixed/harmful is attempted at all; otherwise -> neutral/unclear.
        before_confident = bool(snippet_raw_n)
        after_confident = bool(snippet_fixed_n)
        before_matches_gt = before_confident and before_n == snippet_raw_n
        after_matches_gt = after_confident and after_n == snippet_fixed_n

        if not (before_confident and after_confident):
            label = "neutral/unclear"
        elif after_matches_gt and not before_matches_gt:
            label = "fixed"
        elif before_matches_gt and not after_matches_gt:
            label = "harmful"
        else:
            label = "neutral/unclear"

        note = f"GT@before-pos='{snippet_raw}' | GT@after-pos='{snippet_fixed}'"
        results.append(
            {
                "page": page,
                "before": c["before"],
                "after": c["after"],
                "label": label,
                "note": note,
            }
        )
    return results


def main():
    all_rows = []
    for page in PAGES:
        all_rows.extend(audit_page(page))

    os.makedirs(os.path.dirname(OUT_CSV), exist_ok=True)
    fieldnames = ["page", "before", "after", "label", "note"]
    with open(OUT_CSV, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(all_rows)

    counts = {}
    for r in all_rows:
        counts[r["label"]] = counts.get(r["label"], 0) + 1

    print(f"Wrote {os.path.relpath(OUT_CSV, ROOT)} ({len(all_rows)} edits audited)")
    print("Label counts:")
    for label in ["fixed", "harmful", "neutral/unclear"]:
        print(f"  {label}: {counts.get(label, 0)}")


if __name__ == "__main__":
    main()
