'use client';

/**
 * Chapter Reader Page
 * ===================
 *
 * Displays manga chapter with full reader functionality
 */

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { MangaReader } from '@/components/reader/MangaReader';
import { chapterApi } from '@/lib/api/chapters';
import { mangaApi } from '@/lib/api/manga';
import type { ChapterDetail, ChapterPage, ChapterNavigation } from '@/types/chapter';
import type { MangaDetail } from '@/types/manga';

// Loading component
function ReaderLoading() {
  return (
    <div className="flex items-center justify-center h-screen bg-black">
      <div className="text-center">
        <div className="loading-spinner mb-4">
          <div className="spinner-ring"></div>
        </div>
        <p className="text-gray-400">Loading chapter...</p>
      </div>
    </div>
  );
}

// Error component
function ReaderError({ error }: { error: string }) {
  const router = useRouter();

  return (
    <div className="flex items-center justify-center h-screen bg-black">
      <div className="text-center max-w-md px-4">
        <h1 className="text-2xl font-bold text-red-500 mb-4">Error Loading Chapter</h1>
        <p className="text-gray-400 mb-6">{error}</p>
        <button
          onClick={() => router.back()}
          className="px-6 py-3 bg-gray-700 text-white rounded-lg hover:bg-gray-600 transition"
        >
          Go Back
        </button>
      </div>
    </div>
  );
}

// Main page component (client-side)
export default function ChapterPage() {
  const params = useParams();
  const mangaId = params?.id as string;
  const chapterId = params?.chapter as string;

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<{
    chapter: ChapterDetail;
    pages: ChapterPage[];
    navigation: ChapterNavigation;
    mangaTitle: string;
  } | null>(null);

  useEffect(() => {
    async function loadChapter() {
      try {
        setLoading(true);
        setError(null);

        // Fetch chapter details and pages in parallel
        const [chapterDetail, pages, manga] = await Promise.all([
          chapterApi.getChapterById(chapterId),
          chapterApi.getChapterPages(chapterId),
          mangaApi.getMangaById(mangaId),
        ]);

        if (!chapterDetail || !pages || pages.length === 0) {
          throw new Error('Chapter not found or has no pages');
        }

        // Get all chapters for navigation
        const allChapters = await chapterApi.getChaptersByMangaId(mangaId, {
          sortBy: 'chapterNumber',
          sortOrder: 'asc',
        });

        // Find current chapter index
        const currentIndex = allChapters.items.findIndex((ch) => ch.id === chapterId);

        // Prepare navigation
        const navigation = {
          currentChapter: allChapters.items[currentIndex],
          previousChapter: currentIndex > 0 ? allChapters.items[currentIndex - 1] : undefined,
          nextChapter: currentIndex < allChapters.items.length - 1 ? allChapters.items[currentIndex + 1] : undefined,
        };

        setData({
          chapter: chapterDetail,
          pages,
          navigation,
          mangaTitle: manga.title,
        });
      } catch (err) {
        console.error('Error loading chapter:', err);
        setError(err instanceof Error ? err.message : 'Failed to load chapter');
      } finally {
        setLoading(false);
      }
    }

    if (mangaId && chapterId) {
      loadChapter();
    }
  }, [mangaId, chapterId]);

  if (loading) {
    return <ReaderLoading />;
  }

  if (error || !data) {
    return <ReaderError error={error || 'Unknown error occurred'} />;
  }

  return (
    <MangaReader
      chapter={data.chapter}
      pages={data.pages}
      navigation={data.navigation}
      mangaTitle={data.mangaTitle}
    />
  );
}
