/**
 * Chapter Reader Page
 * ===================
 *
 * Displays manga chapter with full reader functionality
 */

import { Suspense } from 'react';
import { notFound } from 'next/navigation';
import { MangaReader } from '@/components/reader/MangaReader';
import { chapterApi } from '@/lib/api/chapters';
import { mangaApi } from '@/lib/api/manga';

interface ChapterPageProps {
  params: {
    id: string;
    chapter: string;
  };
}

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

// Main page component
export default async function ChapterPage({ params }: ChapterPageProps) {
  const { id: mangaId, chapter: chapterId } = params;

  try {
    // Fetch chapter details and pages in parallel
    const [chapterDetail, pages, manga] = await Promise.all([
      chapterApi.getChapterById(chapterId),
      chapterApi.getChapterPages(chapterId),
      mangaApi.getMangaById(mangaId),
    ]);

    if (!chapterDetail || !pages || pages.length === 0) {
      notFound();
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

    return (
      <Suspense fallback={<ReaderLoading />}>
        <MangaReader
          chapter={chapterDetail}
          pages={pages}
          navigation={navigation}
          mangaTitle={manga.title}
        />
      </Suspense>
    );
  } catch (error) {
    console.error('Error loading chapter:', error);
    notFound();
  }
}

// Generate metadata for SEO
export async function generateMetadata({ params }: ChapterPageProps) {
  try {
    const [chapter, manga] = await Promise.all([
      chapterApi.getChapterById(params.chapter),
      mangaApi.getMangaById(params.id),
    ]);

    return {
      title: `${manga.title} - ${chapter.title} | Manga Reader`,
      description: `Read ${manga.title} ${chapter.title} online`,
    };
  } catch {
    return {
      title: 'Chapter Not Found',
    };
  }
}

// Enable static generation for popular chapters (optional)
export const dynamic = 'force-dynamic'; // Can be changed to 'auto' or removed for static generation
