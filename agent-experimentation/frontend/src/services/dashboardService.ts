import api from './api';

export interface DashboardKPIs {
  total_tickets: number;
  stalled_tickets: number;
  overdue_tickets: number;
  failed_deployments: number;
  critical_alerts: number;
  client_satisfaction_score: number;
  delivery_risk_score: number;
  team_utilization: number;
}

export interface ProjectHealth {
  project_key: string;
  project_name: string;
  health_score: number;
  stalled_tickets: number;
  overdue_tickets: number;
  recent_deployments: number;
  risk_level: 'low' | 'medium' | 'high';
}

export interface TrendData {
  date: string;
  tickets_created: number;
  tickets_resolved: number;
  stalled_count: number;
  overdue_count: number;
}

export interface DashboardSummary {
  kpis: DashboardKPIs;
  project_health: ProjectHealth[];
  trends: TrendData[];
  urgent_items: {
    critical_alerts: number;
    high_risk_projects: string[];
    overdue_tickets: number;
    failed_deployments: number;
  };
  timestamp: string;
}

export const dashboardService = {
  async getExecutiveSummary(): Promise<DashboardSummary> {
    const response = await api.get('/api/dashboard/executive-summary');
    return response.data;
  },

  async getKPIs(): Promise<DashboardKPIs> {
    const response = await api.get('/api/dashboard/kpis');
    return response.data;
  },

  async getProjectHealth(): Promise<ProjectHealth[]> {
    const response = await api.get('/api/dashboard/project-health');
    return response.data;
  },

  async getTrends(daysBack: number = 30): Promise<TrendData[]> {
    const response = await api.get(`/api/dashboard/trends?days_back=${daysBack}`);
    return response.data;
  },

  async refreshData(): Promise<void> {
    await api.post('/api/dashboard/refresh');
  },
};