'use client';

/**
 * Manga Reader Component
 * ======================
 *
 * Main orchestrator component for the manga reading experience
 */

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useReaderStore } from '@/lib/store/readerStore';
import { PageViewer } from './PageViewer';
import { ReaderControls } from './ReaderControls';
import { ProgressTracker } from './ProgressTracker';
import type { ChapterPage, ChapterDetail, ChapterNavigation } from '@/types/chapter';

interface MangaReaderProps {
  chapter: ChapterDetail;
  pages: ChapterPage[];
  navigation?: ChapterNavigation;
  mangaTitle?: string;
}

export function MangaReader({ chapter, pages, navigation, mangaTitle }: MangaReaderProps) {
  const router = useRouter();
  const {
    currentPage,
    totalPages,
    settings,
    isImmersiveMode,
    isSidebarVisible,
    setCurrentPage,
    setTotalPages,
    resetReader,
    toggleSidebar,
    toggleImmersiveMode,
  } = useReaderStore();

  const [isLoading, setIsLoading] = useState(true);

  // Initialize reader
  useEffect(() => {
    setTotalPages(pages.length);
    setCurrentPage(1);
    setIsLoading(false);

    return () => {
      resetReader();
    };
  }, [pages.length, setTotalPages, setCurrentPage, resetReader]);

  // Handle keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Toggle sidebar with 'S' key
      if (e.key === 's' || e.key === 'S') {
        e.preventDefault();
        toggleSidebar();
      }

      // Toggle immersive mode with 'I' key
      if (e.key === 'i' || e.key === 'I') {
        e.preventDefault();
        toggleImmersiveMode();
      }

      // Exit reader with 'Escape' key (if not in fullscreen)
      if (e.key === 'Escape' && !document.fullscreenElement) {
        e.preventDefault();
        router.back();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [toggleSidebar, toggleImmersiveMode, router]);

  // Handle fullscreen changes
  useEffect(() => {
    const handleFullscreenChange = () => {
      const isCurrentlyFullscreen = !!document.fullscreenElement;
      useReaderStore.setState({ isFullscreen: isCurrentlyFullscreen });
    };

    document.addEventListener('fullscreenchange', handleFullscreenChange);
    return () => document.removeEventListener('fullscreenchange', handleFullscreenChange);
  }, []);

  // Auto-navigate to next chapter when reaching the last page
  useEffect(() => {
    if (
      currentPage === totalPages &&
      totalPages > 0 &&
      navigation?.nextChapter &&
      settings.autoAdvance
    ) {
      const timer = setTimeout(() => {
        router.push(`/manga/${navigation.currentChapter.mangaId}/${navigation.nextChapter!.id}`);
      }, settings.autoAdvanceDelay);

      return () => clearTimeout(timer);
    }
  }, [currentPage, totalPages, navigation, settings.autoAdvance, settings.autoAdvanceDelay, router]);

  const handlePageChange = (page: number) => {
    setCurrentPage(page);
  };

  if (isLoading) {
    return (
      <div className="reader-loading">
        <div className="loading-spinner">
          <div className="spinner-ring"></div>
        </div>
        <p className="text-gray-400 mt-4">Loading chapter...</p>
      </div>
    );
  }

  return (
    <div className="manga-reader" data-immersive={isImmersiveMode}>
      {/* Top bar with close button and chapter info (hidden in immersive mode) */}
      {!isImmersiveMode && (
        <div className="reader-topbar">
          <button
            onClick={() => router.back()}
            className="reader-close-btn"
            aria-label="Close reader"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
            <span className="ml-2">Close</span>
          </button>

          <div className="reader-chapter-info">
            {mangaTitle && <span className="reader-manga-title">{mangaTitle}</span>}
            <span className="reader-chapter-title">{chapter.title}</span>
          </div>

          <button
            onClick={toggleSidebar}
            className="reader-settings-btn"
            aria-label="Toggle settings"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
              />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
            <span className="ml-2">Settings</span>
          </button>
        </div>
      )}

      {/* Main reader area */}
      <div className="reader-main">
        <PageViewer pages={pages} currentPage={currentPage} onPageChange={handlePageChange} />
      </div>

      {/* Progress tracker (bottom) */}
      <ProgressTracker chapterTitle={chapter.title} mangaTitle={mangaTitle} />

      {/* Settings sidebar (right) */}
      <ReaderControls />

      {/* Chapter navigation (hidden in immersive mode) */}
      {!isImmersiveMode && navigation && (
        <div className="reader-chapter-nav">
          {navigation.previousChapter ? (
            <button
              onClick={() =>
                router.push(`/manga/${navigation.currentChapter.mangaId}/${navigation.previousChapter!.id}`)
              }
              className="reader-chapter-nav-btn reader-chapter-nav-prev"
            >
              <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                <path
                  fillRule="evenodd"
                  d="M12.707 5.293a1 1 0 010 1.414L9.414 10l3.293 3.293a1 1 0 01-1.414 1.414l-4-4a1 1 0 010-1.414l4-4a1 1 0 011.414 0z"
                  clipRule="evenodd"
                />
              </svg>
              <span>Previous Chapter</span>
            </button>
          ) : (
            <div />
          )}

          {navigation.nextChapter ? (
            <button
              onClick={() =>
                router.push(`/manga/${navigation.currentChapter.mangaId}/${navigation.nextChapter!.id}`)
              }
              className="reader-chapter-nav-btn reader-chapter-nav-next"
            >
              <span>Next Chapter</span>
              <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                <path
                  fillRule="evenodd"
                  d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z"
                  clipRule="evenodd"
                />
              </svg>
            </button>
          ) : (
            <div />
          )}
        </div>
      )}

      {/* Hint overlay for first-time users (can be dismissed) */}
      {!isImmersiveMode && currentPage === 1 && (
        <div className="reader-hint">
          <p className="text-sm text-gray-400">
            Click left/right to navigate • Press <kbd className="reader-hint-kbd">I</kbd> for immersive mode •
            Press <kbd className="reader-hint-kbd">S</kbd> for settings
          </p>
        </div>
      )}
    </div>
  );
}
