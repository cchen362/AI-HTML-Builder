import React, { useState, useEffect } from 'react';
import './AdminDashboard.css';

interface Session {
  session_id: string;
  created_at: string;
  last_activity: string;
  duration_minutes: number;
  iterations: number;
  success_rate: number;
  total_tokens: number;
  avg_response_time: number;
  output_types: string[];
  final_output?: string;
}

interface DashboardOverview {
  overview: {
    total_sessions: number;
    sessions_last_24h: number;
    active_sessions_last_hour: number;
    avg_response_time_ms: number;
    total_tokens_7d: number;
    success_rate: number;
    avg_iterations_per_session: number;
  };
  recent_activity: Session[];
  popular_outputs: Array<{
    type: string;
    count: number;
    percentage: number;
  }>;
  stats_7d: {
    total_iterations: number;
    avg_session_duration: number;
    peak_hours: number[];
  };
}

interface AdminDashboardProps {
  onLogout: () => void;
}

const AdminDashboard: React.FC<AdminDashboardProps> = ({ onLogout }) => {
  const [overview, setOverview] = useState<DashboardOverview | null>(null);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [selectedSession, setSelectedSession] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'sessions' | 'export'>('overview');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    setLoading(true);
    setError('');

    try {
      // Load overview data
      const overviewResponse = await fetch('/api/admin/overview', {
        credentials: 'include'
      });

      if (!overviewResponse.ok) {
        if (overviewResponse.status === 401) {
          onLogout();
          return;
        }
        throw new Error('Failed to load dashboard data');
      }

      const overviewData = await overviewResponse.json();
      setOverview(overviewData);

      // Load sessions list
      const sessionsResponse = await fetch('/api/admin/sessions?limit=20', {
        credentials: 'include'
      });

      if (sessionsResponse.ok) {
        const sessionsData = await sessionsResponse.json();
        setSessions(sessionsData.sessions || []);
      }

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load dashboard');
    } finally {
      setLoading(false);
    }
  };

  const handleExportCSV = async (type: 'events' | 'sessions', days: number = 7) => {
    try {
      const endDate = new Date().toISOString().split('T')[0];
      const startDate = new Date(Date.now() - (days * 24 * 60 * 60 * 1000)).toISOString().split('T')[0];
      
      const url = type === 'events' 
        ? `/api/admin/csv?start_date=${startDate}&end_date=${endDate}`
        : `/api/admin/session-summary-csv?start_date=${startDate}&end_date=${endDate}`;

      const response = await fetch(url, {
        credentials: 'include'
      });

      if (!response.ok) {
        throw new Error('Export failed');
      }

      // Download the file
      const blob = await response.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = `ai_html_builder_${type}_${days}d.csv`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(downloadUrl);

    } catch (err) {
      setError(`Export failed: ${err instanceof Error ? err.message : 'Unknown error'}`);
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString();
  };

  const formatDuration = (minutes: number) => {
    if (minutes < 60) {
      return `${Math.round(minutes)}m`;
    }
    const hours = Math.floor(minutes / 60);
    const mins = Math.round(minutes % 60);
    return `${hours}h ${mins}m`;
  };

  const formatOutputTypes = (types: string[]) => {
    return types.map(type => 
      type.replace(/-/g, ' ')
         .replace(/\b\w/g, l => l.toUpperCase())
    ).join(', ');
  };

  if (loading) {
    return (
      <div className="admin-dashboard">
        <div className="loading-container">
          <div className="loading-spinner">🔄</div>
          <p>Loading dashboard...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="admin-dashboard">
      {/* Header */}
      <div className="dashboard-header">
        <div className="header-content">
          <h1>📊 Analytics Dashboard</h1>
          <p>AI HTML Builder - Admin Panel</p>
        </div>
        <div className="header-actions">
          <button onClick={loadDashboardData} className="refresh-button">
            🔄 Refresh
          </button>
          <button onClick={onLogout} className="logout-button">
            🚪 Logout
          </button>
        </div>
      </div>

      {error && (
        <div className="error-banner">
          ❌ {error}
        </div>
      )}

      {/* Navigation Tabs */}
      <div className="dashboard-tabs">
        <button 
          className={`tab ${activeTab === 'overview' ? 'active' : ''}`}
          onClick={() => setActiveTab('overview')}
        >
          📈 Overview
        </button>
        <button 
          className={`tab ${activeTab === 'sessions' ? 'active' : ''}`}
          onClick={() => setActiveTab('sessions')}
        >
          💬 Sessions
        </button>
        <button 
          className={`tab ${activeTab === 'export' ? 'active' : ''}`}
          onClick={() => setActiveTab('export')}
        >
          📋 Export
        </button>
      </div>

      {/* Content Area */}
      <div className="dashboard-content">
        {activeTab === 'overview' && overview && (
          <div className="overview-tab">
            {/* Key Metrics */}
            <div className="metrics-grid">
              <div className="metric-card">
                <h3>Total Sessions</h3>
                <div className="metric-value">{overview.overview.total_sessions}</div>
                <div className="metric-subtitle">All time</div>
              </div>
              <div className="metric-card">
                <h3>Active Today</h3>
                <div className="metric-value">{overview.overview.sessions_last_24h}</div>
                <div className="metric-subtitle">Last 24 hours</div>
              </div>
              <div className="metric-card">
                <h3>Avg Response Time</h3>
                <div className="metric-value">{(overview.overview.avg_response_time_ms / 1000).toFixed(1)}s</div>
                <div className="metric-subtitle">Claude API + Processing</div>
              </div>
              <div className="metric-card">
                <h3>Success Rate</h3>
                <div className="metric-value">{overview.overview.success_rate.toFixed(1)}%</div>
                <div className="metric-subtitle">Last 7 days</div>
              </div>
              <div className="metric-card">
                <h3>Total Tokens</h3>
                <div className="metric-value">{overview.overview.total_tokens_7d.toLocaleString()}</div>
                <div className="metric-subtitle">Last 7 days</div>
              </div>
              <div className="metric-card">
                <h3>Avg Iterations</h3>
                <div className="metric-value">{overview.overview.avg_iterations_per_session.toFixed(1)}</div>
                <div className="metric-subtitle">Per session</div>
              </div>
            </div>

            {/* Popular Output Types */}
            <div className="section">
              <h2>🎨 Popular Output Types</h2>
              <div className="output-types-grid">
                {overview.popular_outputs.map((output, index) => (
                  <div key={index} className="output-type-card">
                    <div className="output-type-name">
                      {output.type.replace(/-/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                    </div>
                    <div className="output-type-stats">
                      <span className="count">{output.count}</span>
                      <span className="percentage">({output.percentage}%)</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Recent Activity */}
            <div className="section">
              <h2>⏰ Recent Activity</h2>
              <div className="recent-activity">
                {overview.recent_activity.map((session) => (
                  <div key={session.session_id} className="activity-item">
                    <div className="activity-info">
                      <div className="session-id">{session.session_id.substring(0, 8)}...</div>
                      <div className="session-stats">
                        {session.iterations} iterations • {session.total_tokens} tokens • {formatDuration(session.duration_minutes)}
                      </div>
                    </div>
                    <div className="activity-meta">
                      <div className="final-output">
                        {session.final_output?.replace(/-/g, ' ').replace(/\b\w/g, l => l.toUpperCase()) || 'Custom'}
                      </div>
                      <div className="activity-time">{formatDate(session.last_activity)}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {activeTab === 'sessions' && (
          <div className="sessions-tab">
            <div className="section">
              <h2>💬 All Sessions</h2>
              <div className="sessions-table">
                <div className="table-header">
                  <div>Session ID</div>
                  <div>Created</div>
                  <div>Duration</div>
                  <div>Iterations</div>
                  <div>Tokens</div>
                  <div>Success Rate</div>
                  <div>Output Type</div>
                </div>
                {sessions.map((session) => (
                  <div key={session.session_id} className="table-row">
                    <div className="session-id-cell">
                      {session.session_id.substring(0, 12)}...
                    </div>
                    <div>{formatDate(session.created_at)}</div>
                    <div>{formatDuration(session.duration_minutes)}</div>
                    <div>{session.iterations}</div>
                    <div>{session.total_tokens.toLocaleString()}</div>
                    <div className={`success-rate ${session.success_rate >= 90 ? 'high' : session.success_rate >= 70 ? 'medium' : 'low'}`}>
                      {session.success_rate.toFixed(0)}%
                    </div>
                    <div>{session.final_output?.replace(/-/g, ' ').replace(/\b\w/g, l => l.toUpperCase()) || 'Custom'}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {activeTab === 'export' && (
          <div className="export-tab">
            <div className="section">
              <h2>📋 Data Export</h2>
              <p>Export analytics data to CSV for further analysis.</p>
              
              <div className="export-options">
                <div className="export-card">
                  <h3>📊 Detailed Analytics Events</h3>
                  <p>Complete event-by-event data including response times, token usage, and output classifications.</p>
                  <div className="export-buttons">
                    <button onClick={() => handleExportCSV('events', 1)} className="export-button">
                      📅 Last 1 Day
                    </button>
                    <button onClick={() => handleExportCSV('events', 7)} className="export-button">
                      📅 Last 7 Days
                    </button>
                    <button onClick={() => handleExportCSV('events', 30)} className="export-button">
                      📅 Last 30 Days
                    </button>
                  </div>
                </div>

                <div className="export-card">
                  <h3>📋 Session Summaries</h3>
                  <p>High-level session statistics and performance metrics.</p>
                  <div className="export-buttons">
                    <button onClick={() => handleExportCSV('sessions', 1)} className="export-button">
                      📅 Last 1 Day
                    </button>
                    <button onClick={() => handleExportCSV('sessions', 7)} className="export-button">
                      📅 Last 7 Days
                    </button>
                    <button onClick={() => handleExportCSV('sessions', 30)} className="export-button">
                      📅 Last 30 Days
                    </button>
                  </div>
                </div>
              </div>

              <div className="export-info">
                <h4>💡 Export Information</h4>
                <ul>
                  <li><strong>Analytics Events:</strong> Individual chat interactions with timing, tokens, and classifications</li>
                  <li><strong>Session Summaries:</strong> Aggregated metrics per session including success rates and performance</li>
                  <li><strong>Format:</strong> CSV files compatible with Excel, Google Sheets, and data analysis tools</li>
                  <li><strong>Data Retention:</strong> Analytics data is stored for 7 days by default</li>
                </ul>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default AdminDashboard;