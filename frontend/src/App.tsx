import { useState, FormEvent } from "react";
import axios from "axios";
import ReactMarkdown from "react-markdown";
import remarkBreaks from "remark-breaks";

const API_URL = "http://localhost:8000/api/chat";

type Mode = "direct" | "reference";
type BookType = "general" | "higher";
type ContentType = "example" | "exercise";
type ClassChoice = "6" | "7" | "8" | "9-10";

interface GlossaryTerm {
  bn_term: string;
  en_term: string;
}

interface ChatResponse {
  solution: string;
  explanation: string;
  figure?: Record<string, unknown> | null;
  next_step?: string | null;
  practice_question?: string | null;
  confidence_score: number;
  llm_agreement: boolean;
  error_analysis?: string | null;
  glossary_terms?: GlossaryTerm[] | null;
}

const BANGLA_DIGITS = ["০", "১", "২", "৩", "৪", "৫", "৬", "৭", "৮", "৯"];
const toBangla = (n: number | string) =>
  String(n)
    .split("")
    .map((ch) => (ch >= "0" && ch <= "9" ? BANGLA_DIGITS[Number(ch)] : ch))
    .join("");
const toAsciiDigits = (s: string) =>
  s
    .split("")
    .map((ch) => {
      const i = BANGLA_DIGITS.indexOf(ch);
      return i === -1 ? ch : String(i);
    })
    .join("");

// Class 9 and 10 share one NCTB textbook (the SSC syllabus), so "৯-১০" always maps to
// the class=9 payload value — the ingested chunks in Qdrant are all tagged class=9 for
// this combined curriculum; nothing is tagged class=10.
const CLASS_CHOICES: { value: ClassChoice; classNumber: number }[] = [
  { value: "6", classNumber: 6 },
  { value: "7", classNumber: 7 },
  { value: "8", classNumber: 8 },
  { value: "9-10", classNumber: 9 },
];

const CLASS_LABEL_BN: Record<ClassChoice, string> = {
  "6": "৬",
  "7": "৭",
  "8": "৮",
  "9-10": "৯-১০",
};

const CLASS_LABEL_EN: Record<ClassChoice, string> = {
  "6": "6",
  "7": "7",
  "8": "8",
  "9-10": "9-10",
};

// Ordinal words for the natural-language Bangla query sent to the LLM (distinct from
// the numeral shown on the selector chip). English mode just uses "Class {n}" instead.
const CLASS_ORDINAL_BN: Record<ClassChoice, string> = {
  "6": "ষষ্ঠ",
  "7": "সপ্তম",
  "8": "অষ্টম",
  "9-10": "নবম-দশম",
};

const SUB_PROBLEM_OPTIONS: Record<Language, string[]> = {
  bn: ["", "ক", "খ", "গ", "ঘ", "ঙ"],
  en: ["", "a", "b", "c", "d", "e"],
};

type Language = "bn" | "en";

// Chapter names, keyed "<class>|<book_type>". Position in the array is the chapter
// number (1-based) sent to the backend — confirmed against real ingested chunk metadata
// (e.g. class 9 general chapter 2 = "সেট ও ফাংশন"/"Sets and Functions", class 8 general
// chapter 6 = "সরল সহসমীকরণ" both match this list's ordering exactly).
const CHAPTERS: Record<string, Record<Language, string[]>> = {
  "6|general": {
    bn: [
      "স্বাভাবিক সংখ্যা ও ভগ্নাংশ",
      "অনুপাত ও শতকরা",
      "পূর্ণসংখ্যা",
      "বীজগাণিতীয় রাশি",
      "সরল সমীকরণ",
      "জ্যামিতির মৌলিক ধারণা",
      "ব্যবহারিক জ্যামিতি",
      "তথ্য ও উপাত্ত",
    ],
    en: [
      "Natural Numbers and Fractions",
      "Ratios and Percentages",
      "Integers",
      "Algebraic Expressions",
      "Simple Equations",
      "Basic Concepts of Geometry",
      "Practical Geometry",
      "Information and Data",
    ],
  },
  "7|general": {
    bn: [
      "মূলদ ও অমূলদ সংখ্যা",
      "সমানুপাত ও লাভ-ক্ষতি",
      "পরিমাপ",
      "বীজগাণিতীয় রাশির গুণ ও ভাগ",
      "বীজগাণিতীয় সূত্রাবলি ও প্রয়োগ",
      "বীজগাণিতীয় ভগ্নাংশ",
      "সরল সমীকরণ",
      "সমান্তরাল সরলরেখা",
      "ত্রিভুজ",
      "সর্বসমতা ও সদৃশতা",
      "তথ্য ও উপাত্ত",
    ],
    en: [
      "Rational and Irrational Numbers",
      "Proportion, Profit and Loss",
      "Measurement",
      "Multiplication and Division of Algebraic Expressions",
      "Algebraic Formulae and Applications",
      "Algebraic Fractions",
      "Simple Equations",
      "Parallel Straight Lines",
      "Triangles",
      "Congruence and Similarity",
      "Information and Data",
    ],
  },
  "8|general": {
    bn: [
      "প্যাটার্ন",
      "মুনাফা",
      "পরিমাপ",
      "বীজগাণিতীয় সূত্রাবলি ও প্রয়োগ",
      "বীজগাণিতীয় ভগ্নাংশ",
      "সরল সহসমীকরণ",
      "সেট",
      "চতুর্ভুজ",
      "পিথাগোরাসের উপপাদ্য",
      "বৃত্ত",
      "তথ্য ও উপাত্ত",
    ],
    en: [
      "Patterns",
      "Profits",
      "Measurement",
      "Algebraic Formulae and Applications",
      "Algebraic Fractions",
      "Simple Simultaneous Equations",
      "Set",
      "Quadrilateral",
      "Pythagoras Theorem",
      "Circle",
      "Information and Data",
    ],
  },
  "9-10|general": {
    bn: [
      "বাস্তব সংখ্যা",
      "সেট ও ফাংশন",
      "বীজগাণিতিক রাশি",
      "সূচক ও লগারিদম",
      "এক চলকবিশিষ্ট সমীকরণ",
      "রেখা কোণ ও ত্রিভুজ",
      "ব্যবহারিক জ্যামিতি",
      "বৃত্ত",
      "ত্রিকোণমিতিক অনুপাত",
      "দূরত্ব ও উচ্চতা",
      "বীজগাণিতিক অনুপাত ও সমানুপাত",
      "দুই চলকবিশিষ্ট সরল সহসমীকরণ",
      "সসীম ধারা",
      "অনুপাত সদৃশতা ও প্রতিসমতা",
      "ক্ষেত্রফল সম্পর্কিত উপপাদ্য ও সম্পাদ্য",
      "পরিমিতি",
      "পরিসংখ্যান",
    ],
    en: [
      "Real Numbers",
      "Sets and Functions",
      "Algebraic Expressions",
      "Exponents and Logarithms",
      "Equations in One Variable",
      "Lines Angles and Triangles",
      "Practical Geometry",
      "Circle",
      "Trigonometric Ratio",
      "Distance and Elevation",
      "Algebraic Ratio and Proportion",
      "Simple Simultaneous Equations in Two Variables",
      "Finite Series",
      "Ratio Similarity and Symmetry",
      "Area Related Theorems and Constructions",
      "Mensuration",
      "Statistics",
    ],
  },
  "9-10|higher": {
    bn: [
      "সেট ও ফাংশন",
      "বীজগাণিতিক রাশি",
      "জ্যামিতি",
      "জ্যামিতিক অঙ্কন",
      "সমীকরণ",
      "অসমতা",
      "অসীম ধারা",
      "ত্রিকোণমিতি",
      "সূচকীয় ও লগারিদমীয় ফাংশন",
      "দ্বিপদী বিস্তৃতি",
      "স্থানাঙ্ক জ্যামিতি",
      "সমতলীয় ভেক্টর",
      "ঘন জ্যামিতি",
      "সম্ভাবনা",
    ],
    en: [
      "Set and Function",
      "Algebraic Expression",
      "Geometry",
      "Geometric Constructions",
      "Equation",
      "Inequality",
      "Infinite Series",
      "Trigonometry",
      "Exponential and Logarithmic Function",
      "Binomial Expansion",
      "Coordinate Geometry",
      "Planar Vector",
      "Solid Geometry",
      "Probability",
    ],
  },
};

const TEXT: Record<Language, {
  subtitle: string;
  modeDirect: string;
  modeReference: string;
  placeholder: string;
  submit: string;
  submitLoading: string;
  classLabel: string;
  bookTypeLabel: string;
  bookGeneral: string;
  bookHigher: string;
  chapterLabel: string;
  chapterPlaceholder: string;
  contentTypeLabel: string;
  contentTypeExample: string;
  contentTypeExercise: string;
  exampleLabel: string;
  exerciseLabel: string;
  exercisePlaceholder: string;
  problemLabel: string;
  subProblemLabel: string;
  subProblemNone: string;
  queryRequired: string;
  referenceIncomplete: string;
  connectionError: string;
}> = {
  bn: {
    subtitle: "NCTB গণিত সহকারী",
    modeDirect: "সরাসরি প্রশ্ন",
    modeReference: "রেফারেন্স",
    placeholder: "তোমার প্রশ্ন লেখো...",
    submit: "জিজ্ঞেস করো",
    submitLoading: "খুঁজছি...",
    classLabel: "শ্রেণি",
    bookTypeLabel: "বইয়ের ধরন",
    bookGeneral: "সাধারণ গণিত",
    bookHigher: "উচ্চতর গণিত",
    chapterLabel: "অধ্যায়",
    chapterPlaceholder: "অধ্যায় বেছে নাও",
    contentTypeLabel: "ধরন",
    contentTypeExample: "উদাহরণ",
    contentTypeExercise: "অনুশীলনী",
    exampleLabel: "উদাহরণ নম্বর",
    exerciseLabel: "অনুশীলনী নম্বর",
    exercisePlaceholder: "যেমন ১.১",
    problemLabel: "সমস্যা নম্বর",
    subProblemLabel: "অংশ (ঐচ্ছিক)",
    subProblemNone: "কোনোটি নয়",
    queryRequired: "প্রশ্ন লেখা আবশ্যক।",
    referenceIncomplete: "শ্রেণি, অধ্যায়, ধরন ও নম্বর সবগুলো বেছে নাও।",
    connectionError: "সার্ভারের সাথে সংযোগ করা যায়নি। Backend (http://localhost:8000) চালু আছে কিনা দেখো।",
  },
  en: {
    subtitle: "NCTB Math Assistant",
    modeDirect: "Direct Question",
    modeReference: "Reference",
    placeholder: "Type your question...",
    submit: "Ask",
    submitLoading: "Thinking...",
    classLabel: "Class",
    bookTypeLabel: "Book type",
    bookGeneral: "General Math",
    bookHigher: "Higher Math",
    chapterLabel: "Chapter",
    chapterPlaceholder: "Select chapter",
    contentTypeLabel: "Type",
    contentTypeExample: "Example",
    contentTypeExercise: "Exercise",
    exampleLabel: "Example No.",
    exerciseLabel: "Exercise",
    exercisePlaceholder: "e.g. 1.1",
    problemLabel: "Problem No.",
    subProblemLabel: "Part",
    subProblemNone: "None",
    queryRequired: "Please enter a question.",
    referenceIncomplete: "Please select class, chapter, type, and number.",
    connectionError: "Could not connect to the server. Check whether the backend (http://localhost:8000) is running.",
  },
};

function getConfidenceBadge(score: number): { label: string; classes: string } {
  if (score >= 0.9) {
    return { label: "উচ্চ আস্থা", classes: "bg-emerald-100 text-emerald-800 border-emerald-300" };
  }
  if (score >= 0.7) {
    return { label: "মধ্যম আস্থা", classes: "bg-amber-100 text-amber-800 border-amber-300" };
  }
  return { label: "কম আস্থা", classes: "bg-red-100 text-red-800 border-red-300" };
}

const selectClasses =
  "w-full rounded-xl border border-slate-300 p-2.5 text-slate-800 outline-none ring-emerald-500 focus:ring-2";

export default function App() {
  const [language, setLanguage] = useState<Language>("bn");
  const [mode, setMode] = useState<Mode>("direct");
  const [query, setQuery] = useState("");

  // Reference-mode dropdown chain state
  const [classChoice, setClassChoice] = useState<ClassChoice | "">("");
  const [bookType, setBookType] = useState<BookType | "">("");
  const [chapterIndex, setChapterIndex] = useState("");
  const [contentType, setContentType] = useState<ContentType | "">("");
  const [exampleNumber, setExampleNumber] = useState("");
  const [exerciseNumber, setExerciseNumber] = useState("");
  const [problemNumber, setProblemNumber] = useState("");
  const [subProblem, setSubProblem] = useState("");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [response, setResponse] = useState<ChatResponse | null>(null);

  const t = TEXT[language];
  const needsBookStep = classChoice === "9-10";
  const effectiveBookType: BookType | "" = needsBookStep ? bookType : "general";
  const chapterKey = classChoice ? `${classChoice}|${effectiveBookType || "general"}` : "";
  const chapterOptions = chapterKey ? CHAPTERS[chapterKey]?.[language] ?? [] : [];

  const resetFrom = (level: "class" | "book" | "chapter" | "contentType") => {
    if (level === "class") setBookType("");
    if (level === "class" || level === "book") setChapterIndex("");
    if (level === "class" || level === "book" || level === "chapter") setContentType("");
    setExampleNumber("");
    setExerciseNumber("");
    setProblemNumber("");
    setSubProblem("");
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setResponse(null);

    let payload: Record<string, unknown>;

    if (mode === "direct") {
      if (!query.trim()) {
        setError(t.queryRequired);
        return;
      }
      payload = { mode, query: query.trim(), language };
    } else {
      const classNumber = CLASS_CHOICES.find((c) => c.value === classChoice)?.classNumber;
      const chapterNum = Number(chapterIndex);
      const bt = effectiveBookType;

      const basicsMissing =
        !classChoice ||
        !bt ||
        !chapterNum ||
        !contentType ||
        (contentType === "example" ? !exampleNumber : !exerciseNumber || !problemNumber);

      if (basicsMissing) {
        setError(t.referenceIncomplete);
        return;
      }

      const exNumAscii = toAsciiDigits(exampleNumber);
      const exerciseAscii = toAsciiDigits(exerciseNumber);
      const probAscii = toAsciiDigits(problemNumber);

      let generatedQuery: string;
      const refPayload: Record<string, unknown> = {
        mode,
        class_number: classNumber,
        book_type: bt,
        chapter: chapterNum,
        content_type: contentType,
        language,
      };

      if (contentType === "example") {
        refPayload.problem_number = Number(exNumAscii);
        generatedQuery =
          language === "bn"
            ? `${CLASS_ORDINAL_BN[classChoice as ClassChoice]} শ্রেণি অধ্যায় ${toBangla(chapterNum)} উদাহরণ ${toBangla(exNumAscii)}`
            : `Class ${CLASS_LABEL_EN[classChoice as ClassChoice]} Chapter ${chapterNum} Example ${exNumAscii}`;
      } else {
        refPayload.exercise = exerciseAscii;
        refPayload.problem_number = Number(probAscii);
        if (subProblem) refPayload.sub_problem = subProblem;
        generatedQuery =
          language === "bn"
            ? `${CLASS_ORDINAL_BN[classChoice as ClassChoice]} শ্রেণি অধ্যায় ${toBangla(chapterNum)} অনুশীলনী ${toBangla(exerciseAscii)} ` +
              `${toBangla(probAscii)} নম্বর${subProblem ? " " + subProblem : ""}`
            : `Class ${CLASS_LABEL_EN[classChoice as ClassChoice]} Chapter ${chapterNum} Exercise ${exerciseAscii} ` +
              `Problem ${probAscii}${subProblem ? " Part " + subProblem : ""}`;
      }

      refPayload.query = generatedQuery;
      payload = refPayload;
    }

    setLoading(true);
    try {
      const res = await axios.post<ChatResponse>(API_URL, payload);
      setResponse(res.data);
    } catch (err) {
      if (axios.isAxiosError(err) && err.response) {
        const detail = (err.response.data as { detail?: string })?.detail;
        setError(detail ?? `সার্ভার ত্রুটি (status ${err.response.status})।`);
      } else {
        setError(t.connectionError);
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 px-4 py-8 sm:py-12">
      <div className="mx-auto w-full max-w-2xl">
        {/* Header */}
        <header className="relative mb-8 text-center">
          <div className="absolute right-0 top-0">
            <select
              value={language}
              onChange={(e) => setLanguage(e.target.value as Language)}
              aria-label="Language"
              className="rounded-full border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-700 outline-none ring-emerald-500 focus:ring-2"
            >
              <option value="bn">বাংলা</option>
              <option value="en">English</option>
            </select>
          </div>
          <h1 className="text-3xl font-bold text-emerald-700 sm:text-4xl">MathAI Bangladesh</h1>
          <p className="mt-1 text-slate-500">{t.subtitle}</p>
        </header>

        {/* Input Section */}
        <form
          onSubmit={handleSubmit}
          className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:p-6"
        >
          {/* Mode toggle */}
          <div className="mb-4 inline-flex w-full rounded-full bg-slate-100 p-1">
            <button
              type="button"
              onClick={() => setMode("direct")}
              className={`flex-1 rounded-full px-4 py-2 text-sm font-medium transition-colors ${
                mode === "direct" ? "bg-emerald-600 text-white shadow" : "text-slate-600"
              }`}
            >
              {t.modeDirect}
            </button>
            <button
              type="button"
              onClick={() => setMode("reference")}
              className={`flex-1 rounded-full px-4 py-2 text-sm font-medium transition-colors ${
                mode === "reference" ? "bg-emerald-600 text-white shadow" : "text-slate-600"
              }`}
            >
              {t.modeReference}
            </button>
          </div>

          {mode === "direct" ? (
            <textarea
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={t.placeholder}
              rows={4}
              className="w-full resize-none rounded-xl border border-slate-300 p-3 text-slate-800 outline-none ring-emerald-500 focus:ring-2"
            />
          ) : (
            <div className="flex flex-col gap-3">
              {/* Step 1: Class */}
              <select
                value={classChoice}
                onChange={(e) => {
                  setClassChoice(e.target.value as ClassChoice);
                  resetFrom("class");
                }}
                className={selectClasses}
              >
                <option value="">{t.classLabel}</option>
                {CLASS_CHOICES.map((c) => (
                  <option key={c.value} value={c.value}>
                    {t.classLabel} {language === "bn" ? CLASS_LABEL_BN[c.value] : CLASS_LABEL_EN[c.value]}
                  </option>
                ))}
              </select>

              {/* Step 2: Book type — class 9-10 only */}
              {needsBookStep && (
                <select
                  value={bookType}
                  onChange={(e) => {
                    setBookType(e.target.value as BookType);
                    resetFrom("book");
                  }}
                  className={selectClasses}
                >
                  <option value="">{t.bookTypeLabel}</option>
                  <option value="general">{t.bookGeneral}</option>
                  <option value="higher">{t.bookHigher}</option>
                </select>
              )}

              {/* Step 3: Chapter */}
              {classChoice && effectiveBookType && (
                <select
                  value={chapterIndex}
                  onChange={(e) => {
                    setChapterIndex(e.target.value);
                    resetFrom("chapter");
                  }}
                  className={selectClasses}
                >
                  <option value="">{t.chapterPlaceholder}</option>
                  {chapterOptions.map((name, i) => (
                    <option key={name} value={i + 1}>
                      {language === "bn" ? toBangla(i + 1) : i + 1}. {name}
                    </option>
                  ))}
                </select>
              )}

              {/* Step 4: Content type */}
              {chapterIndex && (
                <div className="inline-flex w-full rounded-full bg-slate-100 p-1">
                  <button
                    type="button"
                    onClick={() => {
                      setContentType("example");
                      setExerciseNumber("");
                      setProblemNumber("");
                      setSubProblem("");
                    }}
                    className={`flex-1 rounded-full px-4 py-2 text-sm font-medium transition-colors ${
                      contentType === "example" ? "bg-emerald-600 text-white shadow" : "text-slate-600"
                    }`}
                  >
                    {t.contentTypeExample}
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setContentType("exercise");
                      setExampleNumber("");
                    }}
                    className={`flex-1 rounded-full px-4 py-2 text-sm font-medium transition-colors ${
                      contentType === "exercise" ? "bg-emerald-600 text-white shadow" : "text-slate-600"
                    }`}
                  >
                    {t.contentTypeExercise}
                  </button>
                </div>
              )}

              {/* Step 5: Number input(s) */}
              {contentType === "example" && (
                <input
                  type="text"
                  inputMode="numeric"
                  value={exampleNumber}
                  onChange={(e) => setExampleNumber(e.target.value)}
                  placeholder={t.exampleLabel}
                  className={selectClasses}
                />
              )}

              {contentType === "exercise" && (
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                  <input
                    type="text"
                    value={exerciseNumber}
                    onChange={(e) => setExerciseNumber(e.target.value)}
                    placeholder={`${t.exerciseLabel} (${t.exercisePlaceholder})`}
                    className={selectClasses}
                  />
                  <input
                    type="text"
                    inputMode="numeric"
                    value={problemNumber}
                    onChange={(e) => setProblemNumber(e.target.value)}
                    placeholder={t.problemLabel}
                    className={selectClasses}
                  />
                  <select
                    value={subProblem}
                    onChange={(e) => setSubProblem(e.target.value)}
                    className={selectClasses}
                  >
                    <option value="">{t.subProblemNone}</option>
                    {SUB_PROBLEM_OPTIONS[language].filter(Boolean).map((letter) => (
                      <option key={letter} value={letter}>
                        {letter}
                      </option>
                    ))}
                  </select>
                </div>
              )}
            </div>
          )}

          {/* Submit button */}
          <button
            type="submit"
            disabled={loading}
            className="mt-4 flex w-full items-center justify-center gap-2 rounded-xl bg-emerald-600 px-4 py-3 font-medium text-white transition-colors hover:bg-emerald-700 disabled:cursor-not-allowed disabled:bg-emerald-300"
          >
            {loading && (
              <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
            )}
            {loading ? t.submitLoading : t.submit}
          </button>
        </form>

        {/* Error message */}
        {error && (
          <div className="mt-4 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
            {error}
          </div>
        )}

        {/* Response Section */}
        {response && (
          <div className="mt-6 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:p-6">
            <div className="mb-4 flex items-center justify-between gap-2">
              <h2 className="font-semibold text-slate-700">উত্তর</h2>
              {(() => {
                const badge = getConfidenceBadge(response.confidence_score);
                return (
                  <span
                    className={`rounded-full border px-3 py-1 text-xs font-medium ${badge.classes}`}
                  >
                    {badge.label}
                  </span>
                );
              })()}
            </div>

            <div className="[&_ol]:list-decimal [&_ol]:pl-5 [&_p]:mb-3 [&_p]:leading-relaxed [&_strong]:font-semibold [&_ul]:list-disc [&_ul]:pl-5 text-slate-800">
              <ReactMarkdown remarkPlugins={[remarkBreaks]}>{response.solution}</ReactMarkdown>
            </div>

            {response.glossary_terms && response.glossary_terms.length > 0 && (
              <div className="mt-4 flex flex-wrap gap-2 border-t border-slate-100 pt-4">
                {response.glossary_terms.map((term, i) => (
                  <span
                    key={`${term.bn_term}-${i}`}
                    className="rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-sm text-emerald-700"
                  >
                    {term.bn_term} ({term.en_term})
                  </span>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
