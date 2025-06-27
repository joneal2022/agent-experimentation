import React, { useState, useEffect } from 'react';
import {
  TicketIcon,
  ClockIcon,
  ExclamationTriangleIcon,
  MagnifyingGlassIcon,
} from '@heroicons/react/24/outline';
import toast from 'react-hot-toast';
import classNames from 'classnames';

import api from '../services/api';

interface Ticket {
  ticket_key: string;
  summary: string;
  description: string;
  status: string;
  priority: string;
  assignee: string;
  reporter: string;
  issue_type: string;
  created_date: string;
  updated_date: string;
  due_date?: string;
  days_in_current_status: number;
  is_stalled: boolean;
  is_overdue: boolean;
  level_ii_failed: boolean;
  story_points?: number;
  project_key: string;
}

interface TicketsResponse {
  tickets: Ticket[];
  pagination: {
    total_count: number;
    limit: number;
    offset: number;
    has_more: boolean;
  };
  filters_applied: any;
}

const Tickets: React.FC = () => {
  const [tickets, setTickets] = useState<TicketsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [filters, setFilters] = useState({
    project: '',
    status: '',
    assignee: '',
    priority: '',
    stalled_only: false,
    overdue_only: false,
    failed_testing_only: false,
  });

  useEffect(() => {
    loadTickets();
  }, [filters]);

  const loadTickets = async () => {
    try {
      setLoading(true);
      const response = await api.get('/api/jira/tickets', { params: filters });
      setTickets(response.data);
    } catch (error) {
      console.error('Failed to load tickets:', error);
      toast.error('Failed to load tickets');
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = async () => {
    if (!searchQuery.trim()) {
      toast.error('Please enter a search query');
      return;
    }

    try {
      setLoading(true);
      const response = await api.get('/api/jira/search', {
        params: { query: searchQuery, limit: 50 }
      });
      
      // Convert search results to tickets format
      const searchTickets = {
        tickets: response.data.results.map((result: any) => ({
          ticket_key: result.ticket_key,
          summary: result.title,
          description: result.content,
          status: 'Unknown',
          priority: 'Unknown',
          assignee: 'Unknown',
          reporter: 'Unknown',
          issue_type: 'Unknown',
          created_date: new Date().toISOString(),
          updated_date: new Date().toISOString(),
          days_in_current_status: 0,
          is_stalled: false,
          is_overdue: false,
          level_ii_failed: false,
          project_key: result.ticket_key?.split('-')[0] || 'Unknown'
        })),
        pagination: {
          total_count: response.data.results.length,
          limit: 50,
          offset: 0,
          has_more: false
        },
        filters_applied: { search_query: searchQuery }
      };
      
      setTickets(searchTickets);
    } catch (error) {
      console.error('Search failed:', error);
      toast.error('Search failed');
    } finally {
      setLoading(false);
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority?.toLowerCase()) {
      case 'highest':
      case 'critical': return 'text-red-600 bg-red-100';
      case 'high': return 'text-orange-600 bg-orange-100';
      case 'medium': return 'text-yellow-600 bg-yellow-100';
      case 'low': return 'text-blue-600 bg-blue-100';
      case 'lowest': return 'text-gray-600 bg-gray-100';
      default: return 'text-gray-600 bg-gray-100';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status?.toLowerCase()) {
      case 'open':
      case 'to do': return 'text-gray-600 bg-gray-100';
      case 'in progress': return 'text-blue-600 bg-blue-100';
      case 'in review': return 'text-purple-600 bg-purple-100';
      case 'done':
      case 'closed': return 'text-green-600 bg-green-100';
      default: return 'text-gray-600 bg-gray-100';
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">JIRA Tickets</h1>
        <button
          onClick={loadTickets}
          disabled={loading}
          className="btn btn-primary disabled:opacity-50"
        >
          {loading ? 'Loading...' : 'Refresh'}
        </button>
      </div>

      {/* Search */}
      <div className="card">
        <div className="card-header">
          <h3 className="text-lg font-semibold text-gray-900">Semantic Search</h3>
        </div>
        <div className="flex space-x-4">
          <div className="flex-1">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search tickets by content, description, or comments..."
              className="w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500"
              onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
            />
          </div>
          <button
            onClick={handleSearch}
            disabled={loading}
            className="btn btn-primary disabled:opacity-50"
          >
            <MagnifyingGlassIcon className="w-5 h-5 mr-2" />
            Search
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="card">
        <div className="card-header">
          <h3 className="text-lg font-semibold text-gray-900">Filters</h3>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4 mb-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Project
            </label>
            <input
              type="text"
              value={filters.project}
              onChange={(e) => setFilters({ ...filters, project: e.target.value })}
              placeholder="e.g. PIH, CMDR"
              className="w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Status
            </label>
            <input
              type="text"
              value={filters.status}
              onChange={(e) => setFilters({ ...filters, status: e.target.value })}
              placeholder="e.g. In Progress"
              className="w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Assignee
            </label>
            <input
              type="text"
              value={filters.assignee}
              onChange={(e) => setFilters({ ...filters, assignee: e.target.value })}
              placeholder="Assignee name"
              className="w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Priority
            </label>
            <select
              value={filters.priority}
              onChange={(e) => setFilters({ ...filters, priority: e.target.value })}
              className="w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500"
            >
              <option value="">All Priorities</option>
              <option value="Highest">Highest</option>
              <option value="High">High</option>
              <option value="Medium">Medium</option>
              <option value="Low">Low</option>
              <option value="Lowest">Lowest</option>
            </select>
          </div>

          <div className="flex items-end">
            <button
              onClick={() => setFilters({
                project: '',
                status: '',
                assignee: '',
                priority: '',
                stalled_only: false,
                overdue_only: false,
                failed_testing_only: false,
              })}
              className="btn btn-secondary w-full"
            >
              Clear
            </button>
          </div>
        </div>

        {/* Special Filters */}
        <div className="flex flex-wrap gap-2">
          <label className="inline-flex items-center">
            <input
              type="checkbox"
              checked={filters.stalled_only}
              onChange={(e) => setFilters({ ...filters, stalled_only: e.target.checked })}
              className="rounded border-gray-300 text-primary-600 shadow-sm focus:border-primary-500 focus:ring-primary-500"
            />
            <span className="ml-2 text-sm text-gray-700">Stalled Only</span>
          </label>

          <label className="inline-flex items-center">
            <input
              type="checkbox"
              checked={filters.overdue_only}
              onChange={(e) => setFilters({ ...filters, overdue_only: e.target.checked })}
              className="rounded border-gray-300 text-primary-600 shadow-sm focus:border-primary-500 focus:ring-primary-500"
            />
            <span className="ml-2 text-sm text-gray-700">Overdue Only</span>
          </label>

          <label className="inline-flex items-center">
            <input
              type="checkbox"
              checked={filters.failed_testing_only}
              onChange={(e) => setFilters({ ...filters, failed_testing_only: e.target.checked })}
              className="rounded border-gray-300 text-primary-600 shadow-sm focus:border-primary-500 focus:ring-primary-500"
            />
            <span className="ml-2 text-sm text-gray-700">Failed Testing Only</span>
          </label>
        </div>
      </div>

      {/* Tickets List */}
      <div className="card">
        <div className="card-header">
          <h3 className="text-lg font-semibold text-gray-900">
            Tickets ({tickets?.pagination.total_count || 0})
          </h3>
        </div>

        {loading ? (
          <div className="flex justify-center py-12">
            <div className="loading-spinner"></div>
          </div>
        ) : tickets && tickets.tickets.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Ticket
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Summary
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Priority
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Assignee
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Age
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Flags
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {tickets.tickets.map((ticket) => (
                  <tr key={ticket.ticket_key} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center">
                        <TicketIcon className="w-5 h-5 text-gray-400 mr-2" />
                        <div>
                          <div className="text-sm font-medium text-primary-600">
                            {ticket.ticket_key}
                          </div>
                          <div className="text-sm text-gray-500">
                            {ticket.project_key}
                          </div>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="text-sm font-medium text-gray-900 max-w-xs truncate">
                        {ticket.summary}
                      </div>
                      <div className="text-sm text-gray-500">
                        {ticket.issue_type}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={classNames(
                        'inline-flex px-2 py-1 text-xs font-semibold rounded-full',
                        getStatusColor(ticket.status)
                      )}>
                        {ticket.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={classNames(
                        'inline-flex px-2 py-1 text-xs font-semibold rounded-full',
                        getPriorityColor(ticket.priority)
                      )}>
                        {ticket.priority || 'None'}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {ticket.assignee || 'Unassigned'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {ticket.days_in_current_status} days
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex space-x-1">
                        {ticket.is_stalled && (
                          <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
                            <ClockIcon className="w-3 h-3 mr-1" />
                            Stalled
                          </span>
                        )}
                        {ticket.is_overdue && (
                          <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-red-100 text-red-800">
                            <ExclamationTriangleIcon className="w-3 h-3 mr-1" />
                            Overdue
                          </span>
                        )}
                        {ticket.level_ii_failed && (
                          <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-red-100 text-red-800">
                            ⚠️ Test Failed
                          </span>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center py-12">
            <TicketIcon className="mx-auto h-12 w-12 text-gray-400" />
            <h3 className="mt-2 text-sm font-medium text-gray-900">No tickets found</h3>
            <p className="mt-1 text-sm text-gray-500">
              No tickets match the current filters.
            </p>
          </div>
        )}

        {/* Pagination */}
        {tickets && tickets.pagination.has_more && (
          <div className="mt-6 flex justify-center">
            <button className="btn btn-secondary">
              Load More
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default Tickets;