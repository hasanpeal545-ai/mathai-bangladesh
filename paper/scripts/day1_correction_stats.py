"""Day 1: summarise the Chapter 2 LLM OCR-correction logs (backend/data/comparison/*.json)."""
import json, glob, os, re, csv, collections
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CMP = os.path.join(ROOT, "backend", "data", "comparison")
OUT = os.path.join(ROOT, "paper", "results")

MATH = set("∈∉∪∩∅∴∵⊂⊆⊃⊇×÷−≤≥≠√∞∖∑∏πθ°±→⇒⇔∀∃")
SUP = set("⁰¹²³⁴⁵⁶⁷⁸⁹ⁿˣʸ⁺⁻")
BN_DIG = set("০১২৩৪৫৬৭৮৯")
EN_DIG = set("0123456789")
BRACK = set("{}()[]")

def category(b, a):
    sb, sa = set(b), set(a)
    if a.strip() == "":
        return "deletion (noise removed)"
    if (sa & SUP) and not (sb & SUP):
        return "superscript / exponent"
    if (sa & MATH) - sb:
        return "math symbol"
    if ((sb & BN_DIG) and (sa & EN_DIG)) or ((sb & EN_DIG) and (sa & BN_DIG)):
        return "Bangla/Latin digit swap"
    if re.sub(r"[{}()\[\]]", "", b) == re.sub(r"[{}()\[\]]", "", a) and b != a:
        return "bracket / set notation"
    if (sa & BRACK) != (sb & BRACK) and len(a) < 20:
        return "bracket / set notation"
    if re.sub(r"\s|,|\.|।", "", b) == re.sub(r"\s|,|\.|।", "", a):
        return "punctuation / spacing"
    return "other (word / mixed)"

rows, cats_all = [], collections.Counter()
by_lang = collections.defaultdict(collections.Counter)
examples = collections.defaultdict(list)
for f in sorted(glob.glob(os.path.join(CMP, "*.json"))):
    d = json.load(open(f, encoding="utf-8"))
    # Chapter 2 pages are the bn_/en_ files; some have chapter=None (metadata bug), page_15 is a test file
    if not os.path.basename(f).startswith(("bn_", "en_")):
        continue
    d.setdefault("language", os.path.basename(f)[:2])
    ch = d.get("changes", [])
    c = collections.Counter(category(x.get("before", ""), x.get("after", "")) for x in ch)
    for x in ch:
        k = category(x.get("before", ""), x.get("after", ""))
        if len(examples[k]) < 6:
            examples[k].append((d["language"], d["page"], x.get("before"), x.get("after")))
    cats_all.update(c); by_lang[d["language"]].update(c)
    rows.append({"file": os.path.basename(f), "language": d["language"], "page": d["page"],
                 "raw_chars": len(d.get("raw", "")), "fixed_chars": len(d.get("fixed", "")),
                 "changes_count": d.get("changes_count", len(ch)),
                 "improvement_score": d.get("improvement_score")})

with open(os.path.join(OUT, "day1_per_page.csv"), "w", newline="", encoding="utf-8-sig") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
cats = sorted(cats_all, key=lambda k: -cats_all[k])
with open(os.path.join(OUT, "day1_by_category.csv"), "w", newline="", encoding="utf-8-sig") as fh:
    w = csv.writer(fh); w.writerow(["category", "bn", "en", "total", "percent"])
    tot = sum(cats_all.values())
    for k in cats:
        w.writerow([k, by_lang["bn"][k], by_lang["en"][k], cats_all[k], round(100*cats_all[k]/tot, 1)])
with open(os.path.join(OUT, "day1_examples.json"), "w", encoding="utf-8") as fh:
    json.dump(examples, fh, ensure_ascii=False, indent=1)

tot = sum(cats_all.values())
for lang in ("bn", "en"):
    rs = [r for r in rows if r["language"] == lang]
    print(f"{lang}: pages={len(rs)} (p{min(r['page'] for r in rs)}-{max(r['page'] for r in rs)}), "
          f"changes={sum(r['changes_count'] for r in rs)}, raw_chars={sum(r['raw_chars'] for r in rs)}, "
          f"mean_improvement_score={sum(r['improvement_score'] or 0 for r in rs)/len(rs):.4f}")
print("TOTAL pages", len(rows), "changes", tot)
for k in cats:
    print(f"  {k:28s} bn={by_lang['bn'][k]:4d} en={by_lang['en'][k]:4d} total={cats_all[k]:4d} ({100*cats_all[k]/tot:.1f}%)")
