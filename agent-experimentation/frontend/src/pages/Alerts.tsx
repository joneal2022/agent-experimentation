import React, { useState, useEffect } from 'react';
import {
  ExclamationTriangleIcon,
  CheckCircleIcon,
  ClockIcon,
  BellIcon,
} from '@heroicons/react/24/outline';
import toast from 'react-hot-toast';
import classNames from 'classnames';

import { alertsService, Alert, AlertsResponse } from '../services/alertsService';
import KPICard from '../components/KPICard';

const Alerts: React.FC = () => {
  const [alerts, setAlerts] = useState<AlertsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({
    severity: '',
    status: '',
    alert_type: '',
    days_back: 7,
  });
  const [selectedAlert, setSelectedAlert] = useState<Alert | null>(null);

  useEffect(() => {
    loadAlerts();
  }, [filters]);

  const loadAlerts = async () => {
    try {
      setLoading(true);
      const data = await alertsService.getAlerts(filters);
      setAlerts(data);
    } catch (error) {
      console.error('Failed to load alerts:', error);
      toast.error('Failed to load alerts');
    } finally {
      setLoading(false);
    }
  };

  const handleAcknowledgeAlert = async (alertId: string) => {
    try {
      await alertsService.acknowledgeAlert(alertId, 'CEO'); // In real app, get from auth context
      toast.success('Alert acknowledged');
      loadAlerts();
    } catch (error) {
      console.error('Failed to acknowledge alert:', error);
      toast.error('Failed to acknowledge alert');
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical': return 'text-red-600 bg-red-100';
      case 'high': return 'text-orange-600 bg-orange-100';
      case 'medium': return 'text-yellow-600 bg-yellow-100';
      case 'low': return 'text-blue-600 bg-blue-100';
      default: return 'text-gray-600 bg-gray-100';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active': return 'text-red-600 bg-red-100';
      case 'acknowledged': return 'text-yellow-600 bg-yellow-100';
      case 'resolved': return 'text-green-600 bg-green-100';
      default: return 'text-gray-600 bg-gray-100';
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">Alerts & Notifications</h1>
        <button
          onClick={loadAlerts}
          disabled={loading}
          className="btn btn-primary disabled:opacity-50"
        >
          {loading ? 'Refreshing...' : 'Refresh'}
        </button>
      </div>

      {/* Summary KPIs */}
      {alerts && (
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
          <KPICard
            title="Total Alerts"
            value={alerts.summary.total_alerts}
            subtitle={`Last ${filters.days_back} days`}
            icon={BellIcon}
            color="blue"
          />
          
          <KPICard
            title="Critical Alerts"
            value={alerts.summary.critical_alerts}
            subtitle="Require immediate attention"
            icon={ExclamationTriangleIcon}
            color={alerts.summary.critical_alerts > 0 ? 'red' : 'green'}
          />
          
          <KPICard
            title="Unresolved"
            value={alerts.summary.unresolved_alerts}
            subtitle="Active alerts"
            icon={ClockIcon}
            color={alerts.summary.unresolved_alerts > 5 ? 'red' : 'yellow'}
          />
          
          <KPICard
            title="Resolution Rate"
            value={`${Math.round(alerts.summary.resolution_rate)}%`}
            subtitle="Successfully resolved"
            icon={CheckCircleIcon}
            color={alerts.summary.resolution_rate >= 90 ? 'green' : 
                  alerts.summary.resolution_rate >= 70 ? 'yellow' : 'red'}
          />
        </div>
      )}

      {/* Filters */}
      <div className="card">
        <div className="card-header">
          <h3 className="text-lg font-semibold text-gray-900">Filters</h3>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Severity
            </label>
            <select
              value={filters.severity}
              onChange={(e) => setFilters({ ...filters, severity: e.target.value })}
              className="w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500"
            >
              <option value="">All Severities</option>
              <option value="critical">Critical</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
              <option value="info">Info</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Status
            </label>
            <select
              value={filters.status}
              onChange={(e) => setFilters({ ...filters, status: e.target.value })}
              className="w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500"
            >
              <option value="">All Statuses</option>
              <option value="active">Active</option>
              <option value="acknowledged">Acknowledged</option>
              <option value="resolved">Resolved</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Days Back
            </label>
            <select
              value={filters.days_back}
              onChange={(e) => setFilters({ ...filters, days_back: parseInt(e.target.value) })}
              className="w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500"
            >
              <option value={1}>Last 24 hours</option>
              <option value={7}>Last 7 days</option>
              <option value={30}>Last 30 days</option>
              <option value={90}>Last 90 days</option>
            </select>
          </div>

          <div className="flex items-end">
            <button
              onClick={() => setFilters({ severity: '', status: '', alert_type: '', days_back: 7 })}
              className="btn btn-secondary w-full"
            >
              Clear Filters
            </button>
          </div>
        </div>
      </div>

      {/* Alerts List */}
      <div className="card">
        <div className="card-header">
          <h3 className="text-lg font-semibold text-gray-900">
            Active Alerts ({alerts?.alerts.length || 0})
          </h3>
        </div>
        
        {loading ? (
          <div className="flex justify-center py-12">
            <div className="loading-spinner"></div>
          </div>
        ) : alerts && alerts.alerts.length > 0 ? (
          <div className="space-y-4">
            {alerts.alerts.map((alert) => (
              <div
                key={alert.id}
                className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow cursor-pointer"
                onClick={() => setSelectedAlert(alert)}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center space-x-3 mb-2">
                      <span className={classNames(
                        'inline-flex px-2 py-1 text-xs font-semibold rounded-full',
                        getSeverityColor(alert.severity)
                      )}>
                        {alert.severity.toUpperCase()}
                      </span>
                      
                      <span className={classNames(
                        'inline-flex px-2 py-1 text-xs font-semibold rounded-full',
                        getStatusColor(alert.status)
                      )}>
                        {alert.status.toUpperCase()}
                      </span>

                      {alert.jira_ticket_key && (
                        <span className="text-xs text-gray-500">
                          {alert.jira_ticket_key}
                        </span>
                      )}
                    </div>

                    <h4 className="text-lg font-medium text-gray-900 mb-2">
                      {alert.title}
                    </h4>
                    
                    <p className="text-gray-600 mb-2">
                      {alert.description}
                    </p>

                    {alert.recommendation && (
                      <div className="bg-blue-50 border border-blue-200 rounded-md p-3 mb-2">
                        <p className="text-sm text-blue-800">
                          <strong>Recommendation:</strong> {alert.recommendation}
                        </p>
                      </div>
                    )}

                    <div className="flex items-center justify-between text-sm text-gray-500">
                      <span>
                        Detected: {new Date(alert.first_detected).toLocaleString()}
                      </span>
                      {alert.client && (
                        <span>Client: {alert.client}</span>
                      )}
                    </div>
                  </div>

                  {alert.status === 'active' && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleAcknowledgeAlert(alert.id);
                      }}
                      className="ml-4 btn btn-primary text-sm"
                    >
                      Acknowledge
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-12">
            <BellIcon className="mx-auto h-12 w-12 text-gray-400" />
            <h3 className="mt-2 text-sm font-medium text-gray-900">No alerts</h3>
            <p className="mt-1 text-sm text-gray-500">
              No alerts found for the current filters.
            </p>
          </div>
        )}

        {/* Pagination */}
        {alerts && alerts.pagination.has_more && (
          <div className="mt-6 flex justify-center">
            <button className="btn btn-secondary">
              Load More
            </button>
          </div>
        )}
      </div>

      {/* Alert Details Modal */}
      {selectedAlert && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
          <div className="relative top-20 mx-auto p-5 border w-11/12 md:w-3/4 lg:w-1/2 shadow-lg rounded-md bg-white">
            <div className="mt-3">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-medium text-gray-900">
                  Alert Details
                </h3>
                <button
                  onClick={() => setSelectedAlert(null)}
                  className="text-gray-400 hover:text-gray-600"
                >
                  <span className="sr-only">Close</span>
                  ✕
                </button>
              </div>

              <div className="space-y-4">
                <div>
                  <h4 className="text-lg font-semibold">{selectedAlert.title}</h4>
                  <p className="text-gray-600 mt-1">{selectedAlert.description}</p>
                </div>

                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <strong>Severity:</strong>
                    <span className={classNames(
                      'ml-2 px-2 py-1 text-xs rounded-full',
                      getSeverityColor(selectedAlert.severity)
                    )}>
                      {selectedAlert.severity}
                    </span>
                  </div>
                  <div>
                    <strong>Status:</strong>
                    <span className={classNames(
                      'ml-2 px-2 py-1 text-xs rounded-full',
                      getStatusColor(selectedAlert.status)
                    )}>
                      {selectedAlert.status}
                    </span>
                  </div>
                  <div><strong>Type:</strong> {selectedAlert.alert_type}</div>
                  <div><strong>Client:</strong> {selectedAlert.client || 'N/A'}</div>
                  <div><strong>Project:</strong> {selectedAlert.project_key || 'N/A'}</div>
                  <div><strong>Assignee:</strong> {selectedAlert.assignee || 'N/A'}</div>
                </div>

                {selectedAlert.recommendation && (
                  <div className="bg-blue-50 border border-blue-200 rounded-md p-3">
                    <strong className="text-blue-900">Recommendation:</strong>
                    <p className="text-blue-800 mt-1">{selectedAlert.recommendation}</p>
                  </div>
                )}

                <div className="text-sm text-gray-500">
                  <div><strong>First Detected:</strong> {new Date(selectedAlert.first_detected).toLocaleString()}</div>
                  <div><strong>Last Updated:</strong> {new Date(selectedAlert.last_updated).toLocaleString()}</div>
                  {selectedAlert.acknowledged_at && (
                    <div><strong>Acknowledged:</strong> {new Date(selectedAlert.acknowledged_at).toLocaleString()} by {selectedAlert.acknowledged_by}</div>
                  )}
                </div>

                <div className="flex justify-end space-x-3 pt-4">
                  <button
                    onClick={() => setSelectedAlert(null)}
                    className="btn btn-secondary"
                  >
                    Close
                  </button>
                  {selectedAlert.status === 'active' && (
                    <button
                      onClick={() => {
                        handleAcknowledgeAlert(selectedAlert.id);
                        setSelectedAlert(null);
                      }}
                      className="btn btn-primary"
                    >
                      Acknowledge
                    </button>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Alerts;