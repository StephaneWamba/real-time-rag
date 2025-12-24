import { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { apiService } from '../services/api';

interface MetricData {
  time: string;
  lag: number;
  latency: number;
}

export default function MetricsPanel() {
  const [updateLag, setUpdateLag] = useState<MetricData[]>([]);
  const [queryLatency, setQueryLatency] = useState<MetricData[]>([]);
  const [throughput, setThroughput] = useState({ updates: 0, queries: 0 });

  useEffect(() => {
    const fetchMetrics = async () => {
      try {
        const [updateMetrics, queryMetrics] = await Promise.all([
          apiService.getUpdateMetrics(),
          apiService.getQueryMetrics(),
        ]);

        const now = new Date();
        
        // Convert lag samples to chart data
        const lagSamples = updateMetrics.updates.lag_samples || [];
        const lagData: MetricData[] = lagSamples.map((lag, index) => ({
          time: new Date(now.getTime() - (9 - index) * 60000).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }),
          lag: lag,
          latency: 0,
        }));

        // Fill remaining slots if needed
        while (lagData.length < 10) {
          lagData.unshift({
            time: new Date(now.getTime() - (10 - lagData.length) * 60000).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }),
            lag: 0,
            latency: 0,
          });
        }

        // Convert latency samples to chart data
        const latencySamples = queryMetrics.queries.latency_samples || [];
        const latencyData: MetricData[] = latencySamples.map((latency, index) => ({
          time: new Date(now.getTime() - (9 - index) * 60000).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }),
          lag: 0,
          latency: latency,
        }));

        // Fill remaining slots if needed
        while (latencyData.length < 10) {
          latencyData.unshift({
            time: new Date(now.getTime() - (10 - latencyData.length) * 60000).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }),
            lag: 0,
            latency: 0,
          });
        }

        setUpdateLag(lagData.slice(-10));
        setQueryLatency(latencyData.slice(-10));
        setThroughput({
          updates: Math.floor(updateMetrics.updates.total / 60), // Rough estimate
          queries: Math.floor(queryMetrics.queries.total / 60), // Rough estimate
        });
      } catch (error) {
        console.error('Failed to fetch metrics:', error);
        // Fallback to empty data
        setUpdateLag([]);
        setQueryLatency([]);
      }
    };

    fetchMetrics();
    const interval = setInterval(fetchMetrics, 5000);

    return () => clearInterval(interval);
  }, []);

  const avgLag = updateLag.length > 0
    ? (updateLag.reduce((sum, d) => sum + d.lag, 0) / updateLag.length).toFixed(2)
    : '0.00';

  const avgLatency = queryLatency.length > 0
    ? (queryLatency.reduce((sum, d) => sum + d.latency, 0) / queryLatency.length).toFixed(2)
    : '0.00';

  return (
    <div className="panel bottom-panel">
      <div className="panel-header">
        <div>
          <h2 className="panel-title">Performance Metrics</h2>
          <p className="panel-description">
            <strong>Monitor system performance.</strong> Track how fast documents update and queries respond. Lower values are better—aim for update lag &lt;1s and query latency &lt;2s.
          </p>
        </div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
            <h3 style={{ fontSize: '0.875rem', fontWeight: '600', margin: 0 }}>
              Update Lag (Last 10 min)
            </h3>
            <span style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', cursor: 'help' }} title="Time from document change in PostgreSQL to vector update in Qdrant. Lower is better. Target: <1s">
              ⓘ
            </span>
          </div>
          <p style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>
            Time from DB change to vector update. Measures real-time processing speed.
          </p>
          <ResponsiveContainer width="100%" height={120}>
            <LineChart data={updateLag} margin={{ top: 10, right: 20, left: 0, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" opacity={0.3} />
              <XAxis 
                dataKey="time" 
                stroke="var(--text-secondary)" 
                fontSize={10}
                tick={{ fill: 'var(--text-secondary)' }}
              />
              <YAxis 
                stroke="var(--text-secondary)" 
                fontSize={10}
                tick={{ fill: 'var(--text-secondary)' }}
                domain={[0, 'dataMax + 0.2']}
              />
              <Tooltip 
                contentStyle={{ 
                  backgroundColor: 'var(--bg)', 
                  border: '1px solid var(--border)',
                  borderRadius: '6px',
                  fontSize: '0.75rem'
                }}
                formatter={(value: number) => [`${value.toFixed(2)}s`, 'Update Lag']}
              />
              <Line
                type="monotone"
                dataKey="lag"
                name="Update Lag"
                stroke="var(--accent)"
                strokeWidth={2}
                dot={{ r: 3, fill: 'var(--accent)' }}
                activeDot={{ r: 5, fill: 'var(--accent)' }}
              />
            </LineChart>
          </ResponsiveContainer>
          <div className="metric" style={{ marginTop: '0.5rem' }}>
            <span className="metric-label">Average</span>
            <span className="metric-value" style={{ color: parseFloat(avgLag) < 1 ? 'var(--success)' : 'var(--warning)' }}>
              {avgLag}s
            </span>
          </div>
        </div>

        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
            <h3 style={{ fontSize: '0.875rem', fontWeight: '600', margin: 0 }}>
              Query Latency (Last 10 min)
            </h3>
            <span style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', cursor: 'help' }} title="End-to-end time from query submission to answer delivery. Includes embedding, vector search, LLM generation, and response formatting. Target: <2s">
              ⓘ
            </span>
          </div>
          <p style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>
            End-to-end query response time. Includes embedding, search, and LLM generation.
          </p>
          <ResponsiveContainer width="100%" height={120}>
            <LineChart data={queryLatency} margin={{ top: 10, right: 20, left: 0, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" opacity={0.3} />
              <XAxis 
                dataKey="time" 
                stroke="var(--text-secondary)" 
                fontSize={10}
                tick={{ fill: 'var(--text-secondary)' }}
              />
              <YAxis 
                stroke="var(--text-secondary)" 
                fontSize={10}
                tick={{ fill: 'var(--text-secondary)' }}
                domain={[0, 'dataMax + 0.3']}
              />
              <Tooltip 
                contentStyle={{ 
                  backgroundColor: 'var(--bg)', 
                  border: '1px solid var(--border)',
                  borderRadius: '6px',
                  fontSize: '0.75rem'
                }}
                formatter={(value: number) => [`${value.toFixed(2)}s`, 'Query Latency']}
              />
              <Line
                type="monotone"
                dataKey="latency"
                name="Query Latency"
                stroke="var(--success)"
                strokeWidth={2}
                dot={{ r: 3, fill: 'var(--success)' }}
                activeDot={{ r: 5, fill: 'var(--success)' }}
              />
            </LineChart>
          </ResponsiveContainer>
          <div className="metric" style={{ marginTop: '0.5rem' }}>
            <span className="metric-label">Average</span>
            <span className="metric-value">{avgLatency}s</span>
          </div>
        </div>

        <div style={{ padding: '1rem', background: 'var(--bg-secondary)', borderRadius: '6px' }}>
          <div className="metric">
            <span className="metric-label" title="Number of document updates processed per second through the pipeline">
              Updates/sec
            </span>
            <span className="metric-value">{throughput.updates}</span>
          </div>
          <div className="metric">
            <span className="metric-label" title="Number of RAG queries answered per second">
              Queries/sec
            </span>
            <span className="metric-value">{throughput.queries}</span>
          </div>
        </div>
      </div>
    </div>
  );
}

