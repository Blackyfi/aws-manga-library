/**
 * TypeScript type definitions for API responses and requests
 * Defines the contract between frontend and backend services
 */

import { Manga, MangaFilters, MangaListResponse } from './manga';
import { Chapter, ChapterBatch, ChapterFilters, ReadingProgress } from './chapter';

/**
 * Generic API response wrapper
 */
export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: ApiError;
  timestamp: string;
}

/**
 * API error structure
 */
export interface ApiError {
  code: string;
  message: string;
  details?: Record<string, unknown>;
  statusCode: number;
}

/**
 * Pagination parameters
 */
export interface PaginationParams {
  page: number;
  pageSize: number;
  cursor?: string;
}

/**
 * Manga API Endpoints
 */
export interface MangaApiClient {
  // List and search
  getMangaList(params: MangaListParams): Promise<ApiResponse<MangaListResponse>>;
  searchManga(query: string, filters?: MangaFilters): Promise<ApiResponse<MangaListResponse>>;

  // Single manga operations
  getMangaById(id: string): Promise<ApiResponse<Manga>>;
  getMangaBySlug(slug: string): Promise<ApiResponse<Manga>>;

  // Favorites
  getFavoriteManga(userId: string): Promise<ApiResponse<MangaListResponse>>;
  addToFavorites(mangaId: string): Promise<ApiResponse<void>>;
  removeFromFavorites(mangaId: string): Promise<ApiResponse<void>>;
}

export interface MangaListParams extends PaginationParams {
  filters?: MangaFilters;
}

/**
 * Chapter API Endpoints
 */
export interface ChapterApiClient {
  // List chapters
  getChaptersByMangaId(
    mangaId: string,
    params?: ChapterListParams
  ): Promise<ApiResponse<ChapterBatch>>;

  // Single chapter operations
  getChapterById(chapterId: string): Promise<ApiResponse<Chapter>>;
  getChapterPages(chapterId: string): Promise<ApiResponse<ChapterPage[]>>;

  // Reading progress
  getReadingProgress(mangaId: string): Promise<ApiResponse<ReadingProgress>>;
  updateReadingProgress(
    progress: UpdateProgressRequest
  ): Promise<ApiResponse<ReadingProgress>>;
  markChapterAsRead(chapterId: string): Promise<ApiResponse<void>>;
  markChapterAsUnread(chapterId: string): Promise<ApiResponse<void>>;
}

export interface ChapterListParams extends PaginationParams {
  filters?: ChapterFilters;
}

export interface UpdateProgressRequest {
  mangaId: string;
  chapterId: string;
  currentPage: number;
  totalPages: number;
}

/**
 * HTTP Client configuration
 */
export interface ApiClientConfig {
  baseUrl: string;
  timeout?: number;
  headers?: Record<string, string>;
  withCredentials?: boolean;
  retries?: number;
  retryDelay?: number;
}

/**
 * Request options
 */
export interface RequestOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH';
  headers?: Record<string, string>;
  body?: unknown;
  params?: Record<string, string | number | boolean | undefined>;
  signal?: AbortSignal;
  cache?: RequestCache;
}

/**
 * AWS S3 Pre-signed URL response
 */
export interface PresignedUrlResponse {
  url: string;
  expiresAt: string;
  headers?: Record<string, string>;
}

/**
 * Batch operation response
 */
export interface BatchResponse<T> {
  successful: T[];
  failed: BatchError[];
  total: number;
  successCount: number;
  failureCount: number;
}

export interface BatchError {
  id: string;
  error: ApiError;
}

/**
 * Health check response
 */
export interface HealthCheckResponse {
  status: 'healthy' | 'degraded' | 'unhealthy';
  version: string;
  uptime: number;
  services: ServiceStatus[];
  timestamp: string;
}

export interface ServiceStatus {
  name: string;
  status: 'operational' | 'degraded' | 'down';
  responseTime?: number;
  lastChecked: string;
}

/**
 * Rate limit information
 */
export interface RateLimitInfo {
  limit: number;
  remaining: number;
  reset: string;
  retryAfter?: number;
}

/**
 * API Response headers
 */
export interface ApiResponseHeaders {
  'x-request-id': string;
  'x-rate-limit-limit'?: string;
  'x-rate-limit-remaining'?: string;
  'x-rate-limit-reset'?: string;
  'cache-control'?: string;
  'etag'?: string;
}

/**
 * Cache policy
 */
export type CachePolicy =
  | 'no-cache'
  | 'force-cache'
  | 'default'
  | 'reload'
  | 'no-store'
  | 'only-if-cached';

/**
 * API endpoints configuration
 */
export interface ApiEndpoints {
  manga: {
    list: string;
    search: string;
    byId: (id: string) => string;
    favorites: string;
  };
  chapters: {
    byMangaId: (mangaId: string) => string;
    byId: (id: string) => string;
    pages: (chapterId: string) => string;
    progress: string;
  };
  health: string;
}
