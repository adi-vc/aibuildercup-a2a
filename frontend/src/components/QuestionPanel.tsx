/**
 * QuestionPanel.tsx — Claim guard UI (P7).
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
}

export type AskResponse = AnsweredResponse | RefusalResponse;

const REFUSAL_HEADER: Record<string, string> = {
  superlative_comparative: '⚖️ Only what\'s verified',
  predictive: '🔮 Can\'t promise the future',
  competitor: '🏷️ Other brands',
  adversarial: '🛡️ Sticking to the source',
  out_of_domain: 'ℹ️ Off topic',
  safety: '⚠️ Ask a qualified person',
  subjective: '💭 A matter of taste',
  gap: '⚠️ Not in the source',
};

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
  const [isOpen, setIsOpen] = useState(false);
  const [question, setQuestion] = useState('');
  const [response, setResponse] = useState<AskResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!question.trim()) return;
    
    setLoading(true);
    setError(null);
    setResponse(null);

    try {
      const res = await fetch(`${apiBaseUrl}/v1/ask`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          manifest_id: manifestId,
          question: question.trim(),
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
      onQuestionAsked?.(question.trim(), data);
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to ask question');
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setQuestion('');
    setResponse(null);
    setError(null);
  };

  return (
    <div className={styles.container}>
      {!isOpen ? (
        <button
          className={styles.openButton}
          onClick={() => setIsOpen(true)}
          aria-label="Ask a question"
        >
          Ask ❓
        </button>
      ) : (
        <div className={styles.panel}>
          <div className={styles.header}>
            <h3>Ask a question</h3>
            <button
              className={styles.closeButton}
              onClick={() => {
                setIsOpen(false);
                handleReset();
              }}
              aria-label="Close"
            >
              ×
            </button>
          </div>

          {!response ? (
            <form onSubmit={handleSubmit} className={styles.form}>
              <input
                type="text"
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                placeholder="e.g., What's the warranty?"
                className={styles.input}
                maxLength={500}
                disabled={loading}
                autoFocus
              />
              <button
                type="submit"
                className={styles.submitButton}
                disabled={loading || !question.trim()}
              >
                {loading ? 'Asking...' : 'Ask'}
              </button>
            </form>
          ) : response.type === 'answered' ? (
            <div className={styles.answer}>
              <div className={styles.answerHeader}>Answer</div>
              <p className={styles.answerText}>{response.answer}</p>
              {response.quotes.map((q) => (
                <p key={q.fact_id} className={styles.sourceQuote}>
                  Source: “{q.quote}” <small>({q.span_id})</small>
                </p>
              ))}
              
              {response.facts_cited.length > 0 && (
                <div className={styles.citations}>
                  <div className={styles.citationsLabel}>
                    Based on {response.facts_cited.length} verified fact{response.facts_cited.length > 1 ? 's' : ''}
                  </div>
                  <div className={styles.factBadges}>
                    {response.facts_cited.map((factId) => (
                      <span key={factId} className={styles.factBadge} title={factId}>
                        ✓ {factId.replace('f_', '').replace(/_/g, ' ')}
                      </span>
                    ))}
                  </div>
                </div>
              )}
              
              <button onClick={handleReset} className={styles.askAnotherButton}>
                Ask another question
              </button>
            </div>
          ) : (
            <div className={styles.refusal}>
              <div className={styles.refusalHeader} data-refusal-type={response.refusal_type}>
                {REFUSAL_HEADER[response.refusal_type] ?? '⚠️ Cannot answer'}
              </div>
              <p className={styles.refusalReason}>{response.reason}</p>
              {response.nearest_fact && (
                <p className={styles.sourceQuote}>
                  Verified instead: “{response.nearest_fact.quote}” <small>({response.nearest_fact.span_id})</small>
                </p>
              )}
              
              {!response.nearest_fact && response.available_subjects.length > 0 && (
                <div className={styles.availableTopics}>
                  <div className={styles.availableLabel}>I can answer questions about:</div>
                  <ul className={styles.topicList}>
                    {response.available_subjects.slice(0, 5).map((subject) => (
                      <li key={subject}>{subject.replace(/_/g, ' ')}</li>
                    ))}
                  </ul>
                </div>
              )}
              
              <button onClick={handleReset} className={styles.askAnotherButton}>
                Ask another question
              </button>
            </div>
          )}

          {error && (
            <div className={styles.error}>
              <strong>Error:</strong> {error}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
