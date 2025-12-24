import { useState, useEffect } from 'react';
import './App.css';
import DocumentPanel from './components/DocumentPanel';
import PipelinePanel from './components/PipelinePanel';
import QueryPanel from './components/QueryPanel';
import MetricsPanel from './components/MetricsPanel';
import { apiService } from './services/api';
import type { HealthStatus } from './services/api';

function App() {
  const [isHealthy, setIsHealthy] = useState(false);

  useEffect(() => {
    const fetchHealth = async () => {
      try {
        const status: HealthStatus = await apiService.getHealth();
        setIsHealthy(status.status === 'healthy');
      } catch (error) {
        console.error('Failed to fetch health:', error);
        setIsHealthy(false);
      }
    };

    fetchHealth();
    const interval = setInterval(fetchHealth, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="app">
      <header className="header">
        <div>
          <h1>Real-Time RAG System</h1>
          <p className="header-subtitle">
            Watch documents update in real-time through a 6-stage pipeline. No reindexing required—changes flow automatically from database to vector store in under 1 second.
          </p>
        </div>
        <div className="status">
          <span className="status-dot" style={{ background: isHealthy ? 'var(--success)' : 'var(--error)' }}></span>
          <span>{isHealthy ? 'All systems operational' : 'System degraded'}</span>
        </div>
      </header>

      <main className="main">
        <div className="main-grid">
          <div className="pipeline-row">
            <PipelinePanel />
          </div>
          <div className="bottom-row">
            <DocumentPanel />
            <QueryPanel />
            <MetricsPanel />
          </div>
        </div>
      </main>
    </div>
  );
}

export default App;
