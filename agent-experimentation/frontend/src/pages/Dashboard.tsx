import React, { useState, useEffect } from 'react';
import {
  TicketIcon,
  ExclamationTriangleIcon,
  ClockIcon,
  RocketLaunchIcon,
  BellAlertIcon,
  UserGroupIcon,
  ChartBarIcon,
  TrophyIcon,
} from '@heroicons/react/24/outline';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar } from 'recharts';
import toast from 'react-hot-toast';

import KPICard from '../components/KPICard';
import AlertBanner from '../components/AlertBanner';
import { dashboardService, DashboardSummary } from '../services/dashboardService';
import { alertsService } from '../services/alertsService';

const Dashboard: React.FC = () => {
  const [dashboardData, setDashboardData] = useState<DashboardSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());
  const [criticalAlerts, setCriticalAlerts] = useState(0);

  useEffect(() => {
    loadDashboardData();
    loadCriticalAlerts();
    
    // Auto-refresh every 5 minutes
    const interval = setInterval(() => {
      loadDashboardData();
      loadCriticalAlerts();
    }, 5 * 60 * 1000);

    return () => clearInterval(interval);
  }, []);

  const loadDashboardData = async (retryCount = 0) => {
    try {
      console.log('Loading dashboard data...');
      const data = await dashboardService.getExecutiveSummary();
      setDashboardData(data);
      setLastRefresh(new Date());
      console.log('Dashboard data loaded successfully');
    } catch (error) {
      console.error('Failed to load dashboard data:', error);
      
      // Retry up to 2 times with increasing delays
      if (retryCount < 2) {
        const delay = (retryCount + 1) * 5000; // 5s, 10s delays
        console.log(`Retrying in ${delay/1000}s... (attempt ${retryCount + 1}/2)`);
        setTimeout(() => loadDashboardData(retryCount + 1), delay);
        return;
      }
      
      // Show error only after retries exhausted
      toast.error('Failed to load dashboard data. Please refresh the page.');
    } finally {
      if (retryCount === 0) {
        setLoading(false);
      }
    }
  };

  const loadCriticalAlerts = async () => {
    try {
      const summary = await alertsService.getAlertsSummary();
      setCriticalAlerts(summary.critical_alerts);
    } catch (error) {
      console.error('Failed to load alerts:', error);
    }
  };

  const handleRefresh = async () => {
    setLoading(true);
    toast.promise(
      dashboardService.refreshData().then(() => loadDashboardData()),
      {
        loading: 'Refreshing data...',
        success: 'Data refreshed successfully',
        error: 'Failed to refresh data',
      }
    );
  };

  if (loading && !dashboardData) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-3xl font-bold text-gray-900">Executive Dashboard</h1>
          <div className="loading-spinner"></div>
        </div>
        
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {[...Array(8)].map((_, i) => (
            <KPICard
              key={i}
              title=""
              value=""
              loading={true}
            />
          ))}
        </div>
      </div>
    );
  }

  const hasUrgentIssues = dashboardData && (
    dashboardData.urgent_items.critical_alerts > 0 ||
    dashboardData.urgent_items.failed_deployments > 0 ||
    dashboardData.urgent_items.overdue_tickets > 10
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Executive Dashboard</h1>
          <p className="text-gray-600 mt-1">
            Last updated: {lastRefresh.toLocaleTimeString()}
          </p>
        </div>
        <button
          onClick={handleRefresh}
          disabled={loading}
          className="btn btn-primary disabled:opacity-50"
        >
          {loading ? 'Refreshing...' : 'Refresh Data'}
        </button>
      </div>

      {/* Critical Alerts Banner */}
      {hasUrgentIssues && dashboardData && (
        <AlertBanner
          type="error"
          title="Critical Issues Require Immediate Attention"
          message={`${dashboardData.urgent_items.critical_alerts} critical alerts, ${dashboardData.urgent_items.failed_deployments} failed deployments, ${dashboardData.urgent_items.overdue_tickets} overdue tickets`}
          action={{
            label: 'View Alerts',
            onClick: () => window.location.href = '/alerts',
          }}
        />
      )}

      {/* KPI Cards */}
      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
        <KPICard
          title="Total Tickets"
          value={dashboardData?.kpis.total_tickets || 0}
          subtitle="Active tickets"
          icon={TicketIcon}
          color="blue"
          loading={loading}
        />
        
        <KPICard
          title="Stalled Tickets"
          value={dashboardData?.kpis.stalled_tickets || 0}
          subtitle=">5 days no activity"
          icon={ClockIcon}
          color={dashboardData && dashboardData.kpis.stalled_tickets > 10 ? 'red' : 'yellow'}
          loading={loading}
        />
        
        <KPICard
          title="Overdue Work"
          value={dashboardData?.kpis.overdue_tickets || 0}
          subtitle="Past due date"
          icon={ExclamationTriangleIcon}
          color={dashboardData && dashboardData.kpis.overdue_tickets > 5 ? 'red' : 'yellow'}
          loading={loading}
        />
        
        <KPICard
          title="Failed Deployments"
          value={dashboardData?.kpis.failed_deployments || 0}
          subtitle="Last 30 days"
          icon={RocketLaunchIcon}
          color={dashboardData && dashboardData.kpis.failed_deployments > 0 ? 'red' : 'green'}
          loading={loading}
        />
        
        <KPICard
          title="Critical Alerts"
          value={criticalAlerts}
          subtitle="Requires attention"
          icon={BellAlertIcon}
          color={criticalAlerts > 0 ? 'red' : 'green'}
          loading={loading}
        />
        
        <KPICard
          title="Client Satisfaction"
          value={`${dashboardData?.kpis.client_satisfaction_score || 0}/10`}
          subtitle="Avg. rating"
          icon={TrophyIcon}
          color={dashboardData && dashboardData.kpis.client_satisfaction_score >= 8 ? 'green' : 
                dashboardData && dashboardData.kpis.client_satisfaction_score >= 6 ? 'yellow' : 'red'}
          loading={loading}
        />
        
        <KPICard
          title="Delivery Risk"
          value={`${dashboardData?.kpis.delivery_risk_score || 0}/10`}
          subtitle="Risk assessment"
          icon={ChartBarIcon}
          color={dashboardData && dashboardData.kpis.delivery_risk_score <= 3 ? 'green' : 
                dashboardData && dashboardData.kpis.delivery_risk_score <= 6 ? 'yellow' : 'red'}
          loading={loading}
        />
        
        <KPICard
          title="Team Utilization"
          value={`${dashboardData?.kpis.team_utilization || 0}%`}
          subtitle="Capacity usage"
          icon={UserGroupIcon}
          color={dashboardData && dashboardData.kpis.team_utilization >= 80 && dashboardData.kpis.team_utilization <= 110 ? 'green' : 'yellow'}
          loading={loading}
        />
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Trends Chart */}
        <div className="card">
          <div className="card-header">
            <h3 className="text-lg font-semibold text-gray-900">Ticket Trends (30 Days)</h3>
          </div>
          <div className="h-64">
            {dashboardData?.trends && (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={dashboardData.trends}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis 
                    dataKey="date" 
                    tick={{ fontSize: 12 }}
                    tickFormatter={(value) => new Date(value).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                  />
                  <YAxis tick={{ fontSize: 12 }} />
                  <Tooltip 
                    labelFormatter={(value) => new Date(value).toLocaleDateString()}
                  />
                  <Line 
                    type="monotone" 
                    dataKey="tickets_created" 
                    stroke="#3b82f6" 
                    strokeWidth={2}
                    name="Created"
                  />
                  <Line 
                    type="monotone" 
                    dataKey="tickets_resolved" 
                    stroke="#22c55e" 
                    strokeWidth={2}
                    name="Resolved"
                  />
                  <Line 
                    type="monotone" 
                    dataKey="stalled_count" 
                    stroke="#f59e0b" 
                    strokeWidth={2}
                    name="Stalled"
                  />
                </LineChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        {/* Project Health */}
        <div className="card">
          <div className="card-header">
            <h3 className="text-lg font-semibold text-gray-900">Project Health</h3>
          </div>
          <div className="h-64">
            {dashboardData?.project_health && (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={dashboardData.project_health.slice(0, 8)}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis 
                    dataKey="project_key" 
                    tick={{ fontSize: 12 }}
                  />
                  <YAxis tick={{ fontSize: 12 }} />
                  <Tooltip />
                  <Bar dataKey="health_score" fill="#3b82f6" name="Health Score" />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>
      </div>

      {/* Project Health Table */}
      <div className="card">
        <div className="card-header">
          <h3 className="text-lg font-semibold text-gray-900">Project Status Overview</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Project
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Health Score
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Stalled
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Overdue
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Risk Level
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {dashboardData?.project_health.map((project) => (
                <tr key={project.project_key} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div>
                      <div className="text-sm font-medium text-gray-900">
                        {project.project_key}
                      </div>
                      <div className="text-sm text-gray-500">
                        {project.project_name}
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center">
                      <span className="text-sm font-medium text-gray-900">
                        {project.health_score}/10
                      </span>
                      <div className={`ml-2 w-3 h-3 rounded-full ${
                        project.health_score >= 8 ? 'bg-green-500' :
                        project.health_score >= 6 ? 'bg-yellow-500' : 'bg-red-500'
                      }`}></div>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {project.stalled_tickets}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {project.overdue_tickets}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                      project.risk_level === 'low' ? 'bg-green-100 text-green-800' :
                      project.risk_level === 'medium' ? 'bg-yellow-100 text-yellow-800' :
                      'bg-red-100 text-red-800'
                    }`}>
                      {project.risk_level}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;