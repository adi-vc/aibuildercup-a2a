/**
 * QuestionPanel.tsx — Claim guard UI (P7), set inline in the Ask chapter.
 *
 * Allows viewers to ask questions about the product. Answers are generated
 * from verified facts only, and unsupported questions are refused on screen.
 *
 * Integrates with play-log: questions and refusals are recorded in the current
 * play segment (fields already exist from T6/P7.5).
 */

import { useState } from 'react';
import styles from './QuestionPanel.module.css';

export interface AnsweredResponse {
  type: 'answered';
  answer: string;
  facts_cited: string[];
  span_ids: string[];
  /** The verified source span behind each cited fact. */
  quotes: { fact_id: string; span_id: string; quote: string }[];
  question_type: string;
  question_type_id: number;
  /** Set for price answers: which §24.2 rung produced the value. */
  binding?: { rung: number } | null;
  model_used: string;
}

export interface RefusalResponse {
  type: 'refused';
  /** One of the §30 types, e.g. superlative_comparative, gap, predictive. */
  refusal_type: string;
  refusal_type_id: number;
  reason: string;
  /** The closest supported fact, offered instead (§20, type 3's bounded substitution). */
  nearest_fact: { fact_id: string; span_id: string; text: string; quote: string } | null;
  available_subjects: string[];
  question: string;
  model_used: string;
  /** Set when a model drafted an answer and the mechanical verifier threw it out: why. */
  rejected_draft?: string | null;
}

export type AskResponse = AnsweredResponse | RefusalResponse;

const REFUSAL_HEADER: Record<string, string> = {
  superlative_comparative: 'Only what’s verified',
  predictive: 'Can’t promise the future',
  competitor: 'Other brands',
  adversarial: 'Sticking to the source',
  out_of_domain: 'Off topic',
  safety: 'Ask a qualified person',
  subjective: 'A matter of taste',
  gap: 'Not in the source',
};

/**
 * F4: a refusal explains itself. Why this kind of question can't be answered from the
 * source, and what source would answer it (a refusal that names no reason was the
 * commonest complaint about competing tools; docs/research/replica/fixes.md).
 */
const REFUSAL_WHY: Record<string, { why: string; needs: string }> = {
  superlative_comparative: {
    why: '“Fastest” and “best” are rankings, and the spec sheet ranks it against nothing.',
    needs: 'A published test that names the other models would let it answer.',
  },
  predictive: {
    why: 'The spec sheet documents what is true today. A promise about later can’t be checked.',
    needs: 'A warranty or a durability test covering that period would let it answer.',
  },
  competitor: {
    why: 'The source describes this product only.',
    needs: 'Another brand’s claims need that brand’s own source.',
  },
  adversarial: {
    why: 'The question asks it to say what the source doesn’t, so it repeats only what the source supports.',
    needs: 'No instruction changes that.',
  },
  out_of_domain: {
    why: 'The source is a product spec sheet, and this is about something else.',
    needs: 'It would need a source on that subject.',
  },
  safety: {
    why: 'Safety advice needs a qualified person who knows your situation.',
    needs: 'No line in an ad can answer that safely.',
  },
  subjective: {
    why: 'Taste can’t be checked against a document.',
    needs: 'That one is yours to judge.',
  },
  gap: {
    why: 'No line in the spec sheet covers this, and it says nothing it can’t point to.',
    needs: 'A line in the spec sheet about it would let it answer.',
  },
};

/** One-tap questions for the stage demo: a supported fact, a ranking, a prediction. */
const SUGGESTIONS = ['Does it handle flooded roads?', 'Is it the fastest in India?', 'Will it last ten years?'];

interface Props {
  manifestId: string;
  locale: string;
  /** Viewer's city, so a price question follows the same binding ladder as the screen. */
  city?: string;
  profileHash: string;
  apiBaseUrl: string;
  onQuestionAsked?: (question: string, response: AskResponse) => void;
}

export function QuestionPanel({ manifestId, locale, city, profileHash, apiBaseUrl, onQuestionAsked }: Props) {
  const [question, setQuestion] = useState('');
  const [response, setResponse] = useState<AskResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const ask = async (q: string) => {
    if (!q.trim()) return;
    
    setLoading(true);
    setError(null);
    setResponse(null);

    try {
      const res = await fetch(`${apiBaseUrl}/v1/ask`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          manifest_id: manifestId,
          question: q.trim(),
          locale,
          city,
          profile_hash: profileHash,
        }),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({ detail: 'Unknown error' }));
        throw new Error(errData.detail || `HTTP ${res.status}`);
      }

      const data: AskResponse = await res.json();
      setResponse(data);
      
      // Notify parent (for play-log recording)
      onQuestionAsked?.(q.trim(), data);
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to ask question');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    void ask(question);
  };

  const trySuggestion = (q: string) => {
    setQuestion(q);
    void ask(q);
  };

  return (
    <div className={styles.container}>
      <form onSubmit={handleSubmit} className={styles.form}>
        <input
          type="text"
          name="question"
          autoComplete="off"
          aria-label="Your question"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask about range, charging, price…"
          className={styles.input}
          maxLength={500}
          disabled={loading}
        />
        <button type="submit" className={styles.submitButton} disabled={loading || !question.trim()}>
          {loading ? 'Asking…' : 'Ask'}
        </button>
      </form>

      <p className={styles.suggestions}>
        <span>Try</span>
        {SUGGESTIONS.map((q) => (
          <button key={q} type="button" className={styles.suggestion} onClick={() => trySuggestion(q)} disabled={loading}>
            {q}
          </button>
        ))}
      </p>

      <div aria-live="polite">
        {response?.type === 'answered' && (
          <div className={styles.answer}>
            <p className={styles.status} data-status="answered">Answered from the source</p>
            <p className={styles.answerText}>{response.answer}</p>
            {response.quotes.map((q) => (
              <p key={q.fact_id} className={styles.sourceQuote}>
                The spec sheet says “{q.quote}”.
              </p>
            ))}
          </div>
        )}

        {response && response.type !== 'answered' && (
          <div className={styles.refusal}>
            <p className={styles.status} data-status="refused" data-refusal-type={response.refusal_type}>
              {REFUSAL_HEADER[response.refusal_type] ?? 'Can’t answer that'}
            </p>
            <p className={styles.answerText}>{response.reason}</p>
            {REFUSAL_WHY[response.refusal_type] && (
              <p className={styles.why}>{REFUSAL_WHY[response.refusal_type].why}</p>
            )}
            {response.rejected_draft && (
              <p className={styles.why} data-rejected-draft>
                A drafted answer was checked against the source and thrown out: it {response.rejected_draft}.
              </p>
            )}
            {response.nearest_fact && (
              <p className={styles.sourceQuote}>Verified instead: “{response.nearest_fact.quote}”.</p>
            )}
            {REFUSAL_WHY[response.refusal_type] && (
              <p className={styles.sourceQuote}>{REFUSAL_WHY[response.refusal_type].needs}</p>
            )}
          </div>
        )}
      </div>

      {error && (
        <p className={styles.error} role="alert">
          The question didn’t reach the guard: {error}
        </p>
      )}
    </div>
  );
}
