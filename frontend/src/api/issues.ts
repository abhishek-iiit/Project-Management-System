/**
 * Issues API
 */

import apiClient, { ApiResponse, PaginatedResponse } from './client';
import { Issue, IssueCreateData, IssueUpdateData, Comment, CommentCreateData } from '@/types/issue';

export interface IssueFilters {
  project?: string;
  status?: string;
  priority?: string;
  assignee?: string;
  issue_type?: string;
  search?: string;
  page?: number;
  page_size?: number;
  ordering?: string;
}

export const issuesApi = {
  /**
   * List issues with filters
   */
  async list(filters?: IssueFilters): Promise<PaginatedResponse<Issue>> {
    const response = await apiClient.get('/issues/', { params: filters });
    return response.data;
  },

  /**
   * Get issue by ID
   */
  async get(id: string): Promise<ApiResponse<Issue>> {
    const response = await apiClient.get(`/issues/${id}/`);
    return response.data;
  },

  /**
   * Create issue
   */
  async create(data: IssueCreateData): Promise<ApiResponse<Issue>> {
    const response = await apiClient.post('/issues/', data);
    return response.data;
  },

  /**
   * Update issue
   */
  async update(id: string, data: IssueUpdateData): Promise<ApiResponse<Issue>> {
    const response = await apiClient.patch(`/issues/${id}/`, data);
    return response.data;
  },

  /**
   * Delete issue
   */
  async delete(id: string): Promise<void> {
    await apiClient.delete(`/issues/${id}/`);
  },

  /**
   * Transition issue status
   */
  async transition(id: string, transitionId: string): Promise<ApiResponse<Issue>> {
    const response = await apiClient.post(`/issues/${id}/transition/`, {
      transition: transitionId,
    });
    return response.data;
  },

  /**
   * Get issue comments
   */
  async getComments(issueId: string): Promise<ApiResponse<Comment[]>> {
    const response = await apiClient.get(`/issues/${issueId}/comments/`);
    return response.data;
  },

  /**
   * Add comment
   */
  async addComment(issueId: string, data: CommentCreateData): Promise<ApiResponse<Comment>> {
    const response = await apiClient.post(`/issues/${issueId}/comments/`, data);
    return response.data;
  },

  /**
   * Get issue history
   */
  async getHistory(issueId: string): Promise<ApiResponse<any[]>> {
    const response = await apiClient.get(`/issues/${issueId}/history/`);
    return response.data;
  },

  /**
   * Add watcher
   */
  async addWatcher(issueId: string, userId: string): Promise<ApiResponse<void>> {
    const response = await apiClient.post(`/issues/${issueId}/watchers/`, { user_id: userId });
    return response.data;
  },

  /**
   * Remove watcher
   */
  async removeWatcher(issueId: string, userId: string): Promise<void> {
    await apiClient.delete(`/issues/${issueId}/watchers/${userId}/`);
  },
};
