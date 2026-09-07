import { useState, FormEvent } from "react";
import axios from "axios";
import ReactMarkdown from "react-markdown";
import remarkBreaks from "remark-breaks";

const API_URL = "http://localhost:8000/api/chat";

type Mode = "direct" | "reference";

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

const CLASS_OPTIONS = [6, 7, 8, 9, 10];

type Language = "bn" | "en";

const TEXT: Record<Language, {
  subtitle: string;
  modeDirect: string;
  modeReference: string;
  placeholder: string;
  submit: string;
  submitLoading: string;
  classLabel: string;
  chapterLabel: string;
  exerciseLabel: string;
  queryRequired: string;
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
    chapterLabel: "অধ্যায়",
    exerciseLabel: "অনুশীলনী",
    queryRequired: "প্রশ্ন লেখা আবশ্যক।",
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
    chapterLabel: "Chapter",
    exerciseLabel: "Exercise",
    queryRequired: "Please enter a question.",
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

export default function App() {
  const [language, setLanguage] = useState<Language>("bn");
  const [mode, setMode] = useState<Mode>("direct");
  const [query, setQuery] = useState("");
  const [classNumber, setClassNumber] = useState("");
  const [chapter, setChapter] = useState("");
  const [exercise, setExercise] = useState("");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [response, setResponse] = useState<ChatResponse | null>(null);

  const t = TEXT[language];

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!query.trim()) {
      setError(t.queryRequired);
      return;
    }

    setLoading(true);
    setError(null);
    setResponse(null);

    const payload: Record<string, unknown> = { query: query.trim(), mode, language };
    if (mode === "reference") {
      if (classNumber) payload.class = Number(classNumber);
      if (chapter) payload.chapter = Number(chapter);
      if (exercise) payload.exercise = Number(exercise);
    }

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

          {/* Query input */}
          <textarea
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={t.placeholder}
            rows={4}
            className="w-full resize-none rounded-xl border border-slate-300 p-3 text-slate-800 outline-none ring-emerald-500 focus:ring-2"
          />

          {/* Reference mode fields */}
          {mode === "reference" && (
            <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-3">
              <select
                value={classNumber}
                onChange={(e) => setClassNumber(e.target.value)}
                className="w-full rounded-xl border border-slate-300 p-2.5 text-slate-800 outline-none ring-emerald-500 focus:ring-2"
              >
                <option value="">{t.classLabel}</option>
                {CLASS_OPTIONS.map((c) => (
                  <option key={c} value={c}>
                    {language === "bn" ? `শ্রেণি ${toBangla(c)}` : `Class ${c}`}
                  </option>
                ))}
              </select>
              <input
                type="number"
                min={1}
                value={chapter}
                onChange={(e) => setChapter(e.target.value)}
                placeholder={t.chapterLabel}
                className="w-full rounded-xl border border-slate-300 p-2.5 text-slate-800 outline-none ring-emerald-500 focus:ring-2"
              />
              <input
                type="number"
                min={1}
                value={exercise}
                onChange={(e) => setExercise(e.target.value)}
                placeholder={t.exerciseLabel}
                className="w-full rounded-xl border border-slate-300 p-2.5 text-slate-800 outline-none ring-emerald-500 focus:ring-2"
              />
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
