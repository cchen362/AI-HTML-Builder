import React, { useState, useEffect, useCallback } from 'react';
import { adminApi } from '../../services/api';

interface CostDashboardProps {
  isOpen: boolean;
}

interface CostSummary {
  total_requests: number | null;
  total_input_tokens: number | null;
  total_output_tokens: number | null;
  total_images: number | null;
  total_cost_usd: number | null;
}

interface ModelCost {
  model: string;
  total_requests: number;
  total_input_tokens: number;
  total_output_tokens: number;
  total_images: number;
  total_cost_usd: number;
}

const MODEL_LABELS: Record<string, string> = {
  'claude-sonnet-4-6': 'Claude Sonnet 4.6',
  'claude-sonnet-4-5-20250929': 'Claude Sonnet 4.5',
  'gemini-2.5-pro': 'Gemini 2.5 Pro',
  'gemini-3-pro-image-preview': 'Nano Banana Pro',
  'gemini-2.5-flash-image': 'Gemini Flash Image',
  'claude-haiku-4-5-20251001': 'Claude Haiku 4.5',
};

function formatCost(usd: number | null | undefined): string {
  if (usd == null || usd === 0) return '$0.00';
  if (usd < 0.01) return `$${usd.toFixed(4)}`;
  return `$${usd.toFixed(2)}`;
}

function formatTokens(count: number | null | undefined): string {
  if (count == null) return '0';
  if (count < 1_000) return count.toString();
  if (count < 1_000_000) return `${(count / 1_000).toFixed(1)}k`;
  return `${(count / 1_000_000).toFixed(1)}M`;
}

function formatNumber(n: number | null | undefined): string {
  if (n == null) return '0';
  return n.toLocaleString();
}

const CostDashboard: React.FC<CostDashboardProps> = ({ isOpen }) => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [summary, setSummary] = useState<CostSummary | null>(null);
  const [byModel, setByModel] = useState<ModelCost[]>([]);
  const [todayTotal, setTodayTotal] = useState(0);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [costsRes, todayRes] = await Promise.all([
        adminApi.getCosts(30),
        adminApi.getTodayCosts(),
      ]);
      setSummary(costsRes.summary);
      setByModel(costsRes.by_model);
      setTodayTotal(
        todayRes.costs.reduce((sum, c) => sum + c.estimated_cost_usd, 0),
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load cost data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (isOpen) loadData();
  }, [isOpen, loadData]);

  if (loading) {
    return (
      <div className="admin-section" style={{ textAlign: 'center', color: 'var(--text-tertiary)' }}>
        Loading...
      </div>
    );
  }

  if (error) {
    return (
      <div className="admin-section">
        <div className="auth-error" style={{ margin: 0 }}>{error}</div>
      </div>
    );
  }

  return (
    <>
      <div className="cost-summary-cards">
        <div className="cost-card cost-card--today">
          <span className="cost-card-label">Today</span>
          <span className="cost-card-value">{formatCost(todayTotal)}</span>
        </div>
        <div className="cost-card">
          <span className="cost-card-label">30-Day Total</span>
          <span className="cost-card-value">{formatCost(summary?.total_cost_usd)}</span>
        </div>
        <div className="cost-card">
          <span className="cost-card-label">Requests</span>
          <span className="cost-card-value">{formatNumber(summary?.total_requests)}</span>
        </div>
      </div>

      <div className="cost-table-header">
        <h3 className="admin-section-title">By Model (30 Days)</h3>
        <button type="button" className="admin-btn" onClick={loadData} disabled={loading}>
          Refresh
        </button>
      </div>

      {byModel.length === 0 ? (
        <div className="cost-empty">No usage recorded in the last 30 days.</div>
      ) : (
        <div className="cost-table-wrapper">
          <table className="cost-table">
            <thead>
              <tr>
                <th>Model</th>
                <th>Requests</th>
                <th>Input</th>
                <th>Output</th>
                <th>Images</th>
                <th>Cost</th>
              </tr>
            </thead>
            <tbody>
              {byModel.map((m) => (
                <tr key={m.model}>
                  <td className="cost-model-name">{MODEL_LABELS[m.model] ?? m.model}</td>
                  <td>{formatNumber(m.total_requests)}</td>
                  <td>{formatTokens(m.total_input_tokens)}</td>
                  <td>{formatTokens(m.total_output_tokens)}</td>
                  <td>{formatNumber(m.total_images)}</td>
                  <td className="cost-amount">{formatCost(m.total_cost_usd)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
};

export default CostDashboard;
