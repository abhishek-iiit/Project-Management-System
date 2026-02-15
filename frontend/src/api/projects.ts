/**
 * Projects API
 */

import apiClient, { ApiResponse, PaginatedResponse } from './client';
import { Project, ProjectCreateData, ProjectMember } from '@/types/project';

export const projectsApi = {
  /**
   * List projects
   */
  async list(page = 1, pageSize = 50): Promise<PaginatedResponse<Project>> {
    const response = await apiClient.get('/projects/', {
      params: { page, page_size: pageSize },
    });
    return response.data;
  },

  /**
   * Get project by ID
   */
  async get(id: string): Promise<ApiResponse<Project>> {
    const response = await apiClient.get(`/projects/${id}/`);
    return response.data;
  },

  /**
   * Create project
   */
  async create(data: ProjectCreateData): Promise<ApiResponse<Project>> {
    const response = await apiClient.post('/projects/', data);
    return response.data;
  },

  /**
   * Update project
   */
  async update(id: string, data: Partial<ProjectCreateData>): Promise<ApiResponse<Project>> {
    const response = await apiClient.patch(`/projects/${id}/`, data);
    return response.data;
  },

  /**
   * Delete project
   */
  async delete(id: string): Promise<void> {
    await apiClient.delete(`/projects/${id}/`);
  },

  /**
   * Get project members
   */
  async getMembers(projectId: string): Promise<ApiResponse<ProjectMember[]>> {
    const response = await apiClient.get(`/projects/${projectId}/members/`);
    return response.data;
  },

  /**
   * Add project member
   */
  async addMember(projectId: string, userId: string, role: string): Promise<ApiResponse<ProjectMember>> {
    const response = await apiClient.post(`/projects/${projectId}/members/`, {
      user_id: userId,
      role,
    });
    return response.data;
  },

  /**
   * Remove project member
   */
  async removeMember(projectId: string, userId: string): Promise<void> {
    await apiClient.delete(`/projects/${projectId}/members/${userId}/`);
  },
};
