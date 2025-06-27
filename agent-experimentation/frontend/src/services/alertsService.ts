import api from './api';

export interface Alert {
  id: string;
  alert_type: string;
  severity: 'critical' | 'high' | 'medium' | 'low' | 'info';
  status: 'active' | 'acknowledged' | 'resolved' | 'suppressed';
  title: string;
  description: string;
  recommendation?: string;
  jira_ticket_key?: string;
  project_key?: string;
  assignee?: string;
  client?: string;
  context_data?: any;
  first_detected: string;
  last_updated: string;
  acknowledged_at?: string;
  acknowledged_by?: string;
  resolved_at?: string;
  resolved_by?: string;
  auto_resolve: boolean;
}

export interface AlertsResponse {
  alerts: Alert[];
  pagination: {
    total_count: number;
    limit: number;
    offset: number;
    has_more: boolean;
  };
  summary: {
    total_alerts: number;
    critical_alerts: number;
    high_priority_alerts: number;
    unresolved_alerts: number;
    recent_alerts: number;
    resolution_rate: number;
  };
  filters_applied: {
    severity?: string;
    status?: string;
    alert_type?: string;
    days_back: number;
  };
}

export interface AlertsSummary {
  active_alerts: number;
  critical_alerts: number;
  alerts_last_24h: number;
  avg_resolution_time: number;
  top_alert_types: { [key: string]: number };
  by_severity: { [key: string]: number };
}

export const alertsService = {
  async getAlerts(params: {
    severity?: string;
    status?: string;
    alert_type?: string;
    days_back?: number;
    limit?: number;
    offset?: number;
  } = {}): Promise<AlertsResponse> {
    const response = await api.get('/api/alerts/', { params });
    return response.data;
  },

  async getActiveAlerts(): Promise<Alert[]> {
    const response = await api.get('/api/alerts/active');
    return response.data;
  },

  async getAlertsSummary(): Promise<AlertsSummary> {
    const response = await api.get('/api/alerts/summary');
    return response.data;
  },

  async getAlertDetails(alertId: string): Promise<Alert> {
    const response = await api.get(`/api/alerts/${alertId}`);
    return response.data;
  },

  async acknowledgeAlert(alertId: string, acknowledgedBy: string): Promise<void> {
    await api.post(`/api/alerts/${alertId}/acknowledge`, null, {
      params: { acknowledged_by: acknowledgedBy }
    });
  },

  async createAlert(alertData: {
    alert_type: string;
    severity: string;
    title: string;
    description: string;
    jira_ticket_key?: string;
    project_key?: string;
    assignee?: string;
    client?: string;
    recommendation?: string;
  }): Promise<{ alert_id: string }> {
    const response = await api.post('/api/alerts/create', null, {
      params: alertData
    });
    return response.data;
  },

  async getAlertStatistics(daysBack: number = 30): Promise<any> {
    const response = await api.get(`/api/alerts/statistics/overview?days_back=${daysBack}`);
    return response.data;
  },

  async testNotification(channel: string, recipient: string): Promise<void> {
    await api.post('/api/alerts/test-notification', null, {
      params: { channel, recipient }
    });
  },
};