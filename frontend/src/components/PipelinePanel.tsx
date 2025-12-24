import { useState, useEffect, useRef } from 'react';
import { Database, RefreshCw, MessageSquare, Settings, Brain, Search } from 'lucide-react';
import { apiService } from '../services/api';

interface PipelineStage {
  name: string;
  Icon: React.ComponentType<{ size?: number }>;
  latency: number;
  status: 'idle' | 'active' | 'complete';
}

const initialStages: Omit<PipelineStage, 'latency' | 'status'>[] = [
  { name: 'PostgreSQL', Icon: Database },
  { name: 'Debezium', Icon: RefreshCw },
  { name: 'Kafka', Icon: MessageSquare },
  { name: 'Update Service', Icon: Settings },
  { name: 'Embedding', Icon: Brain },
  { name: 'Qdrant', Icon: Search },
];

export default function PipelinePanel() {
  const [stages, setStages] = useState<PipelineStage[]>(
    initialStages.map(s => ({ ...s, latency: 0, status: 'idle' as const }))
  );

  const [totalLatency, setTotalLatency] = useState(0);
  const [lastUpdate, setLastUpdate] = useState<string>('');
  const lastUpdateTimeRef = useRef<string | null>(null);
  const animationActiveRef = useRef(false);

  useEffect(() => {
    const timeouts: NodeJS.Timeout[] = [];
    
    const fetchPipelineStatus = async () => {
      try {
        const status = await apiService.getPipelineStatus();
        
        // Map backend stage names to frontend stages
        const stageMap: Record<string, string> = {
          'postgresql': 'PostgreSQL',
          'debezium': 'Debezium',
          'kafka': 'Kafka',
          'update_service': 'Update Service',
          'embedding': 'Embedding',
          'qdrant': 'Qdrant',
        };

        // Check if there's new activity (last_update changed and not currently animating)
        const hasNewActivity = status.last_update && 
                              status.last_update !== lastUpdateTimeRef.current &&
                              !animationActiveRef.current &&
                              status.total_latency > 0;
        
        if (hasNewActivity) {
          // Mark animation as active
          animationActiveRef.current = true;
          
          // Update the last update time to prevent re-triggering
          lastUpdateTimeRef.current = status.last_update;
          
          // Clear any existing timeouts
          timeouts.forEach(t => clearTimeout(t));
          timeouts.length = 0;
          
          // Reset all stages to idle first
          setStages(prev => prev.map(s => ({ ...s, status: 'idle' as const, latency: 0 })));
          
          // Animate stages sequentially
          const stageOrder = ['PostgreSQL', 'Debezium', 'Kafka', 'Update Service', 'Embedding', 'Qdrant'];
          const stageNames = Object.keys(stageMap);
          
          stageOrder.forEach((stageName, index) => {
            const timeout = setTimeout(() => {
              setStages(prev => prev.map(stage => {
                if (stage.name === stageName) {
                  const backendName = stageNames.find(key => stageMap[key] === stageName);
                  const latency = backendName ? (status.stages[backendName] || 0) : 0;
                  return {
                    ...stage,
                    latency,
                    status: 'active' as const,
                  };
                }
                // Mark previous stages as complete
                const stageIndex = stageOrder.indexOf(stage.name);
                if (stageIndex < index) {
                  const backendName = stageNames.find(key => stageMap[key] === stage.name);
                  const latency = backendName ? (status.stages[backendName] || 0) : 0;
                  return { ...stage, latency, status: 'complete' as const };
                }
                return stage;
              }));
            }, index * 300); // 300ms delay between each stage
            timeouts.push(timeout);
          });
          
          // After all stages complete, mark last one as complete
          const finalTimeout = setTimeout(() => {
            setStages(prev => prev.map((stage, idx) => {
              if (idx === prev.length - 1) {
                return { ...stage, status: 'complete' as const };
              }
              return stage;
            }));
          }, stageOrder.length * 300);
          timeouts.push(finalTimeout);
          
          // Reset all to idle after animation completes and mark animation as inactive
          const resetTimeout = setTimeout(() => {
            setStages(prev => prev.map(s => ({ ...s, status: 'idle' as const })));
            animationActiveRef.current = false;
          }, stageOrder.length * 300 + 1500);
          timeouts.push(resetTimeout);
          
          setTotalLatency(status.total_latency);
          
          if (status.last_update) {
            const updateTime = new Date(status.last_update);
            setLastUpdate(updateTime.toLocaleTimeString());
          }
        } else {
          // No new activity - just update latencies without animation
          setStages(prev => prev.map((stage) => {
            const backendName = Object.keys(stageMap).find(
              key => stageMap[key] === stage.name
            );
            const latency = backendName ? (status.stages[backendName] || 0) : 0;
            
            return {
              ...stage,
              latency,
              // Only change status if it's currently idle (don't interrupt animations)
              status: stage.status === 'idle' ? 'idle' as const : stage.status,
            };
          }));
          setTotalLatency(status.total_latency);
          
          // Update last update time even if not animating (for display)
          if (status.last_update) {
            const updateTime = new Date(status.last_update);
            setLastUpdate(updateTime.toLocaleTimeString());
          }
        }
      } catch (error) {
        console.error('Failed to fetch pipeline status:', error);
      }
    };

    fetchPipelineStatus();
    const interval = setInterval(fetchPipelineStatus, 2000); // Poll every 2 seconds

    return () => {
      clearInterval(interval);
      timeouts.forEach(t => clearTimeout(t));
    };
  }, []); // Empty dependency array - use refs instead

  return (
    <div className="panel pipeline-panel">
      <div className="panel-header">
        <div>
          <h2 className="panel-title">Real-Time Update Pipeline</h2>
          <p className="panel-description">
            <strong>Watch documents flow through the system:</strong> When you create or update a document, it automatically processes through 6 stages from database to vector store. Each stage lights up as it processes, showing how fast your changes become searchable. The entire pipeline completes in under 1 second.
          </p>
        </div>
      </div>

      <div className="pipeline">
        {stages.map((stage, index) => {
          const IconComponent = stage.Icon;
          const statusClass = stage.status === 'active' ? 'active' : stage.status === 'complete' ? 'complete' : '';
          return (
            <div key={stage.name} className={`pipeline-stage ${statusClass}`} style={{ opacity: stage.status === 'idle' ? 0.5 : 1 }}>
              <div className={`stage-icon ${statusClass}`}>
                <IconComponent size={20} />
              </div>
              <div className="stage-info">
                <div className="stage-name">{stage.name}</div>
                <div className="stage-latency">
                  {stage.latency > 0 ? `${stage.latency.toFixed(2)}s` : '—'}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      <div style={{ marginTop: '1.5rem', padding: '1rem', background: 'var(--bg-secondary)', borderRadius: '6px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <div className="metric" style={{ borderBottom: 'none', padding: '0' }}>
            <span className="metric-label">End-to-End Latency</span>
            <span className="metric-value" style={{ color: totalLatency < 1 ? 'var(--success)' : 'var(--warning)' }}>
              {totalLatency > 0 ? `${totalLatency.toFixed(2)}s` : '—'}
            </span>
          </div>
          {lastUpdate && (
            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
              Last processed: {lastUpdate}
            </div>
          )}
        </div>
        <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', textAlign: 'right' }}>
          <div style={{ marginBottom: '0.25rem' }}>Target: &lt;1s</div>
          <div style={{ color: totalLatency < 1 ? 'var(--success)' : 'var(--warning)' }}>
            {totalLatency > 0 ? (totalLatency < 1 ? '✓ Meeting target' : '⚠ Above target') : 'No recent activity'}
          </div>
        </div>
      </div>
    </div>
  );
}

