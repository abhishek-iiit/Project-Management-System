/**
 * Issue types
 */

import { User } from './auth';
import { Project } from './project';

export type IssueType = 'task' | 'bug' | 'story' | 'epic' | 'subtask';
export type IssuePriority = 'low' | 'medium' | 'high' | 'critical';
export type IssueStatus = 'to_do' | 'in_progress' | 'in_review' | 'done' | 'blocked';

export interface Issue {
  id: string;
  key: string;
  project: Project;
  summary: string;
  description: string;
  issue_type: IssueType;
  priority: IssuePriority;
  status: IssueStatus;
  reporter: User;
  assignee: User | null;
  labels: string[];
  custom_fields: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface IssueCreateData {
  project: string;
  summary: string;
  description?: string;
  issue_type: IssueType;
  priority?: IssuePriority;
  assignee?: string;
  labels?: string[];
  custom_fields?: Record<string, any>;
}

export interface IssueUpdateData {
  summary?: string;
  description?: string;
  priority?: IssuePriority;
  status?: IssueStatus;
  assignee?: string | null;
  labels?: string[];
  custom_fields?: Record<string, any>;
}

export interface Comment {
  id: string;
  issue: string;
  author: User;
  body: string;
  created_at: string;
  updated_at: string;
}

export interface CommentCreateData {
  body: string;
}
