/**
 * Project types
 */

import { User } from './auth';

export interface Organization {
  id: string;
  name: string;
  slug: string;
  description: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Project {
  id: string;
  organization: Organization;
  name: string;
  key: string;
  description: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ProjectCreateData {
  organization: string;
  name: string;
  key: string;
  description?: string;
}

export interface ProjectMember {
  id: string;
  project: string;
  user: User;
  role: string;
  is_active: boolean;
  created_at: string;
}
