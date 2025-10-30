'use client';

/**
 * Page Viewer Component
 * =====================
 *
 * Displays manga pages with click-zone navigation
 * Click left side = previous page, Click right side = next page
 */

import { useState, useEffect, useRef } from 'react';
import Image from 'next/image';
import { useReaderStore } from '@/lib/store/readerStore';
import type { ChapterPage } from '@/types/chapter';

interface PageViewerProps {
  pages: ChapterPage[];
  currentPage: number;
  onPageChange: (page: number) => void;
}

export function PageViewer({ pages, currentPage, onPageChange }: PageViewerProps) {
  const { settings, isImmersiveMode, nextPage, previousPage } = useReaderStore();
  const [imageLoaded, setImageLoaded] = useState(false);
  const [imageError, setImageError] = useState(false);
  const imageRef = useRef<HTMLDivElement>(null);

  const currentPageData = pages[currentPage - 1];

  useEffect(() => {
    setImageLoaded(false);
    setImageError(false);
  }, [currentPage]);

  // Preload next pages
  useEffect(() => {
    const preloadCount = settings.preloadPages;
    const pagesToPreload = pages.slice(currentPage, currentPage + preloadCount);

    pagesToPreload.forEach((page) => {
      const img = new window.Image();
      img.src = page.imageUrl;
    });
  }, [currentPage, pages, settings.preloadPages]);

  // Handle keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
        e.preventDefault();
        nextPage();
      } else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
        e.preventDefault();
        previousPage();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [nextPage, previousPage]);

  const handleClick = (e: React.MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const width = rect.width;

    // Divide the screen into three zones: left (30%), center (40%), right (30%)
    const leftZone = width * 0.3;
    const rightZone = width * 0.7;

    if (clickX < leftZone) {
      // Left zone - previous page
      previousPage();
    } else if (clickX > rightZone) {
      // Right zone - next page
      nextPage();
    }
    // Center zone - do nothing (could be used for showing/hiding UI)
  };

  if (!currentPageData) {
    return (
      <div className="flex items-center justify-center h-screen">
        <p className="text-gray-400">Page not found</p>
      </div>
    );
  }

  const getFitModeClass = () => {
    switch (settings.fitMode) {
      case 'fit-width':
        return 'reader-fit-width';
      case 'fit-height':
        return 'reader-fit-height';
      case 'fit-screen':
        return 'reader-fit-screen';
      case 'original':
        return 'reader-original';
      default:
        return 'reader-fit-screen';
    }
  };

  return (
    <div
      className="relative flex items-center justify-center w-full h-full cursor-pointer select-none"
      onClick={handleClick}
      style={{ backgroundColor: settings.backgroundColor }}
    >
      {/* Loading indicator */}
      {!imageLoaded && !imageError && (
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="loading-spinner">
            <div className="spinner-ring"></div>
          </div>
        </div>
      )}

      {/* Error state */}
      {imageError && (
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="text-center">
            <p className="text-gray-400 mb-2">Failed to load image</p>
            <button
              onClick={() => {
                setImageError(false);
                setImageLoaded(false);
              }}
              className="px-4 py-2 bg-gray-700 text-white rounded hover:bg-gray-600"
            >
              Retry
            </button>
          </div>
        </div>
      )}

      {/* Main image */}
      <div
        ref={imageRef}
        className={`reader-image-container ${getFitModeClass()}`}
        style={{
          opacity: imageLoaded ? 1 : 0,
          transition: 'opacity 0.2s ease-in-out',
        }}
      >
        <img
          src={currentPageData.imageUrl}
          alt={`Page ${currentPage}`}
          className="reader-image"
          onLoad={() => setImageLoaded(true)}
          onError={() => setImageError(true)}
          draggable={false}
        />
      </div>

      {/* Click zone indicators (only show when not in immersive mode and on hover) */}
      {!isImmersiveMode && (
        <div className="reader-click-zones pointer-events-none">
          <div className="reader-click-zone-left">
            <svg
              className="w-8 h-8 text-white opacity-0 group-hover:opacity-50"
              fill="currentColor"
              viewBox="0 0 20 20"
            >
              <path
                fillRule="evenodd"
                d="M12.707 5.293a1 1 0 010 1.414L9.414 10l3.293 3.293a1 1 0 01-1.414 1.414l-4-4a1 1 0 010-1.414l4-4a1 1 0 011.414 0z"
                clipRule="evenodd"
              />
            </svg>
          </div>
          <div className="reader-click-zone-right">
            <svg
              className="w-8 h-8 text-white opacity-0 group-hover:opacity-50"
              fill="currentColor"
              viewBox="0 0 20 20"
            >
              <path
                fillRule="evenodd"
                d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z"
                clipRule="evenodd"
              />
            </svg>
          </div>
        </div>
      )}
    </div>
  );
}
