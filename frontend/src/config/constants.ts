/**
 * Application constants
 */

// API Configuration
export const API_BASE_URL = process.env.EXPO_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
export const WS_BASE_URL = process.env.EXPO_PUBLIC_WS_URL || 'ws://localhost:8000/ws';

// Storage Keys
export const STORAGE_KEYS = {
  ACCESS_TOKEN: 'access_token',
  REFRESH_TOKEN: 'refresh_token',
  THEME: 'theme_preference',
  LANGUAGE: 'language_preference',
} as const;

// Theme
export const THEME_COLORS = {
  primary: '#2196F3',
  secondary: '#FF9800',
  success: '#4CAF50',
  error: '#F44336',
  warning: '#FFC107',
  info: '#00BCD4',
  background: '#FFFFFF',
  surface: '#F5F5F5',
  text: '#212121',
  textSecondary: '#757575',
  border: '#E0E0E0',
  disabled: '#BDBDBD',
} as const;

// Issue Types
export const ISSUE_TYPES = {
  TASK: 'task',
  BUG: 'bug',
  STORY: 'story',
  EPIC: 'epic',
  SUBTASK: 'subtask',
} as const;

// Issue Priorities
export const ISSUE_PRIORITIES = {
  LOW: 'low',
  MEDIUM: 'medium',
  HIGH: 'high',
  CRITICAL: 'critical',
} as const;

// Issue Statuses
export const ISSUE_STATUSES = {
  TO_DO: 'to_do',
  IN_PROGRESS: 'in_progress',
  IN_REVIEW: 'in_review',
  DONE: 'done',
  BLOCKED: 'blocked',
} as const;

// Priority Colors
export const PRIORITY_COLORS = {
  low: '#4CAF50',
  medium: '#FFC107',
  high: '#FF9800',
  critical: '#F44336',
} as const;

// Status Colors
export const STATUS_COLORS = {
  to_do: '#757575',
  in_progress: '#2196F3',
  in_review: '#FF9800',
  done: '#4CAF50',
  blocked: '#F44336',
} as const;

// Pagination
export const DEFAULT_PAGE_SIZE = 50;
export const MAX_PAGE_SIZE = 100;

// Query Cache Times (in milliseconds)
export const CACHE_TIMES = {
  SHORT: 1000 * 60 * 5, // 5 minutes
  MEDIUM: 1000 * 60 * 15, // 15 minutes
  LONG: 1000 * 60 * 60, // 1 hour
} as const;

// API Retry Configuration
export const RETRY_CONFIG = {
  retries: 3,
  retryDelay: (attemptIndex: number) => Math.min(1000 * 2 ** attemptIndex, 30000),
} as const;
