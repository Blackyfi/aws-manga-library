/**
 * Home Page
 * =========
 *
 * Landing page for the manga library
 */

export default function HomePage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-gray-900 to-black">
      <div className="text-center px-4">
        <h1 className="text-5xl font-bold text-white mb-4">
          Manga Library
        </h1>
        <p className="text-xl text-gray-400 mb-8">
          Your personal manga reading experience
        </p>

        <div className="space-y-4">
          <div className="bg-gray-800 p-6 rounded-lg border border-gray-700">
            <h2 className="text-2xl font-semibold text-white mb-2">
              Reader Features
            </h2>
            <ul className="text-left text-gray-300 space-y-2">
              <li>✓ Full black dark mode</li>
              <li>✓ Collapsible settings sidebar</li>
              <li>✓ Click-based navigation</li>
              <li>✓ Immersive fullscreen mode</li>
              <li>✓ Multiple image fit modes</li>
              <li>✓ Keyboard shortcuts</li>
            </ul>
          </div>

          <div className="bg-gray-800 p-6 rounded-lg border border-gray-700">
            <h3 className="text-lg font-semibold text-white mb-2">
              Quick Start
            </h3>
            <p className="text-gray-400 text-sm">
              Navigate to <code className="bg-gray-900 px-2 py-1 rounded">/manga/[id]/[chapter]</code> to start reading
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
