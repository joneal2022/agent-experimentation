import React, { useState, useEffect } from 'react';
import { ChartBarIcon, TrendingUpIcon, ExclamationTriangleIcon } from '@heroicons/react/24/outline';
import { BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import toast from 'react-hot-toast';

import api from '../services/api';
import KPICard from '../components/KPICard';

const Analytics: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [businessMetrics, setBusinessMetrics] = useState<any>(null);
  const [clientImpact, setClientImpact] = useState<any>(null);
  const [teamPerformance, setTeamPerformance] = useState<any>(null);

  useEffect(() => {
    loadAnalyticsData();
  }, []);

  const loadAnalyticsData = async () => {
    try {
      setLoading(true);
      const [metricsResponse, clientResponse, teamResponse] = await Promise.all([
        api.get('/api/analytics/business-metrics'),
        api.get('/api/analytics/client-impact'),
        api.get('/api/analytics/team-performance'),
      ]);

      setBusinessMetrics(metricsResponse.data);
      setClientImpact(clientResponse.data);
      setTeamPerformance(teamResponse.data);
    } catch (error) {
      console.error('Failed to load analytics:', error);
      toast.error('Failed to load analytics data');
    } finally {
      setLoading(false);
    }
  };

  const COLORS = ['#ef4444', '#f59e0b', '#22c55e', '#3b82f6', '#8b5cf6'];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">Business Analytics</h1>
        <button
          onClick={loadAnalyticsData}
          disabled={loading}
          className="btn btn-primary disabled:opacity-50"
        >
          {loading ? 'Loading...' : 'Refresh'}
        </button>
      </div>

      {/* Business Metrics KPIs */}
      {businessMetrics && (
        <>
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
            <KPICard
              title="Delivery Risk Score"
              value={`${businessMetrics.delivery_metrics.delivery_risk_score}/10`}
              subtitle="Overall delivery risk"
              icon={ExclamationTriangleIcon}
              color={businessMetrics.delivery_metrics.delivery_risk_score <= 3 ? 'green' : 
                    businessMetrics.delivery_metrics.delivery_risk_score <= 6 ? 'yellow' : 'red'}
              loading={loading}
            />
            
            <KPICard
              title="Quality Risk Score"
              value={`${businessMetrics.quality_metrics.quality_risk_score}/10`}
              subtitle="Deployment & testing"
              icon={ChartBarIcon}
              color={businessMetrics.quality_metrics.quality_risk_score <= 3 ? 'green' : 
                    businessMetrics.quality_metrics.quality_risk_score <= 6 ? 'yellow' : 'red'}
              loading={loading}
            />

            <KPICard
              title="Utilization Score"
              value={`${businessMetrics.resource_metrics.utilization_score}/10`}
              subtitle="Team efficiency"
              icon={TrendingUpIcon}
              color={businessMetrics.resource_metrics.utilization_score >= 8 ? 'green' : 
                    businessMetrics.resource_metrics.utilization_score >= 6 ? 'yellow' : 'red'}
              loading={loading}
            />

            <KPICard
              title="At-Risk Clients"
              value={clientImpact?.high_risk_clients || 0}
              subtitle="Need attention"
              icon={ExclamationTriangleIcon}
              color={clientImpact?.high_risk_clients === 0 ? 'green' : 'red'}
              loading={loading}
            />
          </div>

          {/* Charts */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Resource Distribution */}
            <div className="card">
              <div className="card-header">
                <h3 className="text-lg font-semibold text-gray-900">Stalled Tickets by Project</h3>
              </div>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={Object.entries(businessMetrics.resource_metrics.project_distribution).map(([key, value]) => ({ project: key, count: value }))}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="project" tick={{ fontSize: 12 }} />
                    <YAxis tick={{ fontSize: 12 }} />
                    <Tooltip />
                    <Bar dataKey="count" fill="#3b82f6" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Team Performance */}
            <div className="card">
              <div className="card-header">
                <h3 className="text-lg font-semibold text-gray-900">Team Performance Scores</h3>
              </div>
              <div className="h-64">
                {teamPerformance && (
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={teamPerformance.team_performance.slice(0, 8)}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="team_member" tick={{ fontSize: 10 }} angle={-45} textAnchor="end" />
                      <YAxis tick={{ fontSize: 12 }} />
                      <Tooltip />
                      <Bar dataKey="performance_score" fill="#22c55e" />
                    </BarChart>
                  </ResponsiveContainer>
                )}
              </div>
            </div>
          </div>
        </>
      )}

      {/* Client Impact Analysis */}
      {clientImpact && (
        <div className="card">
          <div className="card-header">
            <h3 className="text-lg font-semibold text-gray-900">Client Impact Analysis</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Client
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Overdue Tickets
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Failed Deployments
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Overall Risk
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {clientImpact.clients.slice(0, 10).map((client: any, index: number) => (
                  <tr key={index} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                      {client.client_name}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {client.overdue_tickets || 0}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {client.failed_deployments || 0}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                        client.overall_risk === 'low' ? 'bg-green-100 text-green-800' :
                        client.overall_risk === 'medium' ? 'bg-yellow-100 text-yellow-800' :
                        'bg-red-100 text-red-800'
                      }`}>
                        {client.overall_risk}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Team Performance Details */}
      {teamPerformance && (
        <div className="card">
          <div className="card-header">
            <h3 className="text-lg font-semibold text-gray-900">Team Performance Details</h3>
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
            <div className="text-center">
              <div className="text-2xl font-bold text-gray-900">{teamPerformance.team_members_analyzed}</div>
              <div className="text-sm text-gray-500">Team Members</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-red-600">{teamPerformance.summary.members_needing_support}</div>
              <div className="text-sm text-gray-500">Need Support</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-blue-600">{teamPerformance.summary.average_performance_score.toFixed(1)}</div>
              <div className="text-sm text-gray-500">Avg Performance</div>
            </div>
          </div>

          {teamPerformance.recommendations && (
            <div className="bg-blue-50 border border-blue-200 rounded-md p-4">
              <h4 className="text-sm font-medium text-blue-900 mb-2">Recommendations:</h4>
              <ul className="text-sm text-blue-800 space-y-1">
                {teamPerformance.recommendations.map((rec: string, index: number) => (
                  <li key={index}>• {rec}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default Analytics;