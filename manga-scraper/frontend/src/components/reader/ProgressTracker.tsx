'use client';

/**
 * Progress Tracker Component
 * ===========================
 *
 * Shows current page number and progress through the chapter
 */

import { useReaderStore } from '@/lib/store/readerStore';

interface ProgressTrackerProps {
  chapterTitle?: string;
  mangaTitle?: string;
}

export function ProgressTracker({ chapterTitle, mangaTitle }: ProgressTrackerProps) {
  const { currentPage, totalPages, settings, isImmersiveMode } = useReaderStore();

  // Don't show in immersive mode or if disabled in settings
  if (isImmersiveMode || !settings.showPageNumber) {
    return null;
  }

  const percentage = totalPages > 0 ? Math.round((currentPage / totalPages) * 100) : 0;

  return (
    <div className="progress-tracker">
      {/* Page counter */}
      <div className="progress-tracker-counter">
        <span className="progress-tracker-current">{currentPage}</span>
        <span className="progress-tracker-separator">/</span>
        <span className="progress-tracker-total">{totalPages}</span>
      </div>

      {/* Progress percentage */}
      <div className="progress-tracker-percentage">{percentage}%</div>

      {/* Progress bar */}
      <div className="progress-tracker-bar">
        <div
          className="progress-tracker-fill"
          style={{ width: `${percentage}%` }}
        />
      </div>

      {/* Chapter info */}
      {(chapterTitle || mangaTitle) && (
        <div className="progress-tracker-info">
          {mangaTitle && (
            <div className="progress-tracker-manga-title">{mangaTitle}</div>
          )}
          {chapterTitle && (
            <div className="progress-tracker-chapter-title">{chapterTitle}</div>
          )}
        </div>
      )}
    </div>
  );
}
