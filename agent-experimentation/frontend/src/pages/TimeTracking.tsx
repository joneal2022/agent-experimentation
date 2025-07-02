import React, { useState, useEffect } from 'react';
import { ClockIcon, UserGroupIcon, CurrencyDollarIcon, ChartBarIcon } from '@heroicons/react/24/outline';
import { BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import toast from 'react-hot-toast';

import api from '../services/api';
import KPICard from '../components/KPICard';

interface TimeTrackingData {
  worklogs: any;
  utilization: any;
  productivity: any;
  statistics: any;
}

interface TeamMemberBreakdown {
  name: string;
  total_hours: number;
  billable_hours: number;
  tickets_worked: string[];
  ticket_count: number;
  ticket_details: Array<{
    key: string;
    summary: string;
    hours: number;
  }>;
}

const TimeTracking: React.FC = () => {
  const [data, setData] = useState<TimeTrackingData | null>(null);
  const [loading, setLoading] = useState(true);
  const [authors, setAuthors] = useState<string[]>([]);
  const [projects, setProjects] = useState<string[]>([]);
  const [teamBreakdown, setTeamBreakdown] = useState<TeamMemberBreakdown[]>([]);
  const [filters, setFilters] = useState({
    days_back: 30,
    author: '',
    project: '',
  });

  useEffect(() => {
    loadTimeTrackingData();
    loadDropdownData();
    loadTeamBreakdown();
  }, [filters]);

  const loadDropdownData = async () => {
    try {
      const [authorsResponse, projectsResponse] = await Promise.all([
        api.get('/api/tempo/authors'),
        api.get('/api/tempo/projects'),
      ]);
      setAuthors(authorsResponse.data.authors || []);
      setProjects(projectsResponse.data.projects || []);
    } catch (error) {
      console.error('Failed to load dropdown data:', error);
    }
  };

  const loadTeamBreakdown = async () => {
    try {
      const response = await api.get('/api/tempo/team-member-breakdown', { 
        params: { days_back: filters.days_back } 
      });
      setTeamBreakdown(response.data.team_members || []);
    } catch (error) {
      console.error('Failed to load team breakdown:', error);
    }
  };

  const loadTimeTrackingData = async () => {
    try {
      setLoading(true);
      const [worklogsResponse, utilizationResponse, statisticsResponse] = await Promise.all([
        api.get('/api/tempo/worklogs', { params: filters }),
        api.get('/api/tempo/utilization-report', { params: { days_back: filters.days_back } }),
        api.get('/api/tempo/statistics'),
      ]);

      setData({
        worklogs: worklogsResponse.data,
        utilization: utilizationResponse.data,
        productivity: null, // Would be loaded from productivity endpoint
        statistics: statisticsResponse.data,
      });
    } catch (error) {
      console.error('Failed to load time tracking data:', error);
      toast.error('Failed to load time tracking data');
    } finally {
      setLoading(false);
    }
  };

  const refreshAllData = async () => {
    await Promise.all([
      loadTimeTrackingData(),
      loadTeamBreakdown(),
      loadDropdownData()
    ]);
  };

  const COLORS = ['#3b82f6', '#ef4444', '#f59e0b', '#22c55e', '#8b5cf6'];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">Time Tracking & Productivity</h1>
        <button
          onClick={refreshAllData}
          disabled={loading}
          className="btn btn-primary disabled:opacity-50"
        >
          {loading ? 'Loading...' : 'Refresh'}
        </button>
      </div>

      {/* Summary KPIs */}
      {data && (
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
          <KPICard
            title="Total Hours"
            value={data.worklogs?.summary?.total_hours_logged?.toFixed(1) || '0'}
            subtitle={`Last ${filters.days_back} days`}
            icon={ClockIcon}
            color="blue"
            loading={loading}
          />
          
          <KPICard
            title="Team Utilization"
            value={`${Math.round(data.utilization?.team_summary?.average_utilization || 0)}%`}
            subtitle="Average capacity usage"
            icon={UserGroupIcon}
            color={
              (data.utilization?.team_summary?.average_utilization || 0) >= 80 && 
              (data.utilization?.team_summary?.average_utilization || 0) <= 110 ? 'green' : 'yellow'
            }
            loading={loading}
          />
          
          <KPICard
            title="Billable Hours"
            value={data.utilization?.team_summary?.total_billable_hours?.toFixed(1) || '0'}
            subtitle="Revenue generating"
            icon={CurrencyDollarIcon}
            color="green"
            loading={loading}
          />

          <KPICard
            title="Active Contributors"
            value={data.worklogs?.summary?.unique_contributors || 0}
            subtitle="Team members logging time"
            icon={UserGroupIcon}
            color="purple"
            loading={loading}
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
              Author
            </label>
            <select
              value={filters.author}
              onChange={(e) => setFilters({ ...filters, author: e.target.value })}
              className="w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500"
            >
              <option value="">All Authors</option>
              {authors.map((author) => (
                <option key={author} value={author}>
                  {author}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Project
            </label>
            <select
              value={filters.project}
              onChange={(e) => setFilters({ ...filters, project: e.target.value })}
              className="w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500"
            >
              <option value="">All Projects</option>
              {projects.map((project) => (
                <option key={project} value={project}>
                  {project}
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-end">
            <button
              onClick={() => setFilters({ days_back: 30, author: '', project: '' })}
              className="btn btn-secondary w-full"
            >
              Clear Filters
            </button>
          </div>
        </div>
      </div>

      {/* Utilization Charts */}
      {data?.utilization && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Team Utilization */}
          <div className="card">
            <div className="card-header">
              <h3 className="text-lg font-semibold text-gray-900">Team Utilization</h3>
            </div>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={Object.entries(data.utilization.utilization_by_user).slice(0, 8).map(([user, data]: [string, any]) => ({
                  user: user, // Full name for better readability
                  utilization: data.utilization_percentage,
                  target: 100
                }))}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="user" tick={{ fontSize: 12 }} />
                  <YAxis tick={{ fontSize: 12 }} />
                  <Tooltip />
                  <Bar dataKey="utilization" fill="#3b82f6" name="Utilization %" />
                  <Bar dataKey="target" fill="#e5e7eb" name="Target %" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Utilization Status */}
          <div className="card">
            <div className="card-header">
              <h3 className="text-lg font-semibold text-gray-900">Utilization Status</h3>
            </div>
            <div className="h-64 flex items-center justify-center">
              <div className="grid grid-cols-3 gap-8 text-center">
                <div>
                  <div className="text-3xl font-bold text-red-600">
                    {data.utilization.team_summary.underutilized_members}
                  </div>
                  <div className="text-sm text-gray-500">Under-utilized</div>
                  <div className="text-xs text-gray-400">&lt; 80%</div>
                </div>
                <div>
                  <div className="text-3xl font-bold text-green-600">
                    {data.utilization.team_summary.optimal_utilization_members}
                  </div>
                  <div className="text-sm text-gray-500">Optimal</div>
                  <div className="text-xs text-gray-400">80-110%</div>
                </div>
                <div>
                  <div className="text-3xl font-bold text-red-600">
                    {data.utilization.team_summary.overutilized_members}
                  </div>
                  <div className="text-sm text-gray-500">Over-utilized</div>
                  <div className="text-xs text-gray-400">&gt; 110%</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Team Member Breakdown */}
      {teamBreakdown.length > 0 && (
        <div className="card">
          <div className="card-header">
            <h3 className="text-lg font-semibold text-gray-900">Team Member Breakdown</h3>
            <p className="text-sm text-gray-500">Top 10 team members by hours logged in the last {filters.days_back} days</p>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Team Member
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Total Hours
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Billable Hours
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Tickets Worked
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Top Tickets
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {teamBreakdown.map((member, index) => (
                  <tr key={index} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center">
                        <div className="flex-shrink-0 h-8 w-8">
                          <div className="h-8 w-8 rounded-full bg-blue-500 flex items-center justify-center">
                            <span className="text-sm font-medium text-white">
                              {member.name.split(' ').map(n => n[0]).join('').substring(0, 2)}
                            </span>
                          </div>
                        </div>
                        <div className="ml-4">
                          <div className="text-sm font-medium text-gray-900">{member.name}</div>
                          <div className="text-xs text-gray-500">{member.ticket_count} tickets</div>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm font-semibold text-gray-900">{member.total_hours}h</div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm font-semibold text-green-600">{member.billable_hours}h</div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm text-gray-900">{member.ticket_count} tickets</div>
                      <div className="text-xs text-gray-500">
                        {member.tickets_worked.slice(0, 3).join(', ')}
                        {member.tickets_worked.length > 3 && ` +${member.tickets_worked.length - 3} more`}
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="space-y-1">
                        {member.ticket_details.slice(0, 2).map((ticket, ticketIndex) => (
                          <div key={ticketIndex} className="text-xs">
                            <span className="font-medium text-primary-600">{ticket.key}</span>
                            <span className="text-gray-600 ml-1">({ticket.hours}h)</span>
                            <div className="text-gray-500 truncate max-w-xs" title={ticket.summary}>
                              {ticket.summary.length > 40 ? `${ticket.summary.substring(0, 40)}...` : ticket.summary}
                            </div>
                          </div>
                        ))}
                        {member.ticket_details.length > 2 && (
                          <div className="text-xs text-gray-400">
                            +{member.ticket_details.length - 2} more tickets
                          </div>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Utilization Recommendations */}
      {data?.utilization?.recommendations && (
        <div className="card">
          <div className="card-header">
            <h3 className="text-lg font-semibold text-gray-900">Utilization Recommendations</h3>
          </div>
          <div className="bg-blue-50 border border-blue-200 rounded-md p-4">
            <ul className="text-sm text-blue-800 space-y-2">
              {data.utilization.recommendations.map((rec: string, index: number) => (
                <li key={index}>• {rec}</li>
              ))}
            </ul>
          </div>
        </div>
      )}

      {/* Recent Worklogs */}
      {data?.worklogs && (
        <div className="card">
          <div className="card-header">
            <h3 className="text-lg font-semibold text-gray-900">
              Recent Time Entries ({data.worklogs.worklogs?.length || 0})
            </h3>
          </div>

          {loading ? (
            <div className="flex justify-center py-12">
              <div className="loading-spinner"></div>
            </div>
          ) : data.worklogs.worklogs?.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Date
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Author
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Ticket
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Hours
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Description
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {data.worklogs.worklogs.slice(0, 20).map((worklog: any, index: number) => (
                    <tr key={worklog.tempo_worklog_id || index} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {new Date(worklog.start_date).toLocaleDateString()}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {worklog.author_display_name}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className="text-sm font-medium text-primary-600">
                          {worklog.jira_ticket_key}
                        </span>
                        <div className="text-xs text-gray-500">
                          {worklog.project_key}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {worklog.time_spent_hours?.toFixed(1)}h
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-900 max-w-xs truncate">
                        {worklog.description || 'No description'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="text-center py-12">
              <ClockIcon className="mx-auto h-12 w-12 text-gray-400" />
              <h3 className="mt-2 text-sm font-medium text-gray-900">No time entries found</h3>
              <p className="mt-1 text-sm text-gray-500">
                No time entries found for the current filters.
              </p>
            </div>
          )}
        </div>
      )}


      {/* Statistics */}
      {data?.statistics && (
        <div className="card">
          <div className="card-header">
            <h3 className="text-lg font-semibold text-gray-900">Time Tracking Statistics</h3>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <div className="text-center">
              <div className="text-2xl font-bold text-gray-900">
                {data.statistics.worklogs.total}
              </div>
              <div className="text-sm text-gray-500">Total Worklogs</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-blue-600">
                {data.statistics.worklogs.recent_30_days}
              </div>
              <div className="text-sm text-gray-500">Recent (30d)</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-green-600">
                {data.statistics.worklogs.total_hours_30_days?.toFixed(0)}h
              </div>
              <div className="text-sm text-gray-500">Hours (30d)</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-purple-600">
                {data.statistics.teams.total}
              </div>
              <div className="text-sm text-gray-500">Teams</div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default TimeTracking;