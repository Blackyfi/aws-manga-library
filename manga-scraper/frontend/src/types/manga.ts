/**
 * TypeScript type definitions for Manga entities
 * Defines the core data structures for manga metadata and related information
 */

export interface Manga {
  id: string;
  title: string;
  alternativeTitles?: string[];
  description: string;
  author: string;
  artist?: string;
  status: MangaStatus;
  genres: string[];
  tags: string[];
  coverImage: string;
  thumbnailImage?: string;
  rating?: number;
  totalChapters: number;
  releaseYear?: number;
  source: MangaSource;
  sourceUrl: string;
  lastUpdated: string;
  createdAt: string;
  views?: number;
  favorites?: number;
}

export type MangaStatus =
  | 'ongoing'
  | 'completed'
  | 'hiatus'
  | 'cancelled'
  | 'upcoming';

export type MangaSource =
  | 'mangadex'
  | 'mangakakalot'
  | 'other';

export interface MangaMetadata {
  mangaId: string;
  totalPages: number;
  averageChapterLength: number;
  updateFrequency?: string;
  isOfficial: boolean;
  ageRating?: AgeRating;
  language: string;
  translationStatus?: TranslationStatus;
}

export type AgeRating =
  | 'everyone'
  | 'teen'
  | 'mature'
  | 'explicit';

export type TranslationStatus =
  | 'ongoing'
  | 'completed'
  | 'dropped'
  | 'licensed';

export interface MangaFilters {
  genres?: string[];
  status?: MangaStatus[];
  source?: MangaSource[];
  minRating?: number;
  search?: string;
  sortBy?: MangaSortOption;
  sortOrder?: 'asc' | 'desc';
}

export type MangaSortOption =
  | 'title'
  | 'rating'
  | 'views'
  | 'favorites'
  | 'lastUpdated'
  | 'releaseYear'
  | 'totalChapters';

export interface MangaListResponse {
  manga: Manga[];
  total: number;
  page: number;
  pageSize: number;
  hasMore: boolean;
}

export interface MangaCardProps {
  manga: Manga;
  showDetails?: boolean;
  onFavorite?: (mangaId: string) => void;
  isFavorite?: boolean;
}

export interface MangaGridProps {
  manga: Manga[];
  loading?: boolean;
  error?: string | null;
  onLoadMore?: () => void;
  hasMore?: boolean;
}

export interface MangaDetailProps {
  manga: Manga;
  metadata?: MangaMetadata;
  onReadClick?: (chapterId: string) => void;
  onFavoriteClick?: () => void;
  isFavorite?: boolean;
}
