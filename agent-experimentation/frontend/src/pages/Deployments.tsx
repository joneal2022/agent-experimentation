import React, { useState, useEffect } from 'react';
import { RocketLaunchIcon, CheckCircleIcon, XCircleIcon } from '@heroicons/react/24/outline';
import toast from 'react-hot-toast';
import classNames from 'classnames';

import api from '../services/api';
import KPICard from '../components/KPICard';

interface Deployment {
  page_id: string;
  deployment_date: string;
  cases: string[];
  has_failures: boolean;
  failure_details: any[];
  deployment_status: string;
  client_project: string;
  success_rate: number;
  ai_summary: string;
  case_count: number;
  failure_count: number;
}

interface DeploymentsResponse {
  deployments: Deployment[];
  pagination: any;
  summary: {
    total_deployments: number;
    failed_deployments: number;
    success_rate: number;
  };
}

const Deployments: React.FC = () => {
  const [deployments, setDeployments] = useState<DeploymentsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({
    days_back: 30,
    failed_only: false,
  });
  const [deploymentAnalysis, setDeploymentAnalysis] = useState<any>(null);

  useEffect(() => {
    loadDeployments();
    loadDeploymentAnalysis();
  }, [filters]);

  const loadDeployments = async () => {
    try {
      setLoading(true);
      const response = await api.get('/api/confluence/deployments', { params: filters });
      setDeployments(response.data);
    } catch (error) {
      console.error('Failed to load deployments:', error);
      toast.error('Failed to load deployments');
    } finally {
      setLoading(false);
    }
  };

  const loadDeploymentAnalysis = async () => {
    try {
      const response = await api.get('/api/confluence/deployments/analysis', {
        params: { days_back: filters.days_back }
      });
      setDeploymentAnalysis(response.data);
    } catch (error) {
      console.error('Failed to load deployment analysis:', error);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">Deployments</h1>
        <button
          onClick={() => {
            loadDeployments();
            loadDeploymentAnalysis();
          }}
          disabled={loading}
          className="btn btn-primary disabled:opacity-50"
        >
          {loading ? 'Loading...' : 'Refresh'}
        </button>
      </div>

      {/* Summary KPIs */}
      {deployments && (
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
          <KPICard
            title="Total Deployments"
            value={deployments.summary.total_deployments}
            subtitle={`Last ${filters.days_back} days`}
            icon={RocketLaunchIcon}
            color="blue"
            loading={loading}
          />
          
          <KPICard
            title="Failed Deployments"
            value={deployments.summary.failed_deployments}
            subtitle="Deployment failures"
            icon={XCircleIcon}
            color={deployments.summary.failed_deployments === 0 ? 'green' : 'red'}
            loading={loading}
          />
          
          <KPICard
            title="Success Rate"
            value={`${Math.round(deployments.summary.success_rate)}%`}
            subtitle="Deployment success"
            icon={CheckCircleIcon}
            color={deployments.summary.success_rate >= 95 ? 'green' : 
                  deployments.summary.success_rate >= 85 ? 'yellow' : 'red'}
            loading={loading}
          />

          <KPICard
            title="Risk Assessment"
            value={deploymentAnalysis?.risk_level || 'Unknown'}
            subtitle="Based on recent trends"
            icon={RocketLaunchIcon}
            color={deploymentAnalysis?.risk_level === 'low' ? 'green' :
                  deploymentAnalysis?.risk_level === 'medium' ? 'yellow' : 'red'}
            loading={loading}
          />
        </div>
      )}

      {/* Filters */}
      <div className="card">
        <div className="card-header">
          <h3 className="text-lg font-semibold text-gray-900">Filters</h3>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Time Period
            </label>
            <select
              value={filters.days_back}
              onChange={(e) => setFilters({ ...filters, days_back: parseInt(e.target.value) })}
              className="w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500"
            >
              <option value={7}>Last 7 days</option>
              <option value={30}>Last 30 days</option>
              <option value={90}>Last 90 days</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Filter Type
            </label>
            <label className="inline-flex items-center">
              <input
                type="checkbox"
                checked={filters.failed_only}
                onChange={(e) => setFilters({ ...filters, failed_only: e.target.checked })}
                className="rounded border-gray-300 text-primary-600 shadow-sm focus:border-primary-500 focus:ring-primary-500"
              />
              <span className="ml-2 text-sm text-gray-700">Show failed deployments only</span>
            </label>
          </div>

          <div className="flex items-end">
            <button
              onClick={() => setFilters({ days_back: 30, failed_only: false })}
              className="btn btn-secondary w-full"
            >
              Clear Filters
            </button>
          </div>
        </div>
      </div>

      {/* Deployment Analysis */}
      {deploymentAnalysis && (
        <div className="card">
          <div className="card-header">
            <h3 className="text-lg font-semibold text-gray-900">Deployment Analysis</h3>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-gray-900">
                {deploymentAnalysis.total_deployments || 0}
              </div>
              <div className="text-sm text-gray-500">Total Deployments</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-red-600">
                {deploymentAnalysis.failed_deployments || 0}
              </div>
              <div className="text-sm text-gray-500">Failed</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-green-600">
                {Math.round(deploymentAnalysis.success_rate || 100)}%
              </div>
              <div className="text-sm text-gray-500">Success Rate</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-blue-600">
                {Object.keys(deploymentAnalysis.by_client || {}).length}
              </div>
              <div className="text-sm text-gray-500">Affected Clients</div>
            </div>
          </div>

          {deploymentAnalysis.recommendations && (
            <div className="bg-blue-50 border border-blue-200 rounded-md p-4">
              <h4 className="text-sm font-medium text-blue-900 mb-2">Recommendations:</h4>
              <ul className="text-sm text-blue-800 space-y-1">
                {deploymentAnalysis.recommendations.map((rec: string, index: number) => (
                  <li key={index}>• {rec}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Deployments List */}
      <div className="card">
        <div className="card-header">
          <h3 className="text-lg font-semibold text-gray-900">
            Recent Deployments ({deployments?.deployments.length || 0})
          </h3>
        </div>

        {loading ? (
          <div className="flex justify-center py-12">
            <div className="loading-spinner"></div>
          </div>
        ) : deployments && deployments.deployments.length > 0 ? (
          <div className="space-y-4">
            {deployments.deployments.map((deployment) => (
              <div
                key={deployment.page_id}
                className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow"
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center space-x-3">
                    <div className={classNames(
                      'w-3 h-3 rounded-full',
                      deployment.has_failures ? 'bg-red-500' : 'bg-green-500'
                    )}></div>
                    <div>
                      <h4 className="text-lg font-medium text-gray-900">
                        {deployment.client_project || 'Unknown Project'}
                      </h4>
                      <p className="text-sm text-gray-500">
                        {new Date(deployment.deployment_date).toLocaleDateString()}
                      </p>
                    </div>
                  </div>
                  
                  <div className="text-right">
                    <div className="text-sm font-medium text-gray-900">
                      {deployment.case_count} cases deployed
                    </div>
                    {deployment.has_failures && (
                      <div className="text-sm text-red-600">
                        {deployment.failure_count} failures
                      </div>
                    )}
                  </div>
                </div>

                {deployment.ai_summary && (
                  <div className="bg-gray-50 rounded-md p-3 mb-3">
                    <p className="text-sm text-gray-700">{deployment.ai_summary}</p>
                  </div>
                )}

                {deployment.has_failures && deployment.failure_details.length > 0 && (
                  <div className="bg-red-50 border border-red-200 rounded-md p-3">
                    <h5 className="text-sm font-medium text-red-900 mb-2">Failure Details:</h5>
                    <ul className="text-sm text-red-800 space-y-1">
                      {deployment.failure_details.slice(0, 3).map((failure, index) => (
                        <li key={index}>• {typeof failure === 'string' ? failure : JSON.stringify(failure)}</li>
                      ))}
                      {deployment.failure_details.length > 3 && (
                        <li className="text-red-600">+ {deployment.failure_details.length - 3} more failures</li>
                      )}
                    </ul>
                  </div>
                )}

                <div className="flex items-center justify-between text-sm text-gray-500 mt-3">
                  <span>Status: {deployment.deployment_status}</span>
                  <span>Success Rate: {Math.round(deployment.success_rate)}%</span>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-12">
            <RocketLaunchIcon className="mx-auto h-12 w-12 text-gray-400" />
            <h3 className="mt-2 text-sm font-medium text-gray-900">No deployments found</h3>
            <p className="mt-1 text-sm text-gray-500">
              No deployments found for the current filters.
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

export default Deployments;