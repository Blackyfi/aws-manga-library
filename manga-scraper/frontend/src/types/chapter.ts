/**
 * TypeScript type definitions for Chapter entities
 * Defines the data structures for manga chapters and pages
 */

export interface Chapter {
  id: string;
  mangaId: string;
  chapterNumber: number;
  title?: string;
  volumeNumber?: number;
  pages: ChapterPage[];
  pageCount: number;
  releaseDate: string;
  scanlationGroup?: string;
  translator?: string;
  language: string;
  version: number;
  isRead?: boolean;
  readProgress?: number;
  downloadUrl?: string;
  externalUrl?: string;
}

export interface ChapterPage {
  pageNumber: number;
  imageUrl: string;
  width?: number;
  height?: number;
  fileSize?: number;
  format?: ImageFormat;
  thumbnailUrl?: string;
}

export type ImageFormat =
  | 'jpg'
  | 'jpeg'
  | 'png'
  | 'webp'
  | 'avif';

export interface ChapterListItem {
  id: string;
  chapterNumber: number;
  title?: string;
  volumeNumber?: number;
  pageCount: number;
  releaseDate: string;
  isRead: boolean;
  readProgress?: number;
}

export interface ChapterListProps {
  chapters: ChapterListItem[];
  currentChapterId?: string;
  onChapterClick?: (chapterId: string) => void;
  loading?: boolean;
  error?: string | null;
}

export interface ReadingProgress {
  mangaId: string;
  chapterId: string;
  currentPage: number;
  totalPages: number;
  percentage: number;
  lastReadAt: string;
  isCompleted: boolean;
}

export interface ChapterNavigation {
  previousChapter?: ChapterListItem;
  currentChapter: ChapterListItem;
  nextChapter?: ChapterListItem;
}

export interface ReaderSettings {
  readingMode: ReadingMode;
  pageLayout: PageLayout;
  fitMode: FitMode;
  backgroundColor: string;
  autoAdvance: boolean;
  autoAdvanceDelay: number;
  showPageNumber: boolean;
  preloadPages: number;
}

export type ReadingMode =
  | 'single-page'
  | 'double-page'
  | 'long-strip'
  | 'webtoon';

export type PageLayout =
  | 'left-to-right'
  | 'right-to-left'
  | 'vertical';

export type FitMode =
  | 'fit-width'
  | 'fit-height'
  | 'fit-screen'
  | 'original';

export interface ChapterFilters {
  language?: string;
  scanlationGroup?: string;
  minChapterNumber?: number;
  maxChapterNumber?: number;
  unreadOnly?: boolean;
}

export interface ChapterBatch {
  mangaId: string;
  chapters: Chapter[];
  totalChapters: number;
  hasMore: boolean;
  nextCursor?: string;
}
