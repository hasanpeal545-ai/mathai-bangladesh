"""FULL_OCR / Steps 2-3e: Gemini Vision OCR of every NCTB math book (paid tier).

*** Step 3e (2026-10-07) FINAL SETTINGS -- no more API tests after this, per
FULL_OCR.md: "No more API tests." ***
  - Model: gemini-3.5-flash-lite, called via raw REST (requests), NOT the
    google-generativeai SDK -- that SDK (0.8.2, installed in backend/venv,
    untouched by this file) cannot express thinkingConfig at all (confirmed in
    Step 3d by inspecting its compiled proto types directly) and separately has
    a real bug where its own `.text` property crashes on an empty candidate
    (Step 3b). REST sidesteps both issues entirely.
  - thinkingConfig.thinkingLevel = "minimal" on every call (the literal lowest
    of minimal/low/medium/high, confirmed via the API's own error messages in
    Step 3d -- this is what actually removed the multi-thousand-hidden-token
    overhead measured in every call before Step 3d; see
    paper/results/FULL_OCR_MODEL_TEST.md).
  - Prompt: unchanged since Step 3c (base Day 2 prompt + margin-ignore +
    plain-fraction instructions; the Step 3b digit-care sentence stays removed).
  - NEW in Step 3e: a free, local LaTeX-to-plain post-processing pass (see
    latex_to_plain() below) -- Step 3d found that thinkingLevel=minimal makes
    the model more likely to fall back to LaTeX formatting ($...$, \\cup, etc.)
    on set-notation-dense pages, violating the prompt's own "not LaTeX"
    instruction; this cleans that up after the fact rather than relying on the
    model to never do it.

Output ONLY goes to:
  backend/data/ocr_gemini/<book_name>/page_N.txt           (primary, post-processed)
  backend/data/ocr_gemini/<book_name>/page_N.raw.txt       (primary, unprocessed API text)
  backend/data/ocr_gemini/<book_name>/page_N.alt.txt       (bn only: 2nd reading @ temp 0.4, post-processed)
  backend/data/ocr_gemini/<book_name>/page_N.alt.raw.txt   (bn only: 2nd reading, unprocessed)
  backend/data/ocr_gemini/RUN_LOG.csv                      (append-only call log, one row per API call)
  paper/check/digit_disagreements.csv                      (Step 3b.2: bn primary vs secondary digit diffs)
  paper/check/blocked_pages.csv                             (Step 3b.4: pages that fell back to Tesseract)
Nothing that already exists under backend/ (ocr_raw, ocr_fixed, comparison,
approved, Qdrant) is read for writing, or modified -- ocr_raw is read-only here,
used to pick good sample pages for --sample (math-density heuristic) AND as the
Step 3b.4 fallback source for RECITATION-blocked pages.

Books come from backend/data/curriculum.json (5 books x 2 languages = 10 distinct
books) -- the same list backend/run_full_ocr.py already uses, excluding the 4
class_10_*.pdf duplicate files (see paper/results/FULL_OCR_INVENTORY.md) --
but REORDERED per Step 3e.5 for the Step 4 full run: class_9_General (bn, en),
class_9_Hiher/Higher (bn, en), class_8 (bn, en), class_7 (bn, en), class_6 (bn, en)
-- see BOOK_ORDER below. (Default sequential/--sample iteration order now follows
this, not curriculum.json's own 6/7/8/9General/9Higher order.)

CLI:
  --books BOOK1,BOOK2     restrict to these book stems (default: all 10, in BOOK_ORDER)
  --max-pages N           stop after N NEWLY processed pages in this invocation
                          (already-done pages are skipped and don't count)
  --sample                pilot mode: 3 pages/book (start, middle, heaviest-math),
                          ignores --max-pages
  --pages book:page,...   explicit book:page targeting (Step 3c/3d's precise tests)
  --save-images-to DIR    also save each processed page's 300-DPI PNG to
                          DIR/<book>/page_N.png (Step 4's per-batch review copies)
  --force                 reprocess a page even if its output already exists
  --dry-run               print the page plan without calling Gemini or writing files

Policy for Bangla pages (Step 3b.2, unchanged by Step 3e): call Gemini TWICE per
page -- temperature 0 (primary) and temperature 0.4 (secondary) -- and diff the
two readings for digit disagreements (paper/check/digit_disagreements.csv).
English pages: one call only.

Safety:
  - Resumable: a page is skipped if its primary output file already exists and is
    non-empty (unless --force).
  - A failed call is retried up to 2 more times (3 attempts total) with backoff
    (2s, 4s) -- UNLESS the failure is a content-policy block (RECITATION etc.),
    which is deterministic and is not retried. A page where every available
    reading is blocked falls back to the existing Tesseract text (Step 3b.4).
  - Running cost is estimated from the API's own usageMetadata token counts
    (real numbers) x a price-per-token constant below. Step 3e price: real,
    OFFICIAL rate for gemini-3.5-flash-lite, verified directly on
    ai.google.dev/gemini-api/docs/pricing (not third-party-sourced, unlike the
    same number used provisionally in Step 3d): $0.30/1M input, $2.50/1M
    output (thinking tokens included in output price). Cumulative cost is
    computed by summing prior RUN_LOG.csv rows WHERE model == GEMINI_MODEL
    (i.e. only gemini-3.5-flash-lite rows) -- deliberately excludes the Steps
    2-3d rows made under gemini-3.6-flash at its own, higher real price, since
    mixing a different model's token counts into one price would both
    understate history and not match what "$7.00 total spend for Step 4"
    (FULL_OCR.md Step 3e.6) actually means once Step 4 is the only thing still
    calling the API. Step 3e.6: the stop threshold is now $7.00 (was $4.00).
"""
import argparse
import base64
import csv
import datetime
import difflib
import io
import itertools
import json
import os
import re
import sys
import time
import unicodedata

sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BACKEND_DIR = os.path.join(ROOT, "backend")
sys.path.insert(0, BACKEND_DIR)

from config import settings  # noqa: E402

import fitz  # noqa: E402
import requests  # noqa: E402
import sup  # noqa: E402 -- FIX_BATCH9 task 1: paper/scripts/sup.py, same dir as this script
from PIL import Image  # noqa: E402

API_BASE = "https://generativelanguage.googleapis.com/v1beta"
CURRICULUM_PATH = os.path.join(BACKEND_DIR, "data", "curriculum.json")
PDF_ROOT = os.path.join(BACKEND_DIR, "data", "pdfs", "2026")
OCR_RAW_ROOT = os.path.join(BACKEND_DIR, "data", "ocr_raw")
OUT_ROOT = os.path.join(BACKEND_DIR, "data", "ocr_gemini")
RUN_LOG_PATH = os.path.join(OUT_ROOT, "RUN_LOG.csv")
CHECK_DIR = os.path.join(ROOT, "paper", "check")
DIGIT_DISAGREEMENTS_PATH = os.path.join(CHECK_DIR, "digit_disagreements.csv")
BLOCKED_PAGES_PATH = os.path.join(CHECK_DIR, "blocked_pages.csv")

# Step 3e.1: final model choice, called via raw REST (see module docstring).
GEMINI_MODEL = "gemini-3.5-flash-lite"
THINKING_LEVEL = "minimal"  # the literal lowest of minimal/low/medium/high

DPI = 300
PRIMARY_TEMPERATURE = 0
SECONDARY_TEMPERATURE = 0.4  # bn pages only, Step 3b.2

# Base Day 2 prompt, unchanged, plus the Step 3b.1 addition -- MINUS the
# Bangla-digit-care sentence, removed again in Step 3c.1. Step 3c's own check
# (paper/check/ERRORS_LOG.csv re-review) found that sentence didn't reliably
# work anyway (page 156's primary reading was STILL wrong with it in the
# prompt) and it was one of the likely drivers of a large hidden-"thinking"-
# token cost increase (see paper/results/FULL_OCR_PILOT_RERUN.md) -- while the
# actual digit-error catch mechanism is the double bn reading + diff (Step
# 3b.2), not this sentence. Kept: the margin-ignore and plain-fraction
# instructions, which Step 3c's re-review found were NOT implicated in the
# accuracy problem and did measurably help (see FULL_OCR_PILOT_RERUN.md).
PROMPT = (
    "Transcribe this textbook page exactly as printed. Keep Bangla text in Bangla "
    "script and English in English. Write mathematical symbols as Unicode "
    "(∈ ∉ ∪ ∩ ∅ ∴ × − ⊂ ⊆ ∠ ∥ Δ ° ≠, superscripts "
    "like ² ⁿ). Keep line breaks. Do not correct, translate, summarise, add "
    "or skip anything. Output only the transcription. "
    "Ignore any text printed vertically in the page "
    "margin. Write fractions as a/b, not LaTeX. "
    "Mixed numbers like 2⁴⁄₅ must be written as `2 4/5` (whole part, space, "
    "fraction). Write every fraction on ONE line as a/b, never stacked over "
    "several lines. "
    "A dot printed ABOVE a digit marks a recurring decimal and MUST be kept: "
    "write that digit followed by U+0307 (e.g. 0.2̇4̇, 5.234̇57̇). Never drop "
    "these dots, and never read a dotted 1 as the letter i. Also keep "
    "fractions on one line as a/b even inside worked solutions. "
    # FIX_BATCH13 task 2: the prompt's own worked example was leaking into
    # output -- p129's real "AB = AC ≠ BC" came back as "AB = AC R̸ BC"
    # (the model literally copied the example's "R̸" placeholder symbol
    # instead of transcribing the page's actual ≠). Dropped the "x R̸ y"
    # example entirely rather than swapping it for a different placeholder,
    # which could leak the same way; named the real symbols instead.
    "Keep negation slashes on symbols exactly as printed (∉, ≠, ⊄) -- never "
    "drop them, and never replace one symbol with another. "
    "When a fraction multiplies something (a fraction coefficient), wrap the "
    "fraction in parentheses: write (1/27)(3a + 1), (1/2)x², f(−(1/2)a) -- "
    "never 1/27(3a + 1) or 1/2x², which read as a different expression. "
    "Keep digits in the same script as printed: Latin digits (0-9) stay "
    "Latin and Bangla digits (০-৯) stay Bangla -- never convert between "
    "them. "
    "Write exponents with Unicode superscripts (a², aᵐ⁺ⁿ) or as a^(…) when "
    "they contain fractions; keep each exponent attached to its base. "
    "Write log bases as log₂, log₁₀, logₐ, log_b. Never output LaTeX or "
    "HTML. "
    # FIX_BATCH12 task 2: Claude (chat)'s batch-12 review (ERRORS_LOG batch=12)
    # found a real word substitution again (প্রত্যেকটি -> প্রতিটি, page 29 --
    # same family as Step 3b's own প্রত্যেকটি->প্রতিটি finding) -- the model is
    # "correcting"/paraphrasing the book's own wording instead of transcribing
    # it verbatim. Appended, not inserted elsewhere, per the task's own
    # "append to the existing prompt" convention (Step 3b.1/Step 3c.1).
    "Transcribe exactly as printed -- do not replace any word with a synonym "
    "or 'correct' the book's wording."
)

# FIX_BATCH1 task 3(b): accessibility framing, prepended to PROMPT as one of the
# RECITATION-block escalation strategies (see escalate_blocked_page()).
ACCESSIBILITY_PREFIX = (
    "This is a public-domain government textbook page; transcribe it for "
    "accessibility. "
)

# Step 3b.3: standalone margin-year tokens to strip from every output.
# FIX_BATCH13 task 3(a): 2021/2022 added -- page 130 had a "২০২১" leak at
# the end of the page the existing 2023-2026 list didn't cover.
MARGIN_YEAR_TOKENS = [
    "২০২১", "২০২২", "২০২৩", "২০২৪", "২০২৫", "২০২৬",
    "2021", "2022", "2023", "2024", "2025", "2026",
]
_YEAR_ALT = "|".join(MARGIN_YEAR_TOKENS)
_MARGIN_YEAR_WHOLE_LINE_RE = re.compile(rf"^\s*(?:{_YEAR_ALT})\s*$")
_MARGIN_YEAR_TRAILING_RE = re.compile(rf" {{10,}}(?:{_YEAR_ALT})\s*$")

FALLBACK_MARKER = "[FALLBACK: TESSERACT — Gemini RECITATION block]"

# Step 3e.3: LaTeX-to-plain post-processing, applied after margin-year stripping.
# thinkingLevel=minimal (Step 3d finding) makes the model more likely to fall
# back to LaTeX on set-notation-dense pages despite the prompt's own "not
# LaTeX" instruction -- this cleans exactly the patterns Step 3e named, no more:
#   - $...$ / $$...$$ delimiters: stripped (content kept).
#   - \begin{array}{...} / \end{array} and \cline{...}: stripped (these are
#     pure tabular scaffolding with no semantic content of their own; treated
#     as part of "strip \begin{array}/\end{array}" rather than a new mapping).
#   - \frac{a}{b} -> a/b (non-nested case; a nested \frac inside another
#     \frac's argument will only have its outer layer converted correctly).
#   - ^{n} / ^2 -> superscript Unicode, only for 0-9 and n (the only
#     characters with accepted Unicode superscript forms this project uses
#     elsewhere, per Step 3e's own example) -- "where possible", anything else
#     after ^ is left as-is rather than guessed at.
#   - The named symbol commands below -> their Unicode equivalent.
# Explicitly NOT handled: bare array-internal "&" and "\\" row/column
# separators. \overline{...} IS now handled, but separately (see
# _LATEX_OVERLINE_RE below) since it needs its own occurrence count for the
# "overline" QC flag (FIX_BATCH3 task 1), not a 1:1 string substitution.
# FIX_BATCH3 task 1 found a real pre-existing bug while adding \supseteq:
# this is a plain dict of literal str.replace() calls done in insertion
# order, so \subset (a PREFIX of \subseteq) was replacing itself inside
# \subseteq before \subseteq ever got a chance to match -- "\subseteq" ->
# "⊂eq" (exactly the garbled pattern _SUBSETEQ_GARBLED_RE below exists to
# clean up, except this one was self-inflicted, not from the model). Same
# bug for \le/\leq and \ge/\geq ("\leq" -> "≤q", "\geq" -> "≥q"). Confirmed
# via paper/check/ERRORS_LOG.csv batch=3's own page-30 note ("primary had
# ⊂eq ... replaced by GT") and backend/data/ocr_gemini/.../page_30.flashlite.txt
# (an archived pre-fix backup) -- no CURRENTLY-ACTIVE page has this bug's
# output (page 30 is manually fixed and guarded), only future pages were at
# risk. Fixed by listing every multi-char command BEFORE any command that is
# one of its own prefixes.
_LATEX_SYMBOL_MAP = {
    r"\cup": "∪", r"\cap": "∩", r"\in": "∈", r"\notin": "∉",
    r"\subseteq": "⊆", r"\supseteq": "⊇", r"\subset": "⊂",
    r"\emptyset": "∅", r"\varnothing": "∅",
    r"\therefore": "∴", r"\because": "∵", r"\times": "×", r"\div": "÷",
    r"\leq": "≤", r"\le": "≤", r"\geq": "≥", r"\ge": "≥", r"\neq": "≠", r"\pm": "±",
    r"\cdot": "·",
    # FIX_BATCH3 task 1: the book's own house style writes set difference as a
    # bare backslash (observed "A\B" on page 30), not the Unicode "∖" --
    # \setminus matches that convention instead of introducing a symbol the
    # book itself doesn't use.
    r"\setminus": "\\",
    # FIX_BATCH4 task 1: function-mapping arrows (e.g. f: A -> B). No prefix
    # collision with anything else in this map or with the \left/\right
    # delimiter-stripping regex below (that one only fires when \right is
    # immediately followed by a bracket/paren/pipe/dot, never a letter).
    r"\longrightarrow": "→", r"\rightarrow": "→", r"\to": "→",
    # FIX_BATCH7 task 2: \% is just an escaped literal percent sign -- no
    # prefix collision risk with anything else in this map.
    r"\%": "%",
}
# FIX_BATCH3 task 1: Gemini sometimes renders "⊆" as the Unicode "⊂" symbol
# immediately followed by literal text "eq" (a garbled \subseteq) instead of
# either the symbol or the LaTeX command -- fix the literal garbled string.
_SUBSETEQ_GARBLED_RE = re.compile(r"⊂eq")
_SUPERSCRIPT_MAP = {"0": "⁰", "1": "¹", "2": "²", "3": "³", "4": "⁴", "5": "⁵",
                     "6": "⁶", "7": "⁷", "8": "⁸", "9": "⁹", "n": "ⁿ"}
# FIX_BATCH4 task 1: \left/\right are LaTeX's auto-sizing delimiter commands
# -- always immediately followed by the actual delimiter character they
# size (a paren/bracket/pipe/period, or an ESCAPED brace \{ \} ). Captures
# the delimiter and keeps only that, dropping the \left/\right prefix --
# covers \left( \right), \left[ \right], \left\{ \right\} (the kept \{ / \}
# gets un-escaped to a bare brace by the existing _LATEX_ESCAPED_BRACE_RE
# pass later) and \left. \right. alike. MUST consume the whole \left\{ /
# \right\} as one match (not a zero-width lookahead) -- "\le" is a literal
# prefix of "\left", so any leftover bare "\left" text would otherwise be
# mangled by the symbol map's \le -> ≤ replacement later ("\left" -> "≤ft").
# Deliberately requires a recognized delimiter right after -- a bare
# "\right" with nothing recognizable following it is left alone (and
# flagged by find_latex_leftover) rather than guessed at.
_LATEX_LEFT_RIGHT_RE = re.compile(r"\\(?:left|right)(\\[{}]|[(){}\[\]|.])")

# \mathbb{X} -> the blackboard-bold Unicode letter, but ONLY for the 4
# letters these books actually use (N/R/Z/Q) -- an unlisted letter is left
# as literal \mathbb{X} (flagged as latex_left) rather than guessed at.
_MATHBB_MAP = {"N": "ℕ", "R": "ℝ", "Z": "ℤ", "Q": "ℚ"}
_LATEX_MATHBB_RE = re.compile(r"\\mathbb\{([A-Za-z])\}")

# FIX_BATCH4 task 1: \begin{tabular}/\begin{array} ... \end{...} -> one line
# per table row, cells separated by " | " (e.g. "x | 0 | 1 | 2"), \hline
# dropped. LaTeX row separator is "\\", cell separator is "&". Runs BEFORE
# the older bare _LATEX_ARRAY_ENV_RE strip below, which stays only as a
# fallback for a malformed table missing its \end (no real content
# structure to preserve there anyway).
_LATEX_TABLE_ENV_RE = re.compile(
    r"\\begin\{(?:tabular|array)\}(?:\{[^{}]*\})?(.*?)\\end\{(?:tabular|array)\}", re.DOTALL
)
_LATEX_HLINE_RE = re.compile(r"\\hline")


def _convert_latex_table(m):
    body = _LATEX_HLINE_RE.sub("", m.group(1))
    rows = [row.strip() for row in body.split("\\\\")]
    lines = [" | ".join(cell.strip() for cell in row.split("&")) for row in rows if row]
    return "\n".join(lines)


# FIX_BATCH9 task 1: \begin{cases} A \\ B \end{cases} (a piecewise
# definition, e.g. page 82 batch 9: a^{m-n} when m>=n, else 1/a^{n-m}) ->
# "{ A ; B }" -- same "\\" row-separator convention as the tabular/array
# conversion above, just joined with " ; " instead of split into lines
# (a piecewise definition reads naturally on one line, unlike a real
# table). Each row's own LaTeX (superscripts, \frac, \text{}, etc.) is left
# untouched here -- it gets resolved by the normal passes later, same as
# any other text.
_LATEX_CASES_ENV_RE = re.compile(r"\\begin\{cases\}(.*?)\\end\{cases\}", re.DOTALL)


def _convert_latex_cases(m):
    rows = [row.strip() for row in m.group(1).split("\\\\")]
    return "{ " + " ; ".join(row for row in rows if row) + " }"


# FIX_BATCH9 task 1: a plain HTML <table> (page 87 batch 9 -- Gemini fell
# back to HTML instead of LaTeX for a table with merged cells) -> one line
# per <tr>, cells (<td> or <th>, any attributes like rowspan="6" ignored)
# joined with " | ", same convention as the LaTeX table conversion above.
_HTML_TABLE_RE = re.compile(r"<table>(.*?)</table>", re.DOTALL)
_HTML_TR_RE = re.compile(r"<tr>(.*?)</tr>", re.DOTALL)
_HTML_CELL_RE = re.compile(r"<t[dh][^>]*>(.*?)</t[dh]>", re.DOTALL)


def _convert_html_table(m):
    rows = []
    for tr_m in _HTML_TR_RE.finditer(m.group(1)):
        cells = [c.strip() for c in _HTML_CELL_RE.findall(tr_m.group(1))]
        rows.append(" | ".join(cells))
    return "\n".join(rows)


_LATEX_ARRAY_ENV_RE = re.compile(r"\\(?:begin|end)\{array\}(?:\{[^{}]*\})?")
_LATEX_CLINE_RE = re.compile(r"\\cline\{[^{}]*\}")
_LATEX_DOLLAR_RE = re.compile(r"\$\$?")
# FIX_BATCH9 task 1: \dfrac (display-style) and \tfrac (text-style) are
# just \frac with different LaTeX rendering hints -- no plain-text
# distinction, so they're folded into the exact same conversion.
_LATEX_FRAC_RE = re.compile(r"\\(?:frac|dfrac|tfrac)\{([^{}]*)\}\{([^{}]*)\}")
_LATEX_ESCAPED_BRACE_RE = re.compile(r"\\([{}])")

# FIX_BATCH1 task 1: still-leftover LaTeX patterns found on page_8.txt (batch 1
# review, paper/check/ERRORS_LOG.csv). \dot{X} is the recurring-decimal marker
# (dot ABOVE a digit, e.g. 5.1\dot{6}5\dot{4} = 5.16̇54̇) -- must not be lost, so
# it maps to the digit plus a combining dot above (U+0307), not stripped.
_LATEX_DOTS_RE = re.compile(r"\\(?:dots|ldots|cdots)")
_LATEX_QQUAD_RE = re.compile(r"\\(?:qquad|quad)")
_LATEX_DOT_ACCENT_RE = re.compile(r"\\dot\{([^{}]*)\}")
_LATEX_SQRT_RE = re.compile(r"\\sqrt\{([^{}]*)\}")

# FIX_BATCH9 task 1: \sqrt[n]{X} (an nth root with an explicit index, e.g.
# page 84/86/90 batch 9: \sqrt[3]{54}, \sqrt[pq]{...}) -> "ⁿ√X" -- n=3/4 get
# the dedicated Unicode root glyphs (∛/∜) per the task; any other index
# (including a multi-character one like "pq", which has no clean Unicode
# superscript since sup.py's SUP dict has no "q") falls back to the same
# "^(n)" convention used everywhere else an exponent can't be
# superscripted, so "^(pq)√X" rather than guessing at a glyph. X gets
# parens only when it's more than one character, same rule as the existing
# plain (non-indexed) \sqrt conversion just above.
_SQRT_INDEX_MAP = {"3": "∛", "4": "∜"}
_LATEX_SQRT_INDEXED_RE = re.compile(r"\\sqrt\[([^\[\]]*)\]\{([^{}]*)\}")


def _convert_indexed_sqrt(m):
    index, content = m.group(1), m.group(2)
    prefix = _SQRT_INDEX_MAP.get(index)
    if prefix is None:
        sup_index = sup.conv(index)
        prefix = f"{sup_index}√" if sup_index else f"^({index})√"
    return f"{prefix}{content}" if len(content) == 1 else f"{prefix}({content})"
_COMBINING_DOT_ABOVE = "\u0307"
_LATEX_LEFTOVER_RE = re.compile(r"\\[A-Za-z]+")

# FIX_BATCH3 task 1: \text{...} -> just the text inside (it's never anything
# but plain words Gemini wrapped in \text for no real reason).
_LATEX_TEXT_RE = re.compile(r"\\text\{([^{}]*)\}")
# \overline{X} is a second, different recurring-decimal notation (overline
# instead of per-digit dots, e.g. 7.0\overline{18}). Peal's call: do NOT try
# to render a combining macron over X (unreliable rendering, and ambiguous
# which characters it should cover) -- just keep X bare and count the
# occurrence so the page gets an "overline" QC flag for a human to check.
_LATEX_OVERLINE_RE = re.compile(r"\\overline\{([^{}]*)\}")

# FIX_BATCH7 task 2: \underline{X} -> X (a long-division subtraction line,
# e.g. page 64's \underline{6x^2 - 6x} -- the underline styling itself has
# no plain-text equivalent worth keeping, just the content). Runs in the
# same early group as \text/\overline above, before superscripts resolve,
# so content like "6x^2 - 6x" still gets its "^2" converted to "²" by the
# LATER superscript pass once it's exposed in the outer text.
_LATEX_UNDERLINE_RE = re.compile(r"\\underline\{([^{}]*)\}")

# FIX_BATCH7 task 2: \phantom{...} is pure LaTeX alignment padding with NO
# plain-text equivalent -- delete the whole command, argument included.
# Needs a manual balanced-brace scan (not a plain regex): page 64's alt
# reading has a genuinely nested case, \phantom{6x^2 - 7x +{{}} }, where a
# naive non-nesting [^{}]* group would stop at the FIRST inner "{" and leave
# a corrupted remainder.
_LATEX_PHANTOM_START_RE = re.compile(r"\\phantom\{")


def _strip_phantom(text):
    """Returns (text, phantom_count) with every \\phantom{...} command
    removed, including arbitrarily nested braces inside its argument."""
    out = []
    count = 0
    i = 0
    while True:
        m = _LATEX_PHANTOM_START_RE.search(text, i)
        if not m:
            out.append(text[i:])
            break
        out.append(text[i:m.start()])
        depth = 1
        j = m.end()
        while j < len(text) and depth > 0:
            if text[j] == "{":
                depth += 1
            elif text[j] == "}":
                depth -= 1
            j += 1
        i = j
        count += 1
    return "".join(out), count


# FIX_BATCH7 task 2: \; \, \! are LaTeX inter-math spacing commands (thin
# space / comma-space / negative thin space) with no plain-text equivalent
# worth keeping -- delete outright.
_LATEX_SPACING_CMD_RE = re.compile(r"\\[;,!]")

# FIX_BATCH7 task 2: a single-digit subscript (X_0 .. X_9, e.g. page 70's
# "Q_0") -> the Unicode subscript digit (Q₀). Scoped to a BARE single digit
# right after "_" (no braces), matching the task's own "একক অঙ্কের
# subscript" (single-digit subscript) wording -- a braced/multi-digit
# subscript is left alone rather than guessed at (none observed yet).
_SUBSCRIPT_MAP = {"0": "₀", "1": "₁", "2": "₂", "3": "₃", "4": "₄", "5": "₅",
                   "6": "₆", "7": "₇", "8": "₈", "9": "₉"}
_LATEX_SUB_BARE_RE = re.compile(r"_([0-9])")


def find_latex_leftover(text):
    """FIX_BATCH1 task 1 (last bullet): any `\\word` LaTeX command that
    survives latex_to_plain() -- i.e. not one of the patterns handled above.
    Returns a sorted list of distinct leftover commands (empty if none)."""
    return sorted(set(_LATEX_LEFTOVER_RE.findall(text)))


# QC: "stacked_fraction" -- a line that is JUST a 1-3 char digit/variable
# token, or a lone em-dash, is the signature of a numerator/fraction-bar/
# denominator printed on separate lines instead of plain "a/b" on one line
# (found on page 10, see paper/check/ERRORS_LOG.csv "fraction_layout": lines
# like "p²" / "—" / "q" instead of "p²/q"). Restricted to digits (ASCII +
# Bangla) and Latin letters/superscripts/math glyphs so ordinary short Bangla
# words (e.g. "কি") are not mistaken for a stacked fraction component.
_STACKED_FRACTION_RE = re.compile(r"^\s*(?:[0-9০-৯a-zA-Z±√⁰¹²³⁴⁵⁶⁷⁸⁹ⁿ]{1,3}|—)\s*$")


def find_stacked_fraction_lines(text):
    """Returns the 1-based line numbers matching _STACKED_FRACTION_RE (empty
    if none). Used to flag a whole page for QC, not to fix anything --
    recovering the real a/b layout needs re-OCR under a stronger prompt, not
    a local regex (the same text could legitimately be a single short answer
    line, e.g. a lone 'x' heading a worked example)."""
    return [i for i, line in enumerate(text.split("\n"), start=1) if _STACKED_FRACTION_RE.match(line)]


# FIX_BATCH5 task 2 (bullet 3): QC-only flag -- a " / " split where the part
# BEFORE the slash contains a top-level "+"/"-"/"−" (one not enclosed by a
# single pair of parens reaching the slash) is ambiguous: does the "/" apply
# to the whole left expression or just its last term? Real example (page 49
# batch 5, before its manual fix): "(a + b)² + (a − b)² / 2" -- should have
# been "((a + b)² + (a − b)²) / 2". Never auto-fixed (Peal: "বদলাবে না, Claude
# দেখবে") since guessing where the missing paren should open is not safe.
# Scoped to the segment after the LAST "=" before the slash (if any), else
# the whole line, so an unrelated earlier "+" in the same line (e.g. a side
# equation before the "=") doesn't cause a false read of WHERE the ambiguity
# is -- though either way the correct line still gets flagged.
_FRACTION_PARENS_SLASH_RE = re.compile(r" / ")


def find_fraction_parens_lines(text):
    """Returns the 1-based line numbers with an ambiguous ' / ' split (empty
    if none) -- flag only, see module note above."""
    results = []
    for i, line in enumerate(text.split("\n"), start=1):
        for m in _FRACTION_PARENS_SLASH_RE.finditer(line):
            slash_pos = m.start()
            eq_pos = line.rfind("=", 0, slash_pos)
            segment = line[eq_pos + 1:slash_pos] if eq_pos != -1 else line[:slash_pos]
            depth = 0
            ambiguous = False
            for ch in segment:
                if ch == "(":
                    depth += 1
                elif ch == ")":
                    depth = max(0, depth - 1)
                elif ch in "+-−" and depth == 0:
                    ambiguous = True
                    break
            if ambiguous:
                results.append(i)
                break
    return results


# FIX_BATCH7 task 3: QC-only flag -- a plain "digit/digit" fraction
# immediately followed by a letter or "(" (e.g. "1/27(27a³+1)", "1/2x²") is a
# fraction COEFFICIENT with no grouping parens around the fraction itself,
# ambiguous the same way `\frac{X}{Y}` conversion already guards against
# (see _frac_part_needs_parens) -- except this pattern is written plain by
# Gemini directly (never went through \frac), so that guard never sees it.
# Real examples, page 63/67 batch 7: "a^3 + 1/27(27a^3+1)" should have been
# "a³ + (1/27)(27a³+1)"; "f(− 1/2 a)" reads as "−1/(2a)" instead of the
# intended "f(−(1/2)a)". Never auto-fixed ("বদলাবে না" per the task) --
# Task 1's prompt addition is the actual fix, meant to stop Gemini writing
# this in the first place; this flag just catches whatever still slips
# through for a human to check.
_FRACTION_COEFFICIENT_RE = re.compile(r"[0-9]+/[0-9]+[a-zA-Z(]")


def find_fraction_coefficient_lines(text):
    """Returns the 1-based line numbers matching _FRACTION_COEFFICIENT_RE
    (empty if none) -- flag only, see module note above."""
    return [i for i, line in enumerate(text.split("\n"), start=1) if _FRACTION_COEFFICIENT_RE.search(line)]


# FIX_BATCH9 task 3: QC-only flag -- a closing paren, then whitespace, then
# a lowercase letter immediately followed by a superscript sign (e.g. page
# 83 batch 9: "(aᵖ) q⁻r") is an exponent that's come detached from its
# base: "q⁻r" should have been the WHOLE exponent on "(aᵖ)" (i.e.
# "(aᵖ)^(q−r)"), but only the sign superscripted, leaving "q" and "r" at
# normal size and visually disconnected from "(aᵖ)". Not auto-fixed --
# there's no reliable Unicode superscript for every possible exponent
# letter (e.g. no superscript "q" exists at all, which is exactly why
# sup.py's own SUP dict omits it), so guessing at the intended grouping
# isn't safe; flag only, for a human to check against the page image.
_EXPONENT_DETACHED_RE = re.compile(r"\)\s+[a-z][⁻⁺]")


def find_exponent_detached_lines(text):
    """Returns the 1-based line numbers matching _EXPONENT_DETACHED_RE
    (empty if none) -- flag only, see module note above."""
    return [i for i, line in enumerate(text.split("\n"), start=1) if _EXPONENT_DETACHED_RE.search(line)]


# FIX_BATCH5 task 2 (bullet 1): per-book offset so a page's own printed page
# number (always in its running header, within the first 2 lines) can be
# checked against the PDF page number -- confirmed from ERRORS_LOG batch 5:
# PDF page 45 prints "৪০", PDF page 49 prints "৪৪" (both "PDF page - 5"). An
# unlisted book is silently skipped (not guessed at) until its own offset is
# confirmed the same way.
PAGE_NUMBER_OFFSET = {
    "class_9_General_math_bn": 5,
}

_BANGLA_DIGITS = "০১২৩৪৫৬৭৮৯"
_BANGLA_TO_LATIN_DIGITS = str.maketrans(_BANGLA_DIGITS, "0123456789")
_LATIN_DIGIT_RUN_RE = re.compile(r"[0-9]+")
_BANGLA_DIGIT_RUN_RE = re.compile(r"[০-৯]+")
# A chapter-opening title page's header is just "অধ্যায় N" (its CHAPTER
# number, not a page number -- e.g. page 48: "অধ্যায় ৩" then a blank line,
# no page number anywhere on the page). Strips that specific number out
# before hunting for a page-number candidate, so it's never mistaken for one.
# The word is built from explicit code points, not typed literally: Gemini's
# output consistently uses the PRECOMPOSED "য়" (U+09DF), and a literal in
# this source file risked silently normalizing to the DECOMPOSED "য"+nukta
# (U+09AF U+09BC) instead -- same glyph, different codepoints, so a plain
# string literal here would never match any real page (confirmed empirically
# against every batch-5 raw.txt before relying on this).
_CHAPTER_WORD = "অধ্যায়"  # অধ্যায় (precomposed form, matches throughout)
_CHAPTER_NUMBER_RE = re.compile(rf"({_CHAPTER_WORD}\s*)[০-৯]+")

# FIX_BATCH7 fix (found while running batch 7, not a synthetic case): when
# the running header is ENTIRELY on line 1 (e.g. page 67's "৬২<TAB>গণিত"),
# line 2 is already real body content -- an ordinary equation line like
# "∴ g(y) = y² + y² − 2y² = 0" legitimately contains Latin digits ("2",
# "0") as math coefficients, which a plain "scan the first 2 lines for any
# digit" check mistook for a misread page number. A line only counts as
# part of the header if, once its own chapter-number prefix (if any) is
# stripped, what's left is NOTHING but digits/whitespace and the literal
# word "গণিত" -- real sentence/equation content always fails this and is
# skipped entirely (contributing NO candidate digits, Latin or Bangla).
_HEADER_LIKE_LINE_RE = re.compile(r"^[\s0-9০-৯]*(গণিত[\s0-9০-৯]*)?$")


def _bangla_digits_to_int(run):
    return int(run.translate(_BANGLA_TO_LATIN_DIGITS))


def detect_page_number_mismatch(text, book, pdf_page):
    """FIX_BATCH5 task 2 (bullet 1, extended by a FIX_BATCH7 fix): checks
    the page's own printed page number, which this book always prints in
    its running header (within the first 2 lines -- see page_41.raw.txt's
    "৩৬<TAB>গণিত" / page_46.raw.txt's "...ফাংশন<TAB>৪১" / page_49.raw.txt's
    standalone "৪৪"). Only lines that look like header/boilerplate
    (_HEADER_LIKE_LINE_RE, after stripping a chapter-number prefix)
    contribute candidate digit runs -- a real content line is never scanned
    (page 67 batch 7: line 2 was an equation with ordinary Latin-digit
    coefficients, "2"/"0", which a blind first-2-lines scan mistook for a
    misread page number before this fix). Flags (does not fix):
      (a) ANY Latin-digit run on a header-like line -- this book's headers
          are always Bangla-script, so Latin digits there are a misread
          (page 49: header OCR'd as "88" instead of "৪৪").
      (b) Bangla-digit run(s) ARE present but NONE equal the expected
          printed number (pdf_page - PAGE_NUMBER_OFFSET[book]) -- page 45:
          header OCR'd as "৮০" instead of the expected "৪০" (৪/৮ misread);
          page 69 batch 7: "৫৪" instead of the expected "৬৪" (৬/৫ misread).
    A chapter-opening title page prints no running header at all beyond its
    own chapter number (see page 48: first 2 lines are just "অধ্যায় ৩" with
    a blank line, no page number anywhere) -- that line still counts as
    header-like (it's JUST the chapter number) but contributes no digit run
    of its own once the chapter number is stripped, so there's nothing to
    check -- silently skipped rather than flagged as a mismatch. A book with
    no confirmed PAGE_NUMBER_OFFSET entry is skipped the same way.
    Returns a note string, or None if clean / not checkable."""
    offset = PAGE_NUMBER_OFFSET.get(book)
    if offset is None:
        return None
    expected = pdf_page - offset
    latin_runs, bangla_runs = [], []
    for line in text.split("\n")[:2]:
        stripped = _CHAPTER_NUMBER_RE.sub(r"\1", line)
        if not _HEADER_LIKE_LINE_RE.match(stripped):
            continue  # real body content, not header/boilerplate -- skip entirely
        latin_runs += _LATIN_DIGIT_RUN_RE.findall(stripped)
        bangla_runs += _BANGLA_DIGIT_RUN_RE.findall(stripped)
    if latin_runs:
        return f"page_number_mismatch: Latin digits {latin_runs} in header (expected page {expected} in Bangla digits)"
    if not bangla_runs:
        return None
    if expected not in [_bangla_digits_to_int(r) for r in bangla_runs]:
        return f"page_number_mismatch: header number(s) {bangla_runs} don't match expected page {expected}"
    return None


# FIX_BATCH11 task 1: this book normally writes inline equation digits in
# LATIN script (e.g. "3x = 9 বা x = 3", "aᵐ × aⁿ") even though running
# prose/headers use Bangla digits -- but Flash-Lite sometimes converts EVERY
# digit on the page to Bangla despite the prompt's script rules (ERRORS_LOG
# batch=11, page 101: "all Latin digits -> Bangla + stacked ... despite
# prompt rule"; page_101.raw.txt confirms it: "৫x", "x = ১", "y − ২" etc.
# throughout, using the proper minus sign). Scoped to lines that actually
# look like math content (x, y, =, +, or the proper minus sign − U+2212,
# per the task's own literal list) -- deliberately EXCLUDES the plain ASCII
# hyphen "-", unlike an early version of this regex: a real false positive
# was found testing against page 118, a plain-prose page (Euclid's
# postulates) whose ONLY "math-like" line by that broader regex was its
# page footer "ফর্মা-১৫, গণিত-৯ম-১০ম শ্রেণি" -- an ordinary hyphenated
# ordinal range/signature, not an equation, but it alone supplied all 5
# Bangla digits the flag complained about. The real minus sign U+2212
# (confirmed throughout page_101.raw.txt) is a much cleaner signal and
# never appears in ordinary Bangla punctuation.
_MATH_LINE_RE = re.compile(r"[xy=+−]")


def count_script_digits_on_math_lines(text):
    """Returns (bangla_digit_count, latin_digit_count) summed over every
    line in `text` that looks like math content (_MATH_LINE_RE)."""
    bangla = latin = 0
    for line in text.split("\n"):
        if not _MATH_LINE_RE.search(line):
            continue
        bangla += sum(1 for ch in line if ch in _BANGLA_DIGITS)
        latin += sum(1 for ch in line if ch in "0123456789")
    return bangla, latin


def detect_script_digit_mismatch(text):
    """FIX_BATCH11 task 1: flags when math-like lines have MORE Bangla
    digits than Latin digits -- see module note above. Returns a note
    string, or None if clean (including pages with no math-like lines at
    all, or ties)."""
    bangla, latin = count_script_digits_on_math_lines(text)
    if bangla > latin:
        return f"script_digit_mismatch: {bangla} Bangla digit(s) vs {latin} Latin digit(s) on math-like lines"
    return None


# FIX_BATCH10 task 1: the tutor's reference-mode dropdown filters Qdrant
# chunks by chapter+exercise (see CLAUDE.md's retriever.py note), so an
# exercise label with the wrong chapter digit silently breaks that lookup.
# Real, confirmed instances (ERRORS_LOG batch=10): page 91 "অনুশীলনী ৮.২"
# (should be "৪.২"), page 96 "অনুশীলনী ৮.৩" (should be "৪.৩") -- Gemini
# repeatedly misread this book's chapter-4 digit "৪" as "৮" specifically
# inside exercise headers, even on pages whose own running header correctly
# says "অধ্যায় ৪. সূচক ও লগারিদম" right next to it.
_EXERCISE_CHAPTER_RE = re.compile(rf"অনুশীলনী\s*([0-9০-৯]+)\.[0-9০-৯]+")
_CHAPTER_HEADER_NUM_RE = re.compile(rf"{_CHAPTER_WORD}\s*([0-9০-৯]+)")
# "উদাহরণ" (worked example) numbers were checked across this whole book's
# OCR output (grep for "উদাহরণ" followed by a chapter-dot pair) and NEVER
# carry a chapter-number component -- always a plain running count ("উদাহরণ
# ১২."), never "chapter.example" -- so, unlike অনুশীলনী, উদাহরণ contributes
# no chapter-number signal of its own here. Verified empirically, not assumed.

_CHAPTER_RANGES_CACHE = {}


def load_chapter_ranges(book):
    """Returns {chapter_number: (start_printed_page, end_printed_page_or_None)}
    for `book`, built from curriculum.json's start_page_bn (bn books) /
    start_page_en (en books) by chapter-NUMBER adjacency (chapter N's range
    ends the printed page right before chapter N+1's listed start; the last
    chapter's range has no upper bound). Result is cached per book stem.

    KNOWN curriculum.json DATA BUG (found while building this, left
    unedited -- curriculum.json is backend/ data the live app's dropdown
    already reads, out of scope for this pipeline to touch): for
    class_9_General_math_bn, chapter 4 (সূচক ও লগারিদম) is listed with
    start_page_bn=95 but chapter 5 (এক চলকবিশিষ্ট সমীকরণ) is listed with
    start_page_bn=93 -- EARLIER than chapter 4, impossible in reading order.
    Cross-checked against the real OCR'd pages: chapter 4 actually opens at
    PDF page 80 / printed ৭৫ (page_80.txt: "অধ্যায় ৪\nসূচক ও লগারিদম"), so
    95 is simply wrong (should read ~75). A chapter whose computed range
    comes out inverted (end < start) is OMITTED from the returned dict
    rather than guessed at -- here that silently drops chapter 4 from the
    lookup and widens chapter 3's range to swallow chapter 4's real pages
    (43-94), but chapter 5 onward (start_page_bn 93, 111, 136, ... all
    correctly increasing) are unaffected, which covers every page this
    pipeline still has left to process (chapters 3-4's pages are already
    done and manually fixed, see MANUAL_PAGES.txt, so never reprocessed)."""
    if book in _CHAPTER_RANGES_CACHE:
        return _CHAPTER_RANGES_CACHE[book]
    is_bn = book.endswith("_bn")
    page_key = "start_page_bn" if is_bn else "start_page_en"
    fname_key = "bangla_file" if is_bn else "english_file"
    curriculum = json.load(open(CURRICULUM_PATH, encoding="utf-8"))
    chapters = None
    for b in curriculum["books"]:
        if os.path.splitext(b[fname_key])[0] == book:
            chapters = sorted(b["chapters"], key=lambda c: c["number"])
            break
    ranges = {}
    if chapters:
        for i, ch in enumerate(chapters):
            start = ch[page_key]
            end = chapters[i + 1][page_key] - 1 if i + 1 < len(chapters) else None
            if end is not None and end < start:
                continue  # inverted range -- curriculum.json data bug, skip (see docstring)
            ranges[ch["number"]] = (start, end)
    _CHAPTER_RANGES_CACHE[book] = ranges
    return ranges


def expected_chapter_for_page(book, pdf_page):
    """The chapter curriculum.json's page ranges say SHOULD contain this PDF
    page (printed_page = pdf_page - PAGE_NUMBER_OFFSET[book], same offset as
    detect_page_number_mismatch). None if the book has no confirmed offset,
    or the printed page falls in a gap left by an omitted inverted range."""
    offset = PAGE_NUMBER_OFFSET.get(book)
    if offset is None:
        return None
    printed_page = pdf_page - offset
    for num, (start, end) in load_chapter_ranges(book).items():
        if printed_page >= start and (end is None or printed_page <= end):
            return num
    return None


def find_exercise_chapter_mismatches(text, book, pdf_page):
    """FIX_BATCH10 task 1: flags an `অনুশীলনী X.Y` exercise label whose
    chapter digit X disagrees with the page's own `অধ্যায় N` running header
    (preferred, when present on the page) or, failing that, with
    curriculum.json's expected chapter for this PDF page. Also flags the
    page header itself if it disagrees with curriculum.json. Returns a list
    of note strings (empty if clean or not checkable -- book has no
    confirmed PAGE_NUMBER_OFFSET and the page has no "অধ্যায়" header either)."""
    header_nums = [_bangla_digits_to_int(m) for m in _CHAPTER_HEADER_NUM_RE.findall(text)]
    expected = expected_chapter_for_page(book, pdf_page)
    notes = []
    if header_nums and expected is not None and header_nums[0] != expected:
        notes.append(
            f"exercise_chapter_mismatch: page header says অধ্যায় {header_nums[0]} "
            f"but curriculum.json expected chapter {expected} for this page"
        )
    reference = header_nums[0] if header_nums else expected
    if reference is not None:
        for m in _EXERCISE_CHAPTER_RE.finditer(text):
            x = _bangla_digits_to_int(m.group(1))
            if x != reference:
                source = "page header" if header_nums else "curriculum.json expected chapter"
                notes.append(f"exercise_chapter_mismatch: '{m.group(0)}' implies chapter {x} but {source} says {reference}")
    return notes


def build_qc_note(text, counts=None, extra=None, book=None, pdf_page=None):
    """Combines counts (a dict from post_process(): typo_fixes, token_leak,
    overline, devanagari_leak -- FIX_BATCH2/3; margin_digit -- FIX_BATCH5),
    latex_left (FIX_BATCH1), stacked_fraction (FIX_BATCH1), fraction_parens
    (FIX_BATCH5), fraction_coefficient (FIX_BATCH7), a page-number-header
    check (FIX_BATCH5, only when both `book` and `pdf_page` are given), and
    any `extra` note(s) (str or list of
    str; e.g. FIX_BATCH2 task 3's missing_recurring_dot, FIX_BATCH3 task 2's
    quality-pick note) into a single note for a RUN_LOG row's "error" field.
    FIX_BATCH13 task 3(c) added figure_labels_suspect (a flag-only line
    range, computed here directly from `text` rather than passed in via
    `counts`, since it's never auto-fixed). Empty string if nothing applies."""
    counts = counts or {}
    parts = []
    if counts.get("typo_fixes"):
        parts.append(f"typo_fixes: {counts['typo_fixes']}")
    if counts.get("token_leak"):
        parts.append(f"token_leak: {counts['token_leak']}")
    if counts.get("overline"):
        parts.append(f"overline: {counts['overline']}")
    if counts.get("devanagari_leak"):
        parts.append(f"devanagari_leak: {counts['devanagari_leak']}")
    if counts.get("script_leak"):
        parts.append(f"script_leak: {counts['script_leak']}")
    if counts.get("margin_digit"):
        parts.append(f"margin_digit: {counts['margin_digit']}")
    if counts.get("greek_subscript"):
        parts.append(f"greek_subscript: {counts['greek_subscript']}")
    if counts.get("log_fixes"):
        parts.append(f"log_fixes: {counts['log_fixes']}")
    if counts.get("sqrt_parens"):
        parts.append(f"sqrt_parens: {counts['sqrt_parens']}")
    if counts.get("parallel_fixes"):
        parts.append(f"parallel_fixes: {counts['parallel_fixes']}")
    if counts.get("figure_labels_removed"):
        parts.append(f"figure_labels_removed: {counts['figure_labels_removed']}")
    if counts.get("figure_values_lost"):
        parts.append(f"figure_values_lost: {counts['figure_values_lost']}")
    if counts.get("margin_year_tail"):
        parts.append(f"margin_year_tail: {counts['margin_year_tail']}")
    suspect = find_figure_labels_suspect_lines(text)
    if suspect:
        parts.append(f"figure_labels_suspect: L{',L'.join(str(n) for n in suspect)}")
    leftover = find_latex_leftover(text)
    if leftover:
        parts.append(f"latex_left: {','.join(leftover)}")
    stacked = find_stacked_fraction_lines(text)
    if stacked:
        parts.append(f"stacked_fraction: L{',L'.join(str(n) for n in stacked)}")
    frac_parens = find_fraction_parens_lines(text)
    if frac_parens:
        parts.append(f"fraction_parens: L{',L'.join(str(n) for n in frac_parens)}")
    frac_coef = find_fraction_coefficient_lines(text)
    if frac_coef:
        parts.append(f"fraction_coefficient: L{',L'.join(str(n) for n in frac_coef)}")
    exp_detached = find_exponent_detached_lines(text)
    if exp_detached:
        parts.append(f"exponent_detached: L{',L'.join(str(n) for n in exp_detached)}")
    sd_note = detect_script_digit_mismatch(text)
    if sd_note:
        parts.append(sd_note)
    if book is not None and pdf_page is not None:
        pn_note = detect_page_number_mismatch(text, book, pdf_page)
        if pn_note:
            parts.append(pn_note)
        parts.extend(find_exercise_chapter_mismatches(text, book, pdf_page))
    if extra:
        parts.extend(extra if isinstance(extra, list) else [extra])
    return "; ".join(parts)


def append_qc_note(log_row, text, counts=None, extra=None, book=None, pdf_page=None):
    """Appends build_qc_note(...) to log_row['error'] in place, preserving
    any existing error content (e.g. a retry failure message)."""
    note = build_qc_note(text, counts, extra, book=book, pdf_page=pdf_page)
    if note:
        log_row["error"] = f"{log_row['error']}; {note}" if log_row["error"] else note


def _quality_issue_count(text, counts):
    """FIX_BATCH3 task 2 (extended by FIX_BATCH6 task 2): how 'dirty' one bn
    reading is, for picking between primary and secondary when BOTH
    succeeded -- latex_left command count + token_leak + devanagari_leak +
    script_leak (NOT overline or typo_fixes: those are already
    fixed/flagged-for-review, not live defects in the text itself, so they
    shouldn't bias which reading gets kept)."""
    return (
        len(find_latex_leftover(text))
        + counts.get("token_leak", 0)
        + counts.get("devanagari_leak", 0)
        + counts.get("script_leak", 0)
    )


# FIX_BATCH2b task 3 (extended by FIX_BATCH3 task 1, then FIX_BATCH6 task 1):
# \frac{a}{b} -> a/b silently changed arithmetic meaning whenever a or b
# wasn't a single, unambiguous token. Two distinct reasons a part needs
# wrapping:
#   1. It contains a top-level "+", either kind of minus ("-"/"−"),
#      whitespace (a space between terms, e.g. "2 q"), or "/" (what makes
#      nested fracs work: converting the innermost frac first turns the
#      outer part's content into e.g. "2/3", which now also needs wrapping
#      so the OUTER frac's own conversion doesn't produce an ambiguous
#      "2/3/3/7"). Original FIX_BATCH2b/3 reasoning -- \frac{28 - 2}{90}
#      must become "(28 - 2)/90", not the ambiguous "28 - 2/90".
#   2. FIX_BATCH6 task 1: it's an implicit-multiplication run with NO
#      operator at all -- a digit+letter or multi-letter concatenation like
#      "3bc" or "2x" (meaning 3*b*c / 2*x). Real bug found on page 59 batch
#      6: \frac{(b+c)^2}{3bc} converted to the wrong "((b+c)²)/3bc" --
#      numerator redundantly double-wrapped (it was ALREADY a single
#      self-contained "(...)²" unit) while the truly ambiguous denominator
#      "3bc" was left bare. Correct output: "(b+c)²/(3bc)".
# _frac_part_needs_parens() replaces the old plain character-class search
# with an actual "is this a single token" test: a pure digit run (a
# number), a single letter with an optional trailing superscript (a lone
# variable, possibly squared/cubed), or a part ALREADY fully wrapped by one
# paren pair reaching to the end (optionally followed only by superscript
# chars) is left alone; anything else gets wrapped.
_FRAC_SINGLE_DIGIT_RUN_RE = re.compile(r"^[0-9০-৯]+$")
# FIX_BATCH9 task 1: broadened from digit/n-only to EVERY superscript
# character sup.fix() can produce (derived from sup.SUP.values(), not
# hand-typed -- stays in sync with sup.py automatically) -- a base letter
# followed by a richer exponent like "aᵖ⁻ᵠ" (p minus q) is still just ONE
# exponentiation unit, same reasoning as the original digit-only "aⁿ" case,
# so it shouldn't force a wrap either.
_ALL_SUP_CHARS = "".join(sorted(set(sup.SUP.values())))
_FRAC_SINGLE_LETTER_RE = re.compile(rf"^[a-zA-Z][{_ALL_SUP_CHARS}]*$")
_FRAC_MAX_PASSES = 10  # generous bound on nesting depth; real pages never go this deep


def _frac_part_fully_enclosed(part):
    """True if `part` starts with '(' whose matching ')' is the LAST
    non-superscript character -- i.e. the whole part is already one
    self-contained parenthesized unit (e.g. "(b+c)²"), so wrapping it again
    would just be a redundant double-paren. Trailing-superscript check
    broadened the same way as _FRAC_SINGLE_LETTER_RE above."""
    if not part.startswith("("):
        return False
    depth = 0
    for i, ch in enumerate(part):
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                rest = part[i + 1:]
                return all(c in _ALL_SUP_CHARS for c in rest)
    return False  # unbalanced -- treat as not safely enclosed


def _frac_part_needs_parens(part):
    if _FRAC_SINGLE_DIGIT_RUN_RE.match(part):
        return False
    if _FRAC_SINGLE_LETTER_RE.match(part):
        return False
    if _frac_part_fully_enclosed(part):
        return False
    return True


def _wrap_frac_part(part):
    return f"({part})" if _frac_part_needs_parens(part) else part


def _convert_frac_once(text):
    return _LATEX_FRAC_RE.sub(
        lambda m: f"{_wrap_frac_part(m.group(1))}/{_wrap_frac_part(m.group(2))}", text
    )


def latex_to_plain(text):
    """Returns (plain_text, overline_count)."""
    # FIX_BATCH4 task 1: \cline must be gone from the text BEFORE the table
    # conversion splits rows/cells (otherwise a leftover "\cline{..}" token
    # would end up embedded inside a cell). The smart table conversion runs
    # first; _LATEX_ARRAY_ENV_RE right after is only a fallback for a
    # malformed table missing its \end.
    text = _LATEX_CLINE_RE.sub("", text)
    text = _LATEX_TABLE_ENV_RE.sub(_convert_latex_table, text)
    # FIX_BATCH9 task 1: \begin{cases}/HTML <table> -- different environment
    # names from tabular/array above, so no interaction/ordering risk.
    text = _LATEX_CASES_ENV_RE.sub(_convert_latex_cases, text)
    text = _HTML_TABLE_RE.sub(_convert_html_table, text)
    text = _LATEX_ARRAY_ENV_RE.sub("", text)
    # FIX_BATCH4 task 1: a bare, out-of-table "\hline" was found used as a
    # generic horizontal-rule marker (p50) -- strip it globally, not only
    # inside a captured table body (where _convert_latex_table already did).
    text = _LATEX_HLINE_RE.sub("", text)
    text = _LATEX_DOLLAR_RE.sub("", text)
    text = _LATEX_DOTS_RE.sub("...", text)
    text = _LATEX_QQUAD_RE.sub("  ", text)
    # FIX_BATCH7 task 2: \; \, \! spacing commands have no plain-text
    # equivalent worth keeping -- delete, same family as \qquad above.
    text = _LATEX_SPACING_CMD_RE.sub("", text)
    text = _LATEX_DOT_ACCENT_RE.sub(lambda m: m.group(1) + _COMBINING_DOT_ABOVE, text)
    text = _LATEX_TEXT_RE.sub(lambda m: m.group(1), text)
    text, overline_count = _LATEX_OVERLINE_RE.subn(lambda m: m.group(1), text)
    # FIX_BATCH7 task 2: \underline{X} -> X (same early-extraction timing as
    # \text/\overline above, before superscripts resolve below).
    text = _LATEX_UNDERLINE_RE.sub(lambda m: m.group(1), text)
    # FIX_BATCH7 task 2: \phantom{...} is pure alignment padding -- delete
    # outright (balanced-brace aware, see _strip_phantom's docstring).
    text, _ = _strip_phantom(text)
    text = _LATEX_LEFT_RIGHT_RE.sub(lambda m: m.group(1), text)
    # FIX_BATCH7 task 2: single-digit subscript (X_0..X_9) -> Unicode
    # subscript digit.
    text = _LATEX_SUB_BARE_RE.sub(lambda m: _SUBSCRIPT_MAP[m.group(1)], text)
    text = _LATEX_MATHBB_RE.sub(lambda m: _MATHBB_MAP.get(m.group(1), m.group(0)), text)
    # FIX_BATCH9 task 1: Gemini-emitted styled Unicode (bold/italic/etc.
    # math alphanumerics) -> plain ASCII, before superscripts/frac below so
    # a styled letter inside either doesn't block their own regexes (none
    # of sup.py's or _LATEX_FRAC_RE's character classes accept U+1D400+).
    text = normalize_math_italic(text)

    # FIX_BATCH4 task 1 bugfix (extended by FIX_BATCH9 task 1): superscripts
    # (via sup.py's fix(), which also handles letter/operator exponents like
    # "m+n", not just digits/n) and \frac/\dfrac/\tfrac/\sqrt(incl. indexed)
    # each need the OTHER to have already cleared any braces in their way
    # before they can fully resolve -- e.g. a^{\frac{1}{2}}'s superscript
    # braces can't resolve (sup.fix's braced regex requires brace-free
    # content) until the INNER \frac resolves first, but an OUTER \frac
    # like \frac{1}{(12)^{\frac{1}{2}}} (page 84 batch 9) can't resolve
    # until ITS argument's superscript braces are gone -- which only
    # happens once that inner \frac is already plain. A single ordered pass
    # (superscripts once, then frac repeatedly, as FIX_BATCH4 originally
    # did) only resolves one direction; alternating ONE pass of each,
    # repeated to a fixed point, resolves both. Verified against this exact
    # nested page-84 case before relying on it (see CURRENT_BATCH.md).
    for _ in range(_FRAC_MAX_PASSES):
        new_text = sup.fix(text)
        new_text = _LATEX_SQRT_INDEXED_RE.sub(_convert_indexed_sqrt, new_text)
        new_text = _LATEX_SQRT_RE.sub(
            lambda m: f"√{m.group(1)}" if len(m.group(1)) == 1 else f"√({m.group(1)})", new_text
        )
        if _LATEX_FRAC_RE.search(new_text):
            new_text = _convert_frac_once(new_text)
        if new_text == text:
            break
        text = new_text

    text = _SUBSETEQ_GARBLED_RE.sub("⊆", text)
    for cmd, repl in _LATEX_SYMBOL_MAP.items():
        text = text.replace(cmd, repl)
    text = _LATEX_ESCAPED_BRACE_RE.sub(r"\1", text)  # \{ -> {, \} -> }
    return text, overline_count


# FIX_BATCH2 task 2: deterministic fixes for specific recurring OCR
# mis-readings found on batch 2 review (paper/check/ERRORS_LOG.csv, batch=2).
# "আবৃ্ত" (hasant in the wrong place) is always a misreading of "আবৃত্ত" in
# these books. "আবৃত"/"অনাবৃত" on their own (missing the trailing ্ত conjunct)
# are likewise almost always "আবৃত্ত"/"অনাবৃত্ত" misread -- the (?!্ত) guard
# skips the word where it's already spelled correctly, so this never
# double-applies. "আ" (independent vowel, used in "আবৃত") and "া" (the vowel
# SIGN used inside "অনাবৃত") are different Unicode characters, so the two
# words never collide here even without extra lookaround.
_AABRIT_TYPO_RE = re.compile(r"আবৃ্ত")
_AABRIT_WORD_RE = re.compile(r"আবৃত(?!্ত)")
_ONABRIT_WORD_RE = re.compile(r"অনাবৃত(?!্ত)")
_MOSTOBYO_RE = re.compile(r"মস্তব্য")

# FIX_BATCH3 task 1: a specific, short list of words where Gemini sometimes
# doubles the very first character ("উউদাহরণ", "মমন্তব্য") -- NOT a general
# "collapse any doubled Bangla letter" rule (that would wrongly collapse
# legitimate doubled consonants elsewhere), just these named words.
_DOUBLED_FIRST_LETTER_WORDS = ["উদাহরণ", "মন্তব্য", "সমাধান"]
_DOUBLED_FIRST_LETTER_RES = [
    (re.compile(re.escape(w[0] + w)), w) for w in _DOUBLED_FIRST_LETTER_WORDS
]

# FIX_BATCH4 task 1: the book prints "উদাহরণ ৭." (a Western full stop after
# the example number), but OCR sometimes writes the Bangla sentence-ending
# "।" (dari) there instead. Scoped narrowly to right after "উদাহরণ <number>"
# -- NOT a general "replace । with ." rule, which would wrongly touch every
# ordinary Bangla sentence ending.
_UDAHARON_PERIOD_RE = re.compile(r"(উদাহরণ\s+[0-9০-৯]+)।")

# FIX_BATCH5 task 1: this book's own regular spelling is "বীজগাণিতিক", not
# "বীজগণিতিক" -- recurs throughout Chapter 3 (ERRORS_LOG batch=5, pages
# 48/49/50: "বীজগণিতিক x13" / systematic chapter-title misspelling).
_BIJOGANITIK_RE = re.compile(r"বীজগণিতিক")

# FIX_BATCH5 task 1: the book always writes the full "দুইটি", never the
# contracted "দুটি" -- a plain substring replace also fixes "দুটিকে" ->
# "দুইটিকে" as a side effect, since "দুটি" is a literal prefix of "দুটিকে".
# FIX_BATCH13 task 1: that same substring-replace nature was a real bug --
# with no word-boundary guard, the pattern also matched the "দুটি" hiding
# INSIDE the unrelated, already-correct word "বিন্দুটি" ("বি"+"ন্দুটি"),
# turning it into the nonsense "বিন্দুইটি" (ERRORS_LOG batch=13, pages 123
# and 124 -- confirmed against each page's raw.txt: Gemini's own reading was
# already correct, this function broke it). Python's `\b` doesn't reliably
# treat Bangla conjuncts/matras as word characters, so a lookbehind for ANY
# preceding Bangla character (the full Bengali Unicode block, U+0980-U+09FF)
# is used instead of `\b` -- this blocks exactly the mid-word case
# ("ন্দুটি") while still matching "দুটি" at a real word start (preceded by
# whitespace, punctuation, or the start of the text), so "দুটিকে"/"দুটির"
# etc. (the intentional prefix-match side effect above) keep working.
_DUTI_RE = re.compile(r"(?<![ঀ-৿])দুটি")

# FIX_BATCH5 task 1: doubled আ-কার misread ("উদাাহরণ" for "উদাহরণ", page 43).
# MUST run before _UDAHARON_PERIOD_RE above so a page with BOTH typos (e.g. a
# hypothetical "উদাাহরণ ৫।") gets the period fix too in the same pass -- see
# fix_known_bangla_typos()'s ordering below.
_UDAAHARON_RE = re.compile(r"উদাাহরণ")

# FIX_BATCH5 task 1: "সূত্র N।"/"অনুসিদ্ধান্ত N।" -> "...N." -- same
# dari-after-numbered-label fix as _UDAHARON_PERIOD_RE, for these two other
# labels (page 49: "সূত্র ১।", "সূত্র ২।").
# FIX_BATCH14 task 2(a): "উপপাদ্য" (theorem) added -- same bug, pages
# 125/133 ("উপপাদ্য ১১।" should be "উপপাদ্য ১১.").
_SUTRO_ANUSIDDHANTO_PERIOD_RE = re.compile(r"((?:সূত্র|অনুসিদ্ধান্ত|উপপাদ্য)\s+[0-9০-৯]+)।")

# FIX_BATCH6 task 1: a bare question-number at the very START of a line
# ("৩। ...") uses the book's Western full stop too, not the Bangla dari --
# page 59's exercise list ("১৩। যদি...", "১৪। ..."). Anchored to line start
# (^, re.MULTILINE) specifically so this never touches the already-handled
# LABELLED cases above (those require a preceding word like "উদাহরণ"/
# "সূত্র", so a line starting directly with a digit never matches them).
_QUESTION_NUMBER_PERIOD_RE = re.compile(r"^([0-9০-৯]+)। ", re.MULTILINE)

# FIX_BATCH7 task 2: "f (" -> "f(" -- a stray space after the function name
# "f" before its argument paren (pages 65/66/67: "f (− b/a)", "f (- b/a)").
# Scoped narrowly to literally "f" (the only function name this book's
# content has shown so far), not a general "any letter + space + paren"
# rule, which risks mangling ordinary Bangla/English prose that happens to
# end a word right before an unrelated "(".
_F_PAREN_SPACE_RE = re.compile(r"\bf \(")

# FIX_BATCH8 task 3: two more recurring OCR mis-readings. "নিয়ামাবলি" for
# "নিয়মাবলি" (page 80 batch 8: "সূচকের নিয়ামাবলি বর্ণনা..." -- an extra
# "া" inserted). "ফর্মী" for "ফর্মা" (noted back in batch 6 on page 54's
# footer, "ফর্মী-৫৪" style printing-signature marker, but not yet added to
# this function until now).
_NIYAMABOLI_RE = re.compile(r"নিয়ামাবলি")
_FORMI_RE = re.compile(r"ফর্মী")

# FIX_BATCH10 task 2: three more recurring OCR mis-readings (ERRORS_LOG
# batch=10). "লগ্নের" for "লগের" (page 95: "লগ্নের" -- an extra ্ন inserted
# into "log এর", i.e. "of the log", in the সাধারণ লগের পূর্ণক/অংশক section).
# "বহুম্পদী" for "বহুপদী" ("polynomial", page 100: "বহুম্পদী" x6 -- an extra
# ম inserted). "সংখ্যাক" for "সংখ্যক" (page 99: "সংখ্যাক" -- an extra া
# inserted; "সংখ্যক" is the correct "-numbered" suffix, e.g. "নির্দিষ্টসংখ্যক").
# FIX_BATCH13 task 1: _SONKHYAK_RE had the same substring-collision bug as
# _DUTI_RE, just in the OTHER direction -- "সংখ্যাক" (7 chars) is a literal
# PREFIX of "সংখ্যাকে" ("the number", object case: "সংখ্যা" + the everyday
# "-কে" case suffix), a completely common, correct word with nothing to do
# with the "-numbered" typo this pattern exists to fix. Unguarded, it would
# have rewritten "সংখ্যাকে" into the nonsense "সংখ্যকে" (confirmed: found 57
# real "সংখ্যাকে" occurrences across pages 1-130's raw OCR text that would
# hit this exact collision; none have actually been corrupted in the
# DELIVERED corpus yet only because every page containing one either
# predates this rule, which FIX_BATCH10 added, or was later manually
# reviewed -- so this was a live, armed bug, not merely a theoretical one).
# Fixed with a negative lookahead for the one continuation that actually
# causes the collision ("ে", U+09C7) -- "সংখ্যক" (the correct target
# spelling) is always the LAST element of its own compound and never takes
# a further suffix, so this guard costs no real fix, only blocks the false one.
_LOGNER_RE = re.compile(r"লগ্নের")
_BOHUMPODI_RE = re.compile(r"বহুম্পদী")
_SONKHYAK_RE = re.compile(r"সংখ্যাক(?!ে)")

# FIX_BATCH11 task 2: two more recurring OCR mis-readings (ERRORS_LOG
# batch=11, page 106's section heading). "দ্বিমাত" for "দ্বিঘাত"
# ("quadratic" -- দ্বি- + ঘাত, "power 2"; ঘ misread as ম). "বহুমপদী" for
# "বহুপদী" ("polynomial") -- a DIFFERENT misspelling from FIX_BATCH10's
# "বহুম্পদী" (that one has an extra hasant-ম conjunct; this one has a plain
# extra ম with no hasant at all), so it needs its own pattern, not a
# broadening of _BOHUMPODI_RE.
# FIX_BATCH13 task 1: _DBIMATO_RE had the same class of bug as _SONKHYAK_RE
# above -- "দ্বিমাত" (7 chars) is a literal PREFIX of "দ্বিমাত্রিক"
# ("two-dimensional", দ্বি- + মাত্রিক) AND of "দ্বিমাত্রা" ("two
# dimensions", দ্বি- + মাত্রা) -- both real geometry terms with nothing to
# do with "দ্বিঘাত" ("quadratic"). Confirmed live on page 106's own raw.txt
# (the exact page this pattern was written for): running fix_known_bangla_
# typos() on it corrupts "দ্বিমাত্রিক" into "দ্বিঘাত্রিক"; it only never
# showed up in page_106.txt itself because that page was later manually
# rewritten by a human (MANUAL_PAGES.txt), which papered over the bug
# without actually fixing it. Chapter 6 (solid geometry: points, lines,
# PLANES) is exactly the content now being processed (batch 14 onward), so
# "two-dimensional"/"two dimensions" were only going to come up more, not
# less. Both bad continuations start with "্র" (hasant + র, the start of
# "ত্রিক"/"ত্রা"), so one lookahead blocks both at once; the real typo
# "দ্বিমাত" is always followed by a space before "সমীকরণ" ("equation"), never by "্র".
_DBIMATO_RE = re.compile(r"দ্বিমাত(?!্র)")
_BOHUMPODI2_RE = re.compile(r"বহুমপদী")

# FIX_BATCH14 task 1: the geometric term "বিশেষ নির্বচন" ("particular
# enunciation" -- a standard part of every উপপাদ্য/theorem's structure)
# keeps coming back as "বিশেষ নির্বাচন" ("particular ELECTION") -- a
# real, different, much more common Bangla word, so a bare "নির্বাচন" ->
# "নির্বচন" substring rule would be far too broad (it would also wrongly
# rewrite "নির্বাচন" used in its own correct sense elsewhere, e.g. student
# council elections, and "বহুনির্বাচনি" -- "multiple-choice" -- which
# contains "নির্বাচন" as a literal substring but means something else
# again). Scoped to EXACTLY these two 2-word phrases (ERRORS_LOG batch=14,
# pages 131/133/134, all three instances of "বিশেষ নির্বাচন"; "সাধারণ
# নির্বচন" is the book's matching general-case counterpart, added
# pre-emptively since the same misreading is equally likely there).
_BISHESH_NIRBOCHON_RE = re.compile(r"বিশেষ নির্বাচন")
_SADHARAN_NIRBOCHON_RE = re.compile(r"সাধারণ নির্বাচন")

# FIX_BATCH14 task 2: two independent "উপপাদ্য N" (theorem N) heading
# mis-readings, found on different pages. (a) the book always prints a
# Western period after the number ("উপপাদ্য ১১."), but OCR sometimes wrote
# the Bangla dari instead ("উপপাদ্য ১১।", pages 125/133) -- same family as
# _SUTRO_ANUSIDDHANTO_PERIOD_RE just above, so "উপপাদ্য" is added into that
# same regex rather than a new one (see fix_known_bangla_typos()). (b) a
# separate misreading drops the "্য" (ya-phala) entirely -- "উপপাদ ১৫."
# instead of "উপপাদ্য ১৫." (page 135). Needs its own lookahead guard: "উপপাদ"
# (5 chars) is a literal PREFIX of the CORRECT "উপপাদ্য" (adds "্য" next),
# so without a guard this would also fire on an already-correct
# "উপপাদ্য N" and double up the fix into "উপপাদ্য্য N". Scoped instead to
# "উপপাদ" followed by whitespace then a digit (i.e. the broken heading
# with NO "্য" at all between the word and the number) -- "উপপাদ্য N" has
# "্য" immediately after "উপপাদ", not whitespace+digit, so it never
# matches. Also guarded on the left (no Bangla char immediately before)
# for the same reason _DUTI_RE needed one -- so this can never fire
# starting mid-word inside some longer, unrelated word.
# MUST run before _SUTRO_ANUSIDDHANTO_PERIOD_RE (now also handling
# "উপপাদ্য") so a page with BOTH bugs together ("উপপাদ ১৫।") gets the
# period fixed too in the same pass -- same reasoning/ordering as
# _UDAAHARON_RE running before _UDAHARON_PERIOD_RE above.
_UPOPADDO_MISSING_PHOLA_RE = re.compile(r"(?<![ঀ-৿])উপপাদ(?=\s+[০-৯])")


def fix_known_bangla_typos(text):
    """Returns (fixed_text, number_of_replacements_made)."""
    text, n1 = _AABRIT_TYPO_RE.subn("আবৃত্ত", text)
    text, n2 = _AABRIT_WORD_RE.subn("আবৃত্ত", text)
    text, n3 = _ONABRIT_WORD_RE.subn("অনাবৃত্ত", text)
    text, n4 = _MOSTOBYO_RE.subn("মন্তব্য", text)
    n5 = 0
    for pattern, word in _DOUBLED_FIRST_LETTER_RES:
        text, n = pattern.subn(word, text)
        n5 += n
    text, n6a = _UDAAHARON_RE.subn("উদাহরণ", text)
    text, n6 = _UDAHARON_PERIOD_RE.subn(r"\1.", text)
    text, n7 = _BIJOGANITIK_RE.subn("বীজগাণিতিক", text)
    text, n8 = _DUTI_RE.subn("দুইটি", text)
    # FIX_BATCH14 task 2(b): must run BEFORE the period-fix below, same
    # ordering reason as _UDAAHARON_RE/_UDAHARON_PERIOD_RE.
    text, n19 = _UPOPADDO_MISSING_PHOLA_RE.subn("উপপাদ্য", text)
    text, n9 = _SUTRO_ANUSIDDHANTO_PERIOD_RE.subn(r"\1.", text)
    text, n10 = _QUESTION_NUMBER_PERIOD_RE.subn(r"\1. ", text)
    text, n11 = _F_PAREN_SPACE_RE.subn("f(", text)
    text, n12 = _NIYAMABOLI_RE.subn("নিয়মাবলি", text)
    text, n13 = _FORMI_RE.subn("ফর্মা", text)
    text, n14 = _LOGNER_RE.subn("লগের", text)
    text, n15 = _BOHUMPODI_RE.subn("বহুপদী", text)
    text, n16 = _SONKHYAK_RE.subn("সংখ্যক", text)
    text, n17 = _DBIMATO_RE.subn("দ্বিঘাত", text)
    text, n18 = _BOHUMPODI2_RE.subn("বহুপদী", text)
    text, n20 = _BISHESH_NIRBOCHON_RE.subn("বিশেষ নির্বচন", text)
    text, n21 = _SADHARAN_NIRBOCHON_RE.subn("সাধারণ নির্বচন", text)
    return text, (
        n1 + n2 + n3 + n4 + n5 + n6a + n6 + n7 + n8 + n9 + n10 + n11 + n12
        + n13 + n14 + n15 + n16 + n17 + n18 + n19 + n20 + n21
    )


# FIX_BATCH3 task 1: model special tokens (e.g. "<bos>") leaking into the
# transcription -- strip them and flag so a human knows a token was there
# (there was often other OCR damage right next to it, e.g. page 22's
# "<bos>7র্মা-৩" for "ফর্মা-৩" -- the token strip doesn't fix the rest).
_MODEL_TOKEN_RE = re.compile(r"<(?:bos|eos|pad)>")


def strip_model_tokens(text):
    """Returns (text, token_leak_count)."""
    return _MODEL_TOKEN_RE.subn("", text)


# FIX_BATCH9 task 1: "log" followed by a Greek letter that Gemini uses as a
# visual stand-in for a subscript "b" -- Unicode's Latin-subscript-letters
# set has no "b" at all (only a,e,o,x,h,k,l,m,n,p,s,t), so when the book
# prints "log" with a subscript b (meaning "log base b"), Gemini sometimes
# substitutes a visually similar Greek subscript character instead: GREEK
# SUBSCRIPT SMALL LETTER CHI (page 88 batch 9: "logᵪM") or GREEK SUBSCRIPT
# SMALL LETTER BETA (page 89: "logᵦM"). Fixed to a literal "log_b" (plain
# underscore, since there's no real subscript-b glyph to use instead) and
# flagged so a human can double-check the base really was "b" in context.
_LOG_GREEK_SUBSCRIPT_RE = re.compile("log[ᵪᵦ]")


def fix_log_greek_subscript(text):
    """Returns (text, greek_subscript_count)."""
    return _LOG_GREEK_SUBSCRIPT_RE.subn("log_b", text)


# FIX_BATCH10 task 3: two more log-notation mis-readings (ERRORS_LOG
# batch=10, page 95, সাধারণ লগের পূর্ণক/অংশক section). "log₁0" -- subscript
# ONE (₁, U+2081) followed by a PLAIN zero ("0", U+0030) instead of
# subscript zero (₀, U+2080) -- the model got the "1" right but dropped out
# of subscript mode for the "0", so "log base 10" came out as a mix of two
# different digit styles. Fixed to proper "log₁₀" (both digits subscript).
# "log_e" (plain underscore + "e", with or without a trailing space before
# the next token) -- this book always means the natural log base "e" as a
# true subscript, "logₑ", the same convention as FIX_BATCH9's "log_b" fix
# except here a real Unicode subscript-e (ₑ, U+2091) DOES exist, so there's
# no need to fall back to a literal underscore like "log_b" did.
_LOG10_MIXED_RE = re.compile("log₁0")
_LOG_E_SPACE_RE = re.compile(r"log_e ")  # trailing space variant -- consumed, not kept
_LOG_E_RE = re.compile(r"log_e")  # bare variant (no trailing space to consume)


def fix_log_misnotation(text):
    """Returns (text, log_fixes_count)."""
    text, n1 = _LOG10_MIXED_RE.subn("log₁₀", text)
    # the space-trailing variant first, so the space is consumed along with
    # it -- logₑ attaches directly to its argument like log₂/log₁₀/logₐ do.
    text, n2 = _LOG_E_SPACE_RE.subn("logₑ", text)
    text, n3 = _LOG_E_RE.subn("logₑ", text)
    return text, n1 + n2 + n3


# FIX_BATCH11 task 3: "√(N)" where N is a single plain number (e.g. "√(3)y"
# on page 107, ERRORS_LOG batch=11 -- should be "√3y") -- redundant parens
# around a number the model already wrote with a real Unicode radical sign
# (not a `\sqrt{}` LaTeX command, which latex_to_plain's own single-
# character check above already handles). Scoped to a PURELY-digit group
# (Bangla or Latin) so an actual expression like "√(x+1)" keeps its
# necessary parens -- "একটি মাত্র সংখ্যা" (a single number) allows a
# multi-digit number like "12", just not a multi-token expression.
_SQRT_PAREN_NUMBER_RE = re.compile(r"√\(([0-9০-৯]+)\)")


def fix_sqrt_parens(text):
    """Returns (text, sqrt_parens_count)."""
    return _SQRT_PAREN_NUMBER_RE.subn(r"√\1", text)


# FIX_BATCH13 task 3(b): "||" between two 2-letter line-segment names (e.g.
# "AB || CD" meaning "line AB is parallel to line CD") -> the real Unicode
# parallel sign ∥ (U+2225, a DIFFERENT character from "|", U+007C, even
# though they render almost identically) -- a plain "||" risks the tutor
# reading it as nested absolute-value bars instead of "parallel to". Scoped
# to exactly two consecutive uppercase Latin letters on each side (this
# book's own naming convention for a line/segment, e.g. "AB", "CD") rather
# than a bare "||" anywhere, so an unrelated use of double-pipe (none seen
# in this corpus, but not worth risking) is left alone.
# FIX_BATCH13 task 3(b), real bug caught running batch 14: the task's own
# literal regex -- `([A-Z]{2})\s*\|\|\s*([A-Z]{2})` -> `\1 ∥ \2` -- CONSUMES
# both flanking tokens into its match, so a 3-way chain like page 139's
# real "AB || EF || CD" only converted the first "||" ("AB ∥ EF || CD") --
# "EF" was already spent as the first match's group 2, leaving nothing
# un-consumed on its left for a second match to anchor against. Fixed by
# matching ONLY the "||" itself, via fixed-width lookaround (Python's `re`
# allows a fixed-width lookbehind) instead of capturing the letters -- so
# neither token is ever consumed, and every "||" in a chain converts
# independently.
_PARALLEL_SYMBOL_RE = re.compile(r"(?<=[A-Z]{2})\s*\|\|\s*(?=[A-Z]{2})")


def fix_parallel_symbol(text):
    """Returns (text, parallel_count)."""
    return _PARALLEL_SYMBOL_RE.subn(" ∥ ", text)


# FIX_BATCH13 task 3(c): on geometry pages a figure's own labels (point
# names, angle marks, axis labels) sometimes get transcribed as their own
# separate lines of body text instead of staying attached to the diagram
# (page 130: ~30 such lines -- A, B, C, 2, 1, x, y, 40⁰, (i), (ii)). A
# SINGLE such line is ambiguous on its own (a real line of content could
# legitimately BE just "x" or "(i)" -- e.g. "∴ x = 5" or a sub-part
# heading), but a RUN of 3+ ones is a strong, safe signal that a whole
# cluster of figure labels leaked in -- removed outright. A run of only 1-2
# is left alone and merely flagged (figure_labels_suspect, see
# build_qc_note) for a human to check against the page image.
# FIX_BATCH14 task 3: the original version required the label lines to be
# LITERALLY consecutive (no line in between at all), which missed page
# 137's real labels (P, C, B, Q, A, R, D) -- each one was on its OWN line
# separated by a BLANK line from the next, so no run of 3 ever formed.
# find_figure_label_runs() now treats a blank line as transparent: it
# never breaks an in-progress run, but it also never counts toward the
# run's length on its own -- only actual label lines do. A removed run's
# span (see strip_figure_labels) still includes those interior blanks (so
# the whole cluster disappears together), collapsed down to exactly ONE
# blank line in the output rather than deleted outright, so two unrelated
# paragraphs on either side of the figure don't get mashed into one.
_FIGURE_LABEL_LINE_RE = re.compile(
    r"^(?:[A-Z]{1,2}|[0-9০-৯]{1,3}[°⁰]?|[xy]|\([ivxIVX]{1,4}\))$"
)
# FIX_BATCH14 task 4: the subset of the above that is a NUMBER (optionally
# with a degree sign, e.g. "30°", "40⁰", "120") -- the one label shape
# whose loss can make a question unanswerable (the question text refers to
# "the angle shown", answerable only from that number). Tracked separately
# so a removed run's lost values can be called out BY VALUE, not just
# counted.
_FIGURE_VALUE_LINE_RE = re.compile(r"^[0-9০-৯]{1,3}[°⁰]?$")


def _is_figure_label_line(line):
    stripped = line.strip()
    return bool(stripped) and len(stripped) <= 4 and bool(_FIGURE_LABEL_LINE_RE.match(stripped))


def find_figure_label_runs(text):
    """Returns (remove_spans, suspect_line_nums).
      - remove_spans: list of (start_line, end_line) 1-based INCLUSIVE
        ranges, one per cluster of >=3 figure-label-like lines
        (_is_figure_label_line) where every GAP between consecutive label
        lines in the cluster is blank-only -- the span runs from the
        cluster's first label line to its last (interior blanks included,
        but never reaching past the outermost label lines into ordinary
        surrounding blank/paragraph spacing).
      - suspect_line_nums: flat list of 1-based line numbers of label
        lines belonging to a cluster of only 1-2 (never removed, flag only)."""
    lines = text.split("\n")
    n = len(lines)
    remove_spans, suspect_nums = [], []
    i = 0
    while i < n:
        if not _is_figure_label_line(lines[i]):
            i += 1
            continue
        label_idxs = [i]
        j = i + 1
        while j < n:
            if _is_figure_label_line(lines[j]):
                label_idxs.append(j)
                j += 1
            elif lines[j].strip() == "":
                j += 1  # blank -- keeps the run open, doesn't extend/count it
            else:
                break
        if len(label_idxs) >= 3:
            remove_spans.append((label_idxs[0] + 1, label_idxs[-1] + 1))
        else:
            suspect_nums.extend(p + 1 for p in label_idxs)
        i = label_idxs[-1] + 1
    return remove_spans, suspect_nums


def strip_figure_labels(text):
    """Returns (text, removed_count, lost_values).
      - removed_count: number of actual LABEL lines removed (blank lines
        collapsed in the same spans don't count).
      - lost_values: comma-joined string of any number-shaped label lines
        (_FIGURE_VALUE_LINE_RE, e.g. "30°", "120") that were part of a
        removed run (FIX_BATCH14 task 4) -- empty string if none. Never
        reconstructed or guessed at -- flag only, for a human to add the
        real figure context back.
    Each remove_span (see find_figure_label_runs) -- the run's full line
    range, including any interior blank lines -- is collapsed down to a
    SINGLE blank line (keeping one blank line as a paragraph separator)
    rather than deleted outright. A shorter run (1-2 label lines) is left
    completely untouched (only flagged, see find_figure_labels_suspect_lines)."""
    remove_spans, _ = find_figure_label_runs(text)
    if not remove_spans:
        return text, 0, ""
    lines = text.split("\n")
    out = []
    cursor = 0
    removed_label_count = 0
    lost_values = []
    for start, end in remove_spans:
        start0, end0 = start - 1, end - 1
        out.extend(lines[cursor:start0])
        span_lines = lines[start0:end0 + 1]
        removed_label_count += sum(1 for ln in span_lines if _is_figure_label_line(ln))
        lost_values.extend(
            ln.strip() for ln in span_lines if _FIGURE_VALUE_LINE_RE.match(ln.strip())
        )
        out.append("")
        cursor = end0 + 1
    out.extend(lines[cursor:])
    return "\n".join(out), removed_label_count, ", ".join(lost_values)


def find_figure_labels_suspect_lines(text):
    """QC-only flag (never removed) -- see strip_figure_labels()."""
    _, suspect_nums = find_figure_label_runs(text)
    return suspect_nums


# FIX_BATCH9 task 1: Gemini occasionally writes a styled "Mathematical
# Alphanumeric Symbols" character (bold/italic/script/etc., U+1D400-
# U+1D7FF) instead of a plain ASCII letter/digit -- page 83 batch 9: "a𝑞"
# (MATHEMATICAL ITALIC SMALL Q) for plain "aq". These all have an official
# Unicode COMPATIBILITY decomposition to their plain ASCII equivalent, so
# unicodedata.normalize("NFKC", ...) is the correct, authoritative way to
# collapse them -- not a hand-built ~2000-entry mapping table (which would
# risk silently mapping some styled letter to the wrong plain one; verified
# directly against the real page-83 character before relying on this, not
# assumed from the Unicode block's known general layout). Scoped to just
# the matched run (not the whole page) so NFKC can't touch anything else
# incidentally (e.g. any fullwidth/ligature forms elsewhere in the text).
_MATH_ALPHANUM_RUN_RE = re.compile(r"[\U0001D400-\U0001D7FF]+")


def normalize_math_italic(text):
    return _MATH_ALPHANUM_RUN_RE.sub(lambda m: unicodedata.normalize("NFKC", m.group(0)), text)


# FIX_BATCH3 task 1: Devanagari characters leaking into Bangla text (e.g.
# "डिनार" instead of "ডিনার") -- flag only, never touched, since there's no
# safe deterministic way to guess the intended Bangla spelling from this.
# EXCLUDES U+0964 DEVANAGARI DANDA ("।") and U+0965 DOUBLE DANDA ("॥") --
# Unicode assigns the standard Bangla (and several other Indic scripts')
# sentence-ending punctuation INTO the Devanagari block, so "।" ends almost
# every Bangla sentence and is completely normal, not a script leak. Without
# this exclusion the flag fired on page 31's very first test (15-18 hits,
# only "।"), which would have made the flag noise on nearly every page and
# corrupted the Task 2 quality comparison (which uses this count) -- caught
# before running the real batch, not after.
_DEVANAGARI_RE = re.compile(r"[ऀ-ॣ०-ॿ]")


def count_devanagari(text):
    return len(_DEVANAGARI_RE.findall(text))


# FIX_BATCH6 task 2 (extended by FIX_BATCH8 task 1): script-leak families,
# flagged (never touched, same reasoning as devanagari_leak above -- no safe
# way to guess the intended Bangla spelling) under a new "script_leak"
# count, alongside the existing devanagari_leak: Cyrillic (U+0400-U+04FF --
# page 60 batch 6: "উৎপাদке" for "উৎপাদকে", a Cyrillic "ке" glued into a
# Bangla word), the two Assamese-only letters ৰ/ৱ (U+09F0/U+09F1 -- already
# seen misused inside a Bangla word in batch 4: "সম্পৰ্কযুক্ত" for
# "সম্পর্কযুক্ত", see ERRORS_LOG batch=4), and FIX_BATCH8's addition:
# Gurmukhi/Gujarati/Odia/Tamil, U+0A00-U+0BFF in ONE combined range per the
# task (page 76 batch 8: "বিশ্লেଷায়িত" for "বিশ্লেষায়িত", Odia letter ଷ
# U+0B37 glued into a Bangla word -- Odia's own block U+0B00-U+0B7F is a
# subset of this wider range, so it's covered without a separate entry).
_SCRIPT_LEAK_RE = re.compile(r"[Ѐ-ӿৰৱ਀-௿]")


def count_script_leak(text):
    return len(_SCRIPT_LEAK_RE.findall(text))


# FIX_BATCH2 task 3: a page that talks about recurring decimals ("আবৃত্ত" /
# "পৌনঃপুনিক") and contains a decimal number, but has NOT ONE U+0307
# combining-dot mark anywhere, almost certainly lost every recurring-decimal
# dot during OCR (see FIX_BATCH2.md's finding: flash-lite dropped them on
# p12/14/15/16/18/20 of batch 2). Triggers escalate_missing_recurring_dot().
_RECURRING_WORD_RE = re.compile(r"আবৃত্ত|পৌনঃপুনিক")
_DECIMAL_NUMBER_RE = re.compile(r"[0-9০-৯]+\.[0-9০-৯]+")


def detect_missing_recurring_dot(text):
    return bool(
        _RECURRING_WORD_RE.search(text)
        and _DECIMAL_NUMBER_RE.search(text)
        and _COMBINING_DOT_ABOVE not in text
    )


def count_recurring_dots(text):
    """FIX_BATCH2b task 2: NOT an escalation trigger, just a count for the
    human reviewer -- a page with any U+0307 is worth zooming into the image
    to check each dot landed on the right digit (dots were present but on
    the WRONG digit in several batch-2 pages even after the Task 1 prompt
    fix). Callers surface this as "has_recurring_dots (N)" in CURRENT_BATCH.md."""
    return text.count(_COMBINING_DOT_ABOVE)


def post_process(text):
    """Step 3b.3 margin-year stripping, FIX_BATCH5 margin-digit stripping,
    Step 3e.3 LaTeX-to-plain (incl. FIX_BATCH3's \\text/\\overline/nested-
    \\frac handling and FIX_BATCH9's dfrac/tfrac/indexed-sqrt/cases/HTML-
    table/math-italic additions), FIX_BATCH2 task 2 known-typo fixes (incl.
    FIX_BATCH3's doubled-first-letter words and FIX_BATCH5/6/8's additions),
    FIX_BATCH3's model-token stripping + Devanagari detection (plus
    FIX_BATCH6/8's Cyrillic/Assamese/Gurmukhi/Gujarati/Odia/Tamil script_leak
    detection), FIX_BATCH9's log-base Greek-subscript fix, FIX_BATCH10's
    log₁0/log_e notation fix, and FIX_BATCH11's √(N) parens-stripping fix.
    Returns (processed_text, counts) where counts is a dict with keys
    typo_fixes, token_leak, overline, devanagari_leak, margin_digit,
    script_leak, greek_subscript, log_fixes, sqrt_parens, parallel_fixes,
    figure_labels_removed, figure_values_lost, margin_year_tail (any may
    be 0/empty). FIX_BATCH13 task 3 added parallel_fixes/
    figure_labels_removed (plus MARGIN_YEAR_TOKENS' 2021/2022 entries,
    inside strip_margin_year itself); FIX_BATCH14 tasks 4/5 added
    figure_values_lost and margin_year_tail."""
    text = strip_margin_year(text)
    text, margin_digit_count = strip_margin_digit(text)
    text, overline_count = latex_to_plain(text)
    text, typo_count = fix_known_bangla_typos(text)
    text, token_leak_count = strip_model_tokens(text)
    text, greek_subscript_count = fix_log_greek_subscript(text)
    text, log_fixes_count = fix_log_misnotation(text)
    text, sqrt_parens_count = fix_sqrt_parens(text)
    text, parallel_count = fix_parallel_symbol(text)
    text, figure_labels_removed_count, figure_values_lost = strip_figure_labels(text)
    # FIX_BATCH14 task 5: runs AFTER figure-label stripping so that if a
    # label run sat right before the margin year, the year is still
    # correctly seen as the page's last non-empty line once that run has
    # already collapsed.
    text, margin_year_tail = strip_margin_year_tail(text)
    devanagari_count = count_devanagari(text)
    script_leak_count = count_script_leak(text)
    return text, {
        "typo_fixes": typo_count,
        "token_leak": token_leak_count,
        "overline": overline_count,
        "devanagari_leak": devanagari_count,
        "margin_digit": margin_digit_count,
        "script_leak": script_leak_count,
        "greek_subscript": greek_subscript_count,
        "log_fixes": log_fixes_count,
        "sqrt_parens": sqrt_parens_count,
        "parallel_fixes": parallel_count,
        "figure_labels_removed": figure_labels_removed_count,
        "figure_values_lost": figure_values_lost,
        "margin_year_tail": margin_year_tail,
    }


RETRY_ATTEMPTS = 3  # 1 original + 2 retries, per FULL_OCR.md
RETRY_BACKOFF_S = [2, 4]

# Step 3e: real, OFFICIAL price for gemini-3.5-flash-lite, verified directly on
# ai.google.dev/gemini-api/docs/pricing (2026-10-07) -- not third-party-sourced,
# unlike the same number used provisionally for the projections in Step 3d.
PRICE_PER_1K_INPUT_TOKENS = 0.0003   # $0.30 / 1M input tokens
PRICE_PER_1K_OUTPUT_TOKENS = 0.0025  # $2.50 / 1M output tokens (thinking included)
COST_STOP_THRESHOLD_USD = 7.00  # Step 3e.6 (was $4.00)

MATH_INDICATOR_CHARS = set("∈∉∪∩∅∴⊂⊆×−≤≥±′\\{}()[]/+=") | set("0123456789০১২৩৪৫৬৭৮৯") | set("⁰¹²³⁴⁵⁶⁷⁸⁹ⁿ")

RUN_LOG_FIELDS = ["book", "page", "time", "model", "input_tokens", "output_tokens", "status", "error"]


# Step 3e.5: fixed book order for the Step 4 full run (NOT curriculum.json's own
# 6/7/8/9General/9Higher order) -- class 9-10 books first (both General and
# Higher, bn then en each), then 8, 7, 6, each bn then en.
BOOK_ORDER = [
    "class_9_General_math_bn", "class_9_General_math_en",
    "class_9_Hiher_math_bn", "class_9_Higher_math_en",
    "class_8_math_bn", "class_8_math_en",
    "class_7_math_bn", "class_7_math_en",
    "class_6_math_bn", "class_6_math_en",
]


def load_books():
    """Returns [{"book": stem, "lang": "bn"/"en", "pdf_path": ..., "class":int, "book_type":str}, ...]
    straight from curriculum.json -- the same source backend/run_full_ocr.py uses, so this
    naturally excludes the 4 class_10_*.pdf duplicate files (see FULL_OCR_INVENTORY.md) --
    but returned in BOOK_ORDER (Step 3e.5), not curriculum.json's own book order."""
    curriculum = json.load(open(CURRICULUM_PATH, encoding="utf-8"))
    by_stem = {}
    for b in curriculum["books"]:
        for lang, fname_key, subdir in [("bn", "bangla_file", "bangla"), ("en", "english_file", "english")]:
            fname = b[fname_key]
            stem = os.path.splitext(fname)[0]
            by_stem[stem] = {
                "book": stem,
                "lang": lang,
                "class": b["class"],
                "book_type": b["book_type"],
                "pdf_path": os.path.join(PDF_ROOT, subdir, fname),
            }
    return [by_stem[stem] for stem in BOOK_ORDER if stem in by_stem]


def get_page_count(pdf_path):
    doc = fitz.open(pdf_path)
    n = doc.page_count
    doc.close()
    return n


def render_page_image(pdf_path, page_number_1based, dpi=DPI):
    """Renders one page to a PIL Image in memory -- never written to disk unless
    the caller explicitly saves it (--save-images-to)."""
    doc = fitz.open(pdf_path)
    page = doc[page_number_1based - 1]
    zoom = dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat)
    img = Image.open(io.BytesIO(pix.tobytes("png")))
    doc.close()
    return img


def output_path(book):
    return os.path.join(OUT_ROOT, book)


def page_output_file(book, page):
    return os.path.join(output_path(book), f"page_{page}.txt")


def already_done(book, page):
    p = page_output_file(book, page)
    return os.path.exists(p) and os.path.getsize(p) > 0


def read_prior_cost_usd():
    """Sums every prior RUN_LOG.csv row WHERE model == GEMINI_MODEL (across ALL
    previous invocations of this script) so the $7 stop (Step 3e.6) tracks
    actual spend under the current model/price, not a mix of this and the
    Steps 2-3d rows made under gemini-3.6-flash at a different real price --
    see the module docstring for why that distinction matters here."""
    if not os.path.exists(RUN_LOG_PATH):
        return 0.0, 0, 0
    total_in = total_out = 0
    with open(RUN_LOG_PATH, encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if row.get("model") != GEMINI_MODEL:
                continue
            try:
                total_in += int(row.get("input_tokens") or 0)
                total_out += int(row.get("output_tokens") or 0)
            except ValueError:
                continue
    cost = (total_in / 1000) * PRICE_PER_1K_INPUT_TOKENS + (total_out / 1000) * PRICE_PER_1K_OUTPUT_TOKENS
    return cost, total_in, total_out


def append_run_log(rows):
    os.makedirs(OUT_ROOT, exist_ok=True)
    is_new = not os.path.exists(RUN_LOG_PATH)
    with open(RUN_LOG_PATH, "a", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=RUN_LOG_FIELDS)
        if is_new:
            w.writeheader()
        w.writerows(rows)


# finish_reason values that mean the model refused to produce the page at all
# (content-policy style stop, not a transient error) -- retrying the identical
# request at temperature 0 will almost certainly fail identically every time, so
# these are NOT retried (see call_gemini_once's docstring for how this was found).
BLOCKED_FINISH_REASONS = {"SAFETY", "RECITATION", "PROHIBITED_CONTENT", "BLOCKLIST", "SPII"}


def image_to_png_b64(image):
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


def call_gemini_once(model, image, temperature, prompt=None):
    """Returns (text, input_tokens, output_tokens, finish_reason, blocked).
    `model` is normally unused/None (kept for call-site compatibility with the
    pre-Step-3e SDK-based signature) and falls back to the fixed module-wide
    GEMINI_MODEL -- EXCEPT for FIX_BATCH1 task 3's RECITATION-escalation ladder
    (see escalate_blocked_page()), which explicitly passes a different model
    name (e.g. "gemini-3.6-flash") as strategy (c). `prompt` similarly defaults
    to the module-wide PROMPT but escalation strategy (b) overrides it with an
    accessibility-framing variant.

    Called via raw REST (requests), not the google-generativeai SDK, since
    Step 3e.1 moved the whole pipeline to gemini-3.5-flash-lite with an
    explicit thinkingConfig.thinkingLevel -- the installed SDK (0.8.2) cannot
    express thinkingConfig at all (confirmed in Step 3d by inspecting its
    compiled proto types directly: the field simply isn't there), and
    separately has a real bug where its own `.text` property crashes on an
    empty candidate (see paper/results/FULL_OCR_PILOT.md) by trying to read a
    `finish_message` field its proto type doesn't know about either. REST
    sidesteps both: this function parses the plain JSON response directly and
    never touches anything resembling that property.

    Raises RuntimeError on a non-200 HTTP response (caught by call_with_retry,
    same contract call_with_retry already expected from the old SDK-exception
    version) -- the error message is the API's own JSON error body, inspected
    by is_model_not_found/is_insufficient_balance below.

    output_tokens = totalTokenCount - promptTokenCount, not candidatesTokenCount
    (see FULL_OCR_PILOT.md for why -- gemini-3.6-flash's hidden "thinking"
    tokens weren't reflected in candidatesTokenCount at all). At
    thinkingLevel=minimal this gap is usually ~0 (confirmed in Step 3d: exactly
    0 on 10/10 test calls), but the formula is kept for correctness on any call
    where it isn't."""
    model_name = model or GEMINI_MODEL
    prompt_text = prompt or PROMPT
    url = f"{API_BASE}/models/{model_name}:generateContent"
    body = {
        "contents": [{"parts": [{"text": prompt_text}, {"inline_data": {"mime_type": "image/png", "data": image_to_png_b64(image)}}]}],
        "generationConfig": {"temperature": temperature, "thinkingConfig": {"thinkingLevel": THINKING_LEVEL}},
    }
    resp = requests.post(url, params={"key": settings.gemini_api_key}, json=body, timeout=120)
    data = resp.json()
    if resp.status_code != 200:
        raise RuntimeError(f"HTTP {resp.status_code}: {json.dumps(data, ensure_ascii=False)[:1000]}")

    usage = data.get("usageMetadata", {})
    input_tokens = usage.get("promptTokenCount", 0)
    total_tokens = usage.get("totalTokenCount", 0)
    output_tokens = max(0, total_tokens - input_tokens)

    finish_reason = None
    blocked = False
    text = ""
    candidates = data.get("candidates", [])
    if candidates:
        candidate = candidates[0]
        finish_reason = candidate.get("finishReason")
        parts = candidate.get("content", {}).get("parts", [])
        if parts:
            text = "".join(p.get("text", "") for p in parts)
        elif finish_reason in BLOCKED_FINISH_REASONS:
            blocked = True
    return text, input_tokens, output_tokens, finish_reason, blocked


def is_model_not_found(exc):
    msg = str(exc).lower()
    return ("404" in msg or "not_found" in msg) and "model" in msg


def is_insufficient_balance(exc):
    msg = str(exc).lower()
    return "insufficient" in msg and ("balance" in msg or "quota" in msg or "credit" in msg)


def strip_margin_year(text):
    """Step 3b.3: remove standalone margin-year tokens (২০২৩/২০২৪/২০২৫/২০২৬ or
    2023-2026) that appear on their own line, or glued onto the end of a content
    line after 10+ spaces (the signature of a rotated vertical-margin-year token
    getting swept into the transcription next to a content line)."""
    out_lines = []
    for line in text.split("\n"):
        if _MARGIN_YEAR_WHOLE_LINE_RE.match(line):
            continue  # drop the whole line
        line = _MARGIN_YEAR_TRAILING_RE.sub("", line)
        out_lines.append(line)
    return "\n".join(out_lines)


# FIX_BATCH14 task 5: strip_margin_year() above only catches a KNOWN year
# (MARGIN_YEAR_TOKENS -- the real printing years, 2021-2026). Page 137's
# margin year got misread as "২০২৯" (a year that was never actually
# printed in any of these books), which the fixed token list can't name in
# advance. Generalized rule: if the page's LAST non-empty line is exactly
# 4 digits (Bangla or Latin) starting with ২০/20, it's almost certainly
# that same rotated-margin-year artifact landing at the very end of the
# page (same position every other margin-year instance has been found in)
# -- stripped, regardless of which specific 4 digits it misread as.
# Deliberately scoped to ONLY the page's last non-empty line (never a
# middle line) -- a real 4-digit number used inside a word problem (a
# sum, a count, a different kind of year mentioned in the text) is never
# touched, since those can appear anywhere, not just as the final line.
_FOUR_DIGIT_YEAR_TAIL_RE = re.compile(r"^(?:২০[০-৯]{2}|20[0-9]{2})$")


def strip_margin_year_tail(text):
    """Returns (text, year_or_None) -- see module note above."""
    lines = text.split("\n")
    last_idx = None
    for i in range(len(lines) - 1, -1, -1):
        if lines[i].strip() != "":
            last_idx = i
            break
    if last_idx is None:
        return text, None
    candidate = lines[last_idx].strip()
    if not _FOUR_DIGIT_YEAR_TAIL_RE.match(candidate):
        return text, None
    del lines[last_idx]
    return "\n".join(lines), candidate


# FIX_BATCH5 task 2 (bullet 2): a content line ending in a tab followed by
# exactly ONE Bangla digit is a rotated margin-text fragment that leaked onto
# the line's end -- the same margin-leak family as the year-stripping above,
# but a single stray digit instead of a full year (page 41 batch 5: "...তৈরি
# করি।\t২", see ERRORS_LOG batch=5). Scoped to exactly one trailing digit so
# a legitimate 2-digit tab-separated page number (e.g. page 46's header
# "...ফাংশন\t৪১") is never touched.
_MARGIN_DIGIT_TRAILING_RE = re.compile(r"\t[০-৯]$", re.MULTILINE)


def strip_margin_digit(text):
    """Returns (text, margin_digit_count)."""
    return _MARGIN_DIGIT_TRAILING_RE.subn("", text)


def digit_sequence(line):
    return re.findall(r"[0-9০-৯]", line)


def find_digit_disagreements(book, page, primary_text, secondary_text):
    """Step 3b.2: flags every line where the two bn readings differ in any digit.

    A naive POSITIONAL line-by-line comparison (line i vs line i) was tried first
    and discarded: temperature-0 and temperature-0.4 readings of the same page
    don't always wrap text into the exact same line count (one extra/missing
    line anywhere on the page shifts every later line by one), which turned a
    single real wrapping difference into a cascade of dozens of false
    "disagreements" for every line after it -- the same failure mode already
    found and fixed in paper/scripts/day3_diff_hints.py's word-level diff.
    Fixed the same way: align with difflib.SequenceMatcher on lines first (which
    finds the real matching anchors instead of assuming strict position-for-
    position correspondence), skip 'equal' opcodes entirely (identical lines
    trivially have identical digits), and only compare digit sequences within
    the aligned non-equal blocks -- ignores non-digit differences, since this
    check exists specifically for the pilot's Bangla-digit-misread finding, not
    to catch every wording difference between the two readings."""
    primary_lines = primary_text.split("\n")
    secondary_lines = secondary_text.split("\n")
    matcher = difflib.SequenceMatcher(None, primary_lines, secondary_lines, autojunk=False)
    rows = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        a_block = primary_lines[i1:i2]
        b_block = secondary_lines[j1:j2]
        for offset, (a, b) in enumerate(itertools.zip_longest(a_block, b_block, fillvalue="")):
            if digit_sequence(a) != digit_sequence(b):
                line_no = i1 + offset + 1 if offset < len(a_block) else i1 + len(a_block)
                rows.append({"book": book, "page": page, "line": line_no, "reading1": a, "reading2": b})
    return rows


DIGIT_DISAGREEMENT_FIELDS = ["book", "page", "line", "reading1", "reading2"]
BLOCKED_PAGE_FIELDS = ["book", "page", "time", "lang", "resolution", "note"]


def append_csv(path, fields, rows):
    if not rows:
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    is_new = not os.path.exists(path)
    with open(path, "a", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        if is_new:
            w.writeheader()
        w.writerows(rows)


def math_density(text):
    if not text:
        return 0
    return sum(1 for ch in text if ch in MATH_INDICATOR_CHARS)


def read_ocr_raw_page(book, page):
    path = os.path.join(OCR_RAW_ROOT, book, f"page_{page}.txt")
    if not os.path.exists(path):
        return ""
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def pick_sample_pages(book, npages):
    """One page near the start, one in the middle, one with the heaviest math
    notation (by scanning the existing Tesseract ocr_raw text for this book --
    already complete for all 10 books, see FULL_OCR_INVENTORY.md). Falls back to
    evenly-spaced pages if ocr_raw text isn't available for some reason. Ensures
    3 DISTINCT page numbers."""
    start_page = max(2, round(npages * 0.08))
    middle_page = max(1, round(npages * 0.5))

    best_page, best_score = None, -1
    for p in range(1, npages + 1):
        score = math_density(read_ocr_raw_page(book, p))
        if score > best_score:
            best_score, best_page = score, p
    heavy_page = best_page if best_page is not None else min(npages, round(npages * 0.3))

    pages = [start_page, middle_page, heavy_page]
    seen = set()
    result = []
    for p in pages:
        q = p
        while q in seen and q < npages:
            q += 1
        while q in seen and q > 1:
            q -= 1
        seen.add(q)
        result.append(q)
    return sorted(set(result)) if len(set(result)) == 3 else sorted(result)


def call_with_retry(model, image, temperature, book, page, call_label, prompt=None):
    """One RUN_LOG row per call attempt-sequence. Retries transient errors up to
    RETRY_ATTEMPTS times with backoff; does NOT retry a content-policy block
    (deterministic, see call_gemini_once's docstring). Returns
    (text, input_tokens, output_tokens, finish_reason, blocked, log_row, hard_stop).

    `model`/`prompt` are forwarded to call_gemini_once (None -> its own
    defaults); the log row's "model" field always records the ACTUAL model
    name used (FIX_BATCH1 task 3's escalation ladder can call a different
    model than GEMINI_MODEL, and RUN_LOG must reflect that correctly, not the
    module default, so cost/history audits stay accurate)."""
    log_row = {
        "book": book,
        "page": page,
        "time": datetime.datetime.now().isoformat(timespec="seconds"),
        "model": model or GEMINI_MODEL,
        "input_tokens": 0,
        "output_tokens": 0,
        "status": "",
        "error": "",
    }
    last_error = None
    for attempt in range(1, RETRY_ATTEMPTS + 1):
        try:
            text, in_tok, out_tok, finish_reason, blocked = call_gemini_once(model, image, temperature, prompt=prompt)
            log_row["input_tokens"] = in_tok
            log_row["output_tokens"] = out_tok
            if blocked:
                log_row["status"] = f"BLOCKED {call_label} temp={temperature} ({finish_reason})"
                return text, in_tok, out_tok, finish_reason, True, log_row, None
            log_row["status"] = f"OK {call_label} temp={temperature} (attempt {attempt}, finish_reason={finish_reason})"
            return text, in_tok, out_tok, finish_reason, False, log_row, None
        except Exception as e:  # noqa: BLE001
            last_error = e
            if is_model_not_found(e):
                log_row["status"] = f"MODEL_NAME_FAILED {call_label}"
                log_row["error"] = str(e)[:500]
                return "", 0, 0, None, False, log_row, "MODEL_NOT_FOUND"
            if is_insufficient_balance(e):
                log_row["status"] = f"INSUFFICIENT_BALANCE {call_label}"
                log_row["error"] = str(e)[:500]
                return "", 0, 0, None, False, log_row, "INSUFFICIENT_BALANCE"
            print(f"  [WARN] {book} page {page} {call_label} attempt {attempt}/{RETRY_ATTEMPTS} failed: {e}")
            if attempt < RETRY_ATTEMPTS:
                time.sleep(RETRY_BACKOFF_S[attempt - 1])

    log_row["status"] = f"FAILED {call_label} (all {RETRY_ATTEMPTS} attempts)"
    log_row["error"] = str(last_error)[:500] if last_error else ""
    return "", 0, 0, None, False, log_row, None


ESCALATION_MODEL_C = "gemini-3.6-flash"  # FIX_BATCH1 task 3(c)


def escalate_blocked_page(image, book, page):
    """FIX_BATCH1 task 3: when every normal reading of a page (primary, and
    secondary for bn) came back RECITATION-blocked, try progressively
    different strategies before giving up to the Tesseract fallback -- in the
    exact order Peal specified:
      (a) same model, temp 0.4 (retried even for bn pages, where the normal
          secondary call already used 0.4 and was also blocked -- RECITATION
          is not perfectly deterministic page to page, so this is a genuine
          second attempt, not a guaranteed no-op)
      (b) same model/temp 0, but with an accessibility-framing sentence
          prepended to the prompt (ACCESSIBILITY_PREFIX)
      (c) a different, older model (gemini-3.6-flash), temp 0, same
          thinkingLevel=minimal
    Stops at the first strategy that returns usable (non-blocked, non-empty)
    text. Returns (text_or_None, label_or_None, log_rows, total_in, total_out,
    hard_stop) -- text is None only if all three strategies failed/blocked.

    FIX_BATCH12 task 1: this is no longer the last resort before Tesseract --
    when this returns None, process_page() now tries one more ladder step,
    escalate_split_page() (split the page in half and read each piece
    separately), before falling back to Tesseract. Kept as a separate
    function rather than a 4th entry in `attempts` below since it needs two
    image crops + a merge step, not one plain call_with_retry() like (a)-(c).
    Every attempt (successful or not) gets its own RUN_LOG row via
    call_with_retry, so which strategy worked (or that none did) is always
    visible in RUN_LOG.csv."""
    log_rows = []
    total_in = total_out = 0

    attempts = [
        ("escalate_temp0.4", 0.4, None, None),
        ("escalate_accessibility_prompt", 0, None, ACCESSIBILITY_PREFIX + PROMPT),
        (f"escalate_{ESCALATION_MODEL_C}", 0, ESCALATION_MODEL_C, None),
    ]
    for call_label, temperature, model_override, prompt_override in attempts:
        text, in_tok, out_tok, finish_reason, blocked, log_row, hard_stop = call_with_retry(
            model_override, image, temperature, book, page, call_label, prompt=prompt_override
        )
        log_rows.append(log_row)
        total_in += in_tok
        total_out += out_tok
        if hard_stop:
            return None, None, log_rows, total_in, total_out, hard_stop
        if not blocked and text:
            return text, call_label, log_rows, total_in, total_out, None

    return None, None, log_rows, total_in, total_out, None


# FIX_BATCH12 task 1: fraction of the page height that the two split halves
# overlap by -- Peal's "~৫% overlap". Split symmetrically around the
# midpoint so each half gets half of that overlap on its own edge (the
# overlapping BAND itself still ends up ~5% of the page tall in total).
SPLIT_OVERLAP_FRACTION = 0.05


def split_page_image(image):
    """FIX_BATCH12 task 1: crops `image` (a full page) into a top half and a
    bottom half with a ~5% overlap band straddling the vertical midpoint --
    a smaller image gives the model less to "recite" at once, which in
    practice is what tends to dodge a RECITATION block (Peal's own
    rationale for trying this). Returns (top_half, bottom_half), both PIL
    Images, same width as `image`."""
    width, height = image.size
    mid = height // 2
    half_overlap = int(height * SPLIT_OVERLAP_FRACTION / 2)
    top_half = image.crop((0, 0, width, min(height, mid + half_overlap)))
    bottom_half = image.crop((0, max(0, mid - half_overlap), width, height))
    return top_half, bottom_half


def merge_split_halves(top_text, bottom_text):
    """FIX_BATCH12 task 1: stitches the two half-page readings back into one
    page of text, dropping the duplicated lines the ~5% image overlap
    causes both halves to transcribe. Finds the longest run of lines near
    the boundary that both readings share (difflib.SequenceMatcher's
    find_longest_match) rather than assuming a fixed line count on either
    side -- same "align on real matching anchors" approach already used by
    find_digit_disagreements() above, for the same reason (the two calls
    don't reliably wrap text into identical line counts). If no matching
    run is found at all (the two halves' OCR differs too much to align),
    falls back to simple concatenation rather than silently dropping
    anything."""
    top_lines = top_text.split("\n")
    bottom_lines = bottom_text.split("\n")
    matcher = difflib.SequenceMatcher(None, top_lines, bottom_lines, autojunk=False)
    match = matcher.find_longest_match(0, len(top_lines), 0, len(bottom_lines))
    if match.size == 0:
        return "\n".join(top_lines + bottom_lines)
    merged_lines = top_lines[: match.a + match.size] + bottom_lines[match.b + match.size:]
    return "\n".join(merged_lines)


def escalate_split_page(image, book, page):
    """FIX_BATCH12 task 1: the escalation ladder's new last step, tried after
    escalate_blocked_page()'s three strategies all fail and BEFORE giving up
    to the Tesseract fallback. Splits the page image top/bottom
    (split_page_image(), ~5% overlap) and reads each half with GEMINI_MODEL
    at temp 0 as its own call_with_retry() attempt (call_label
    "escalate_split_top"/"escalate_split_bottom", each getting its own
    RUN_LOG row same as every other call), then merges the two readings with
    merge_split_halves(). Returns (text_or_None, log_rows, total_in,
    total_out, hard_stop) -- text is None if EITHER half is still
    blocked/empty, which is process_page()'s signal to fall back to
    Tesseract same as before."""
    log_rows = []
    total_in = total_out = 0
    top_img, bottom_img = split_page_image(image)
    half_texts = []
    for half_image, call_label in [(top_img, "escalate_split_top"), (bottom_img, "escalate_split_bottom")]:
        text, in_tok, out_tok, finish_reason, blocked, log_row, hard_stop = call_with_retry(
            None, half_image, PRIMARY_TEMPERATURE, book, page, call_label
        )
        log_rows.append(log_row)
        total_in += in_tok
        total_out += out_tok
        if hard_stop:
            return None, log_rows, total_in, total_out, hard_stop
        if blocked or not text:
            return None, log_rows, total_in, total_out, None
        half_texts.append(text)
    return merge_split_halves(half_texts[0], half_texts[1]), log_rows, total_in, total_out, None


def escalate_missing_recurring_dot(image, book, page):
    """FIX_BATCH2 task 3: triggered only when detect_missing_recurring_dot()
    flags a page's final text. One extra reading with gemini-3.6-flash
    (thinkingLevel minimal, temp 0, the same -- now dot-aware -- prompt).
    Promoted ONLY if that new reading itself contains at least one U+0307
    (i.e. actually recovered the dots, not just another dot-less reading).
    Returns (raw_text_or_None, processed_text_or_None, counts, log_row,
    input_tokens, output_tokens, hard_stop) -- the first two are None when
    the re-read is blocked/failed, or still has no recurring-dot marks
    (nothing worth promoting over the original)."""
    raw_text, in_tok, out_tok, finish_reason, blocked, log_row, hard_stop = call_with_retry(
        ESCALATION_MODEL_C, image, 0, book, page, "missing_dot_escalate_gemini-3.6-flash"
    )
    if hard_stop or blocked or not raw_text:
        return None, None, {}, log_row, in_tok, out_tok, hard_stop
    new_processed, counts = post_process(raw_text)
    if _COMBINING_DOT_ABOVE in new_processed:
        return raw_text, new_processed, counts, log_row, in_tok, out_tok, None
    return None, None, {}, log_row, in_tok, out_tok, None


# FIX_BATCH2b task 1: paper/check/MANUAL_PAGES.txt is the authoritative list
# of manually-fixed pages, one "<book>/page_N.txt" per line. Replaces
# FIX_BATCH2's hardcoded page_8/10 set -- that file already contains them, so
# a single file (editable without touching this script) now covers every
# manually-fixed page, marked with "[MANUAL" or not.
MANUAL_PAGES_PATH = os.path.join(CHECK_DIR, "MANUAL_PAGES.txt")
_MANUAL_PAGE_LINE_RE = re.compile(r"^(.+)/page_(\d+)\.txt\s*$")


def load_manual_pages():
    """Returns the set of (book, page) pairs listed in MANUAL_PAGES.txt
    (empty set if the file doesn't exist). Blank lines and lines that don't
    match "<book>/page_N.txt" are ignored rather than raising, since this
    file is hand-edited."""
    if not os.path.exists(MANUAL_PAGES_PATH):
        return set()
    pages = set()
    with open(MANUAL_PAGES_PATH, encoding="utf-8") as fh:
        for line in fh:
            m = _MANUAL_PAGE_LINE_RE.match(line.strip())
            if m:
                pages.add((m.group(1), int(m.group(2))))
    return pages


def is_manually_fixed(book, page, manual_pages=None):
    """FIX_BATCH2 / FIX_BATCH2b standing rule: never overwrite a page that is
    EITHER listed in paper/check/MANUAL_PAGES.txt OR whose existing output
    file's FIRST LINE starts with "[MANUAL" -- a human (Claude chat, from the
    page image), not Gemini/Tesseract, produced that text. The marker check
    stays dynamic (not file-dependent) so it protects any future
    manually-fixed page even before MANUAL_PAGES.txt is updated for it.
    Callers must skip such a page even when --force or the STALE_PILOT
    auto-force would otherwise reprocess it. `manual_pages` lets a caller
    pass an already-loaded set (e.g. main()'s loop) instead of re-reading the
    file on every page; omitted, it loads the file itself."""
    if manual_pages is None:
        manual_pages = load_manual_pages()
    if (book, page) in manual_pages:
        return True
    path = page_output_file(book, page)
    if not os.path.exists(path):
        return False
    with open(path, encoding="utf-8") as fh:
        return fh.readline().startswith("[MANUAL")


def process_page(model, book, lang, pdf_path, page, save_images_to):
    """Orchestrates Step 3b's full per-page pipeline:
      1. primary call (temp 0, all languages)
      2. secondary call (temp 0.4, bn only) -- Step 3b.2
      3. if BOTH succeeded (bn): FIX_BATCH3 task 2 picks whichever reading
         has fewer latex_left/token_leak/devanagari_leak/script_leak issues
         as the MAIN output (tie -> primary); the other becomes the .alt
         reading. If only
         primary is usable: it's the main, no .alt. If primary is blocked:
         promote a successful secondary; else, if both primary and secondary
         are blocked, try the FIX_BATCH1 task-3 escalation ladder
         (escalate_blocked_page()); only if THAT also fails does it fall back
         to the existing Tesseract raw text with the FALLBACK_MARKER line (3b.4)
      4. post-process (margin-year strip + LaTeX-to-plain + FIX_BATCH3's
         token/overline/devanagari/typo handling) and write page_N.txt/.raw.txt
         (+ page_N.alt.txt/.alt.raw.txt for the non-chosen bn reading, when one
         exists); QC flags from post-processing are logged on the producing
         call's RUN_LOG row
      5. digit-disagreement check between the two bn readings (3b.2)
    Returns (log_rows, total_in, total_out, hard_stop)."""
    image = render_page_image(pdf_path, page)
    if save_images_to:
        img_dir = os.path.join(save_images_to, book)
        os.makedirs(img_dir, exist_ok=True)
        image.save(os.path.join(img_dir, f"page_{page}.png"))

    is_bn = lang == "bn"
    log_rows = []
    total_in = total_out = 0

    p_text, p_in, p_out, p_fr, p_blocked, p_log, hard_stop = call_with_retry(
        model, image, PRIMARY_TEMPERATURE, book, page, "primary"
    )
    log_rows.append(p_log)
    total_in += p_in
    total_out += p_out
    if hard_stop:
        return log_rows, total_in, total_out, hard_stop

    s_text, s_blocked = None, False
    if is_bn:
        s_text, s_in, s_out, s_fr, s_blocked, s_log, hard_stop = call_with_retry(
            model, image, SECONDARY_TEMPERATURE, book, page, "secondary"
        )
        log_rows.append(s_log)
        total_in += s_in
        total_out += s_out
        if hard_stop:
            return log_rows, total_in, total_out, hard_stop

    blocked_note = None
    quality_note = None
    source_log_row = None
    alt_text, alt_log_row = None, None
    if is_bn and p_text and not p_blocked and s_text and not s_blocked:
        # FIX_BATCH3 task 2: both readings succeeded -- pick the cleaner one.
        p_processed, p_counts = post_process(p_text)
        s_processed, s_counts = post_process(s_text)
        p_issues = _quality_issue_count(p_processed, p_counts)
        s_issues = _quality_issue_count(s_processed, s_counts)
        # FIX_BATCH11 task 1: a wrong-script digit changes the actual math
        # (e.g. a page number or coefficient silently reads differently),
        # worse than the generic "cleanliness" issues _quality_issue_count
        # tracks -- so this check runs FIRST and overrides it when it fires.
        p_bangla_digits, p_latin_digits = count_script_digits_on_math_lines(p_processed)
        s_bangla_digits, s_latin_digits = count_script_digits_on_math_lines(s_processed)
        if p_bangla_digits > p_latin_digits and s_latin_digits > p_latin_digits:
            final_text, source, source_log_row = s_text, "secondary-promoted-digit-script", s_log
            alt_text, alt_log_row = p_text, p_log
            quality_note = (
                f"quality: promoted secondary over primary (script_digit_mismatch: primary "
                f"{p_bangla_digits} Bangla/{p_latin_digits} Latin vs secondary "
                f"{s_bangla_digits} Bangla/{s_latin_digits} Latin on math-like lines)"
            )
        elif s_issues < p_issues:
            final_text, source, source_log_row = s_text, "secondary-promoted-quality", s_log
            alt_text, alt_log_row = p_text, p_log
            quality_note = f"quality: promoted secondary over primary ({s_issues} < {p_issues} issues)"
        else:
            final_text, source, source_log_row = p_text, "primary", p_log
            alt_text, alt_log_row = s_text, s_log
            quality_note = f"quality: kept primary ({p_issues} <= {s_issues} issues)"
    elif not p_blocked:
        final_text, source = p_text, "primary"
        source_log_row = p_log
    elif is_bn and s_text and not s_blocked:
        final_text, source = s_text, "secondary-promoted"
        source_log_row = s_log
        blocked_note = "primary (temp 0) blocked; promoted secondary (temp 0.4) reading to be the page's output"
    else:
        esc_text, esc_label, esc_logs, esc_in, esc_out, esc_hard_stop = escalate_blocked_page(image, book, page)
        log_rows.extend(esc_logs)
        total_in += esc_in
        total_out += esc_out
        if esc_hard_stop:
            return log_rows, total_in, total_out, esc_hard_stop
        if esc_text:
            final_text, source = esc_text, esc_label
            source_log_row = esc_logs[-1]  # the escalation attempt that actually succeeded
            blocked_note = f"primary (and secondary, if bn) blocked; recovered via {esc_label}"
        else:
            # FIX_BATCH12 task 1: one more ladder step before giving up to
            # Tesseract -- split the page and read each half separately.
            split_text, split_logs, split_in, split_out, split_hard_stop = escalate_split_page(image, book, page)
            log_rows.extend(split_logs)
            total_in += split_in
            total_out += split_out
            if split_hard_stop:
                return log_rows, total_in, total_out, split_hard_stop
            if split_text:
                final_text, source = split_text, "escalate_split"
                source_log_row = split_logs[-1]  # the half that completed the merge
                blocked_note = "primary (and secondary, if bn) blocked, and the escalation ladder failed; recovered via escalate_split (page split top/bottom)"
            else:
                final_text = FALLBACK_MARKER + "\n" + read_ocr_raw_page(book, page)
                source = "tesseract-fallback"
                blocked_note = "every available Gemini reading, including the escalation ladder and split-page escalation, was blocked (RECITATION); used Tesseract raw text instead"

    os.makedirs(output_path(book), exist_ok=True)
    out_file = page_output_file(book, page)
    processed_primary = final_text
    if source == "tesseract-fallback":
        with open(out_file, "w", encoding="utf-8") as fh:
            fh.write(final_text)
        # No .raw.txt here -- there is no usable API text to keep a raw copy of.
    else:
        processed_primary, counts = post_process(final_text)
        dot_note = None

        # FIX_BATCH2 task 3: one extra gemini-3.6-flash reading if this page's
        # text looks like it lost its recurring-decimal dots.
        if detect_missing_recurring_dot(processed_primary):
            new_raw, new_processed, new_counts, dot_log_row, dot_in, dot_out, dot_hard_stop = (
                escalate_missing_recurring_dot(image, book, page)
            )
            log_rows.append(dot_log_row)
            total_in += dot_in
            total_out += dot_out
            if dot_hard_stop:
                return log_rows, total_in, total_out, dot_hard_stop
            if new_processed:
                final_text, processed_primary, counts = new_raw, new_processed, new_counts
                source = "promoted-missing-dot-gemini-3.6-flash"
                source_log_row = dot_log_row
                dot_note = "missing_recurring_dot: recovered via gemini-3.6-flash escalation"
            else:
                dot_note = "missing_recurring_dot: gemini-3.6-flash escalation did not recover dots either"

        if source_log_row is not None:
            extra_notes = [n for n in (quality_note, dot_note) if n]
            append_qc_note(source_log_row, processed_primary, counts, extra=extra_notes, book=book, pdf_page=page)

        raw_file = os.path.join(output_path(book), f"page_{page}.raw.txt")
        with open(raw_file, "w", encoding="utf-8") as fh:
            fh.write(final_text)
        with open(out_file, "w", encoding="utf-8") as fh:
            fh.write(processed_primary)

    if blocked_note:
        append_csv(
            BLOCKED_PAGES_PATH,
            BLOCKED_PAGE_FIELDS,
            [
                {
                    "book": book,
                    "page": page,
                    "time": datetime.datetime.now().isoformat(timespec="seconds"),
                    "lang": lang,
                    "resolution": source,
                    "note": blocked_note,
                }
            ],
        )

    # .alt file + digit-disagreement check: alt_text/alt_log_row are only set
    # when there were genuinely TWO usable bn readings (FIX_BATCH3 task 2's
    # quality branch, or the plain both-succeeded case) -- whichever one
    # DIDN'T become the main output. Never set for a blocked-primary
    # recovery or the escalation ladder, where there's no second usable
    # reading of this same page to keep.
    if alt_text is not None and alt_log_row is not None:
        alt_raw_file = os.path.join(output_path(book), f"page_{page}.alt.raw.txt")
        alt_file = os.path.join(output_path(book), f"page_{page}.alt.txt")
        with open(alt_raw_file, "w", encoding="utf-8") as fh:
            fh.write(alt_text)
        processed_secondary, alt_counts = post_process(alt_text)
        append_qc_note(alt_log_row, processed_secondary, alt_counts, book=book, pdf_page=page)
        with open(alt_file, "w", encoding="utf-8") as fh:
            fh.write(processed_secondary)

        disagreements = find_digit_disagreements(book, page, processed_primary, processed_secondary)
        append_csv(DIGIT_DISAGREEMENTS_PATH, DIGIT_DISAGREEMENT_FIELDS, disagreements)

    return log_rows, total_in, total_out, None


def load_stale_pilot_pages():
    """FIX_BATCH1 task 4: (book, page) pairs that were OCR'd under an older
    model (anything != GEMINI_MODEL -- i.e. the Steps 2-3d pilot/test rows made
    under gemini-3.6-flash) and have NOT since been redone under GEMINI_MODEL.
    These sit in backend/data/ocr_gemini/<book>/page_N.txt already (so
    already_done() would normally skip them) but are pre-final-settings text.
    They are deliberately NOT reprocessed by this function -- it only computes
    the set; main()'s per-page loop uses it to auto-force just these pages
    when the normal sequential run reaches their own book, so the whole corpus
    ends up under one consistent model without a special separate pass."""
    if not os.path.exists(RUN_LOG_PATH):
        return set()
    old_model_pages = set()
    current_model_pages = set()
    with open(RUN_LOG_PATH, encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            page_str = row.get("page")
            if not page_str:
                continue
            key = (row.get("book"), int(page_str))
            if row.get("model") == GEMINI_MODEL:
                current_model_pages.add(key)
            elif row.get("model"):
                old_model_pages.add(key)
    return old_model_pages - current_model_pages


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--books", type=str, default=None, help="comma-separated book stems to restrict to")
    ap.add_argument("--max-pages", type=int, default=None, help="stop after N newly-processed pages")
    ap.add_argument("--sample", action="store_true", help="pilot mode: 3 pages/book")
    ap.add_argument(
        "--pages",
        type=str,
        default=None,
        help="explicit book:page list, e.g. 'class_6_math_bn:156,class_7_math_bn:14' "
        "(Step 3c's 4-page cost test needs exact pages, not --sample's 3/book)",
    )
    ap.add_argument("--save-images-to", type=str, default=None, help="also save page PNGs here")
    ap.add_argument("--force", action="store_true", help="reprocess even if output already exists")
    ap.add_argument("--dry-run", action="store_true", help="print the plan, call nothing")
    ap.add_argument(
        "--reprocess-only",
        action="store_true",
        help="FIX_BATCH1 task 2: no API calls -- re-run post_process() on each "
        "page's EXISTING page_N.raw.txt (and page_N.alt.raw.txt, if present) "
        "and overwrite page_N.txt/.alt.txt. Pages with no raw.txt (e.g. a "
        "tesseract-fallback page) are skipped with a note, not an error.",
    )
    args = ap.parse_args()

    all_books = load_books()
    if args.books:
        wanted = set(args.books.split(","))
        all_books = [b for b in all_books if b["book"] in wanted]
        missing = wanted - {b["book"] for b in all_books}
        if missing:
            print(f"[WARN] --books named unknown stems (ignored): {sorted(missing)}")

    # Build the full page plan: list of (book_info, page_number)
    plan = []
    if args.pages:
        books_by_stem = {b["book"]: b for b in all_books}
        for item in args.pages.split(","):
            book_stem, _, page_str = item.partition(":")
            b = books_by_stem.get(book_stem)
            if not b:
                print(f"[WARN] --pages named unknown/excluded book stem (ignored): {book_stem}")
                continue
            npages = get_page_count(b["pdf_path"])
            plan.append((b, int(page_str), npages))
    else:
        for b in all_books:
            npages = get_page_count(b["pdf_path"])
            if args.sample:
                pages = pick_sample_pages(b["book"], npages)
            else:
                pages = list(range(1, npages + 1))
            for p in pages:
                plan.append((b, p, npages))

    if args.dry_run:
        print(f"Plan: {len(plan)} page(s) across {len(all_books)} book(s)")
        for b, p, npages in plan:
            status = "DONE" if already_done(b["book"], p) else "pending"
            print(f"  {b['book']:<28} page {p:>4}/{npages:<4} [{status}]")
        return

    if args.reprocess_only:
        reprocessed = 0
        skipped = 0
        log_buffer = []
        manual_pages = load_manual_pages()
        for b, p, npages in plan:
            book = b["book"]
            if is_manually_fixed(book, p, manual_pages):
                print(f"  [MANUAL_GUARD] {book} page {p}: manually fixed -- never overwritten, skipping")
                skipped += 1
                continue
            raw_file = os.path.join(output_path(book), f"page_{p}.raw.txt")
            if not os.path.exists(raw_file):
                print(f"  [SKIP] {book} page {p}: no raw.txt to reprocess (tesseract-fallback or not yet OCR'd)")
                skipped += 1
                continue
            with open(raw_file, encoding="utf-8") as fh:
                raw_text = fh.read()
            processed, counts = post_process(raw_text)
            note = build_qc_note(processed, counts, book=book, pdf_page=p)
            with open(page_output_file(book, p), "w", encoding="utf-8") as fh:
                fh.write(processed)
            log_buffer.append({
                "book": book, "page": p,
                "time": datetime.datetime.now().isoformat(timespec="seconds"),
                "model": GEMINI_MODEL, "input_tokens": 0, "output_tokens": 0,
                "status": "REPROCESS_ONLY",
                "error": note,
            })
            reprocessed += 1
            print(f"  [REPROCESSED] {book} page {p}" + (f"  ({note})" if note else ""))

            alt_raw_file = os.path.join(output_path(book), f"page_{p}.alt.raw.txt")
            if os.path.exists(alt_raw_file):
                with open(alt_raw_file, encoding="utf-8") as fh:
                    alt_raw_text = fh.read()
                alt_processed, alt_counts = post_process(alt_raw_text)
                alt_note = build_qc_note(alt_processed, alt_counts, book=book, pdf_page=p)
                alt_out_file = os.path.join(output_path(book), f"page_{p}.alt.txt")
                with open(alt_out_file, "w", encoding="utf-8") as fh:
                    fh.write(alt_processed)
                log_buffer.append({
                    "book": book, "page": p,
                    "time": datetime.datetime.now().isoformat(timespec="seconds"),
                    "model": GEMINI_MODEL, "input_tokens": 0, "output_tokens": 0,
                    "status": "REPROCESS_ONLY_ALT",
                    "error": alt_note,
                })
        if log_buffer:
            append_run_log(log_buffer)
        print(f"\nReprocessed {reprocessed} page(s), skipped {skipped} (no raw.txt / manually-fixed). No API calls, $0 cost.")
        return

    prior_cost, prior_in, prior_out = read_prior_cost_usd()
    print(f"Prior cumulative cost from RUN_LOG.csv: ${prior_cost:.4f} ({prior_in} in / {prior_out} out tokens)")
    if prior_cost >= COST_STOP_THRESHOLD_USD:
        print(f"[STOP] Prior cumulative cost ${prior_cost:.2f} already >= ${COST_STOP_THRESHOLD_USD:.2f} threshold. Not calling Gemini. Report to Peal.")
        return

    model = None  # unused -- REST call site needs no model object, see call_gemini_once
    stale_pilot_pages = load_stale_pilot_pages()  # FIX_BATCH1 task 4
    manual_pages = load_manual_pages()  # FIX_BATCH2b task 1

    processed_this_run = 0
    total_in, total_out = prior_in, prior_out
    log_buffer = []
    stop_reason = None

    for b, p, npages in plan:
        if args.max_pages is not None and processed_this_run >= args.max_pages:
            break
        if is_manually_fixed(b["book"], p, manual_pages):
            print(f"  [MANUAL_GUARD] {b['book']} page {p}: manually fixed -- never overwritten, skipping even with --force/STALE_PILOT")
            continue
        force_this_page = args.force
        if not force_this_page and (b["book"], p) in stale_pilot_pages:
            print(f"  [STALE_PILOT] {b['book']} page {p}: previously done under an older model -- forcing re-OCR with {GEMINI_MODEL}")
            force_this_page = True
        if already_done(b["book"], p) and not force_this_page:
            continue

        cur_cost = (total_in / 1000) * PRICE_PER_1K_INPUT_TOKENS + (total_out / 1000) * PRICE_PER_1K_OUTPUT_TOKENS
        if cur_cost >= COST_STOP_THRESHOLD_USD:
            stop_reason = f"cumulative cost ${cur_cost:.2f} reached the ${COST_STOP_THRESHOLD_USD:.2f} stop threshold"
            break

        print(f"Processing {b['book']} page {p}/{npages} ({b['lang']}) ...")
        page_log_rows, in_tok, out_tok, hard_stop = process_page(model, b["book"], b["lang"], b["pdf_path"], p, args.save_images_to)
        log_buffer.extend(page_log_rows)
        total_in += in_tok
        total_out += out_tok
        processed_this_run += 1

        if hard_stop == "MODEL_NOT_FOUND":
            stop_reason = f"model '{GEMINI_MODEL}' not found on page {b['book']}/{p} -- per rules, STOP and ask Peal, do not switch models"
            break
        if hard_stop == "INSUFFICIENT_BALANCE":
            stop_reason = f"API reported insufficient balance on page {b['book']}/{p}"
            break

        if len(log_buffer) >= 5:
            append_run_log(log_buffer)
            log_buffer = []

    if log_buffer:
        append_run_log(log_buffer)

    final_cost = (total_in / 1000) * PRICE_PER_1K_INPUT_TOKENS + (total_out / 1000) * PRICE_PER_1K_OUTPUT_TOKENS
    print(f"\nProcessed {processed_this_run} page(s) this run.")
    print(f"Cumulative tokens: {total_in} in / {total_out} out. Estimated cumulative cost: ${final_cost:.4f} (PLACEHOLDER price -- see docstring)")
    if stop_reason:
        print(f"[STOPPED] {stop_reason}")


if __name__ == "__main__":
    main()
