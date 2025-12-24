import { useState } from 'react';
import { apiService } from '../services/api';
import type { QueryResponse } from '../services/api';

export default function QueryPanel() {
  const [query, setQuery] = useState('');
  const [response, setResponse] = useState<QueryResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [latency, setLatency] = useState(0);

  const handleQuery = async () => {
    if (!query.trim()) return;

    setLoading(true);
    const startTime = Date.now();

    try {
      const result = await apiService.query({ query, top_k: 5 });
      setResponse(result);
      setLatency((Date.now() - startTime) / 1000);
    } catch (error) {
      console.error('Query failed:', error);
      setResponse(null);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="panel bottom-panel">
      <div className="panel-header">
        <div>
          <h2 className="panel-title">Ask Questions</h2>
          <p className="panel-description">
            <strong>Query your knowledge base.</strong> Type a question and get AI-powered answers with citations from your documents. The system searches recently updated vectors in real-time.
          </p>
        </div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        <div>
          <input
            className="input"
            placeholder="Ask a question..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleQuery()}
          />
          <button
            className="btn btn-primary"
            onClick={handleQuery}
            disabled={loading}
            style={{ width: '100%', marginTop: '0.5rem' }}
          >
            {loading ? 'Searching...' : 'Search'}
          </button>
        </div>

        {response && (
          <>
            <div style={{ padding: '1rem', background: 'var(--bg-secondary)', borderRadius: '6px' }}>
              <div style={{ marginBottom: '0.75rem' }}>
                <strong>Answer:</strong>
                <p style={{ marginTop: '0.5rem', fontSize: '0.875rem' }}>{response.answer}</p>
              </div>
              <div className="metric">
                <span className="metric-label">Confidence</span>
                <span className="metric-value">
                  {(response.confidence * 100).toFixed(0)}%
                </span>
              </div>
              <div className="metric">
                <span className="metric-label">Query Time</span>
                <span className="metric-value">{latency.toFixed(2)}s</span>
              </div>
            </div>

            {response.sources.length > 0 && (
              <div>
                <h3 style={{ fontSize: '0.875rem', fontWeight: '600', marginBottom: '0.5rem' }}>
                  Sources ({response.sources.length})
                </h3>
                <div className="list">
                  {response.sources.map((source, index) => (
                    <div key={index} className="list-item">
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span style={{ fontSize: '0.875rem' }}>Document {source.document_id.substring(0, 8)}</span>
                        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                          <span className="badge">v{source.version}</span>
                          {source.cited && <span className="badge badge-success">Cited</span>}
                        </div>
                      </div>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
                        Score: {source.score.toFixed(3)}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

