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
  model_used: string;
}

export interface RefusalResponse {
  type: 'unsupported' | 'off_topic';
  reason: string;
  available_subjects: string[];
  question: string;
}

export type AskResponse = AnsweredResponse | RefusalResponse;

interface Props {
  manifestId: string;
  locale: string;
  profileHash: string;
  apiBaseUrl: string;
  onQuestionAsked?: (question: string, response: AskResponse) => void;
}

export function QuestionPanel({ manifestId, locale, profileHash, apiBaseUrl, onQuestionAsked }: Props) {
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
              <div className={styles.refusalHeader}>
                {response.type === 'unsupported' ? '⚠️ Cannot answer' : 'ℹ️ Off topic'}
              </div>
              <p className={styles.refusalReason}>{response.reason}</p>
              
              {response.available_subjects.length > 0 && (
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
