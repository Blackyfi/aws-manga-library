'use client';

/**
 * Reader Controls Component
 * =========================
 *
 * Collapsible sidebar with all reader settings
 */

import { useReaderStore } from '@/lib/store/readerStore';
import type { FitMode, ReadingMode } from '@/types/chapter';

interface ReaderControlsProps {
  onClose?: () => void;
}

export function ReaderControls({ onClose }: ReaderControlsProps) {
  const {
    settings,
    isSidebarVisible,
    isDarkMode,
    isImmersiveMode,
    isFullscreen,
    setFitMode,
    setReadingMode,
    toggleDarkMode,
    toggleImmersiveMode,
    toggleFullscreen,
    toggleSidebar,
  } = useReaderStore();

  if (!isSidebarVisible) return null;

  const fitModes: { value: FitMode; label: string; description: string }[] = [
    { value: 'fit-screen', label: 'Fit to Screen', description: 'Fit entire image to screen' },
    { value: 'fit-width', label: 'Fit to Width', description: 'Fit image width to screen' },
    { value: 'fit-height', label: 'Fit to Height', description: 'Fit image height to screen' },
    { value: 'original', label: 'Original Size', description: 'Show image at original size' },
  ];

  const readingModes: { value: ReadingMode; label: string; description: string }[] = [
    { value: 'single-page', label: 'Single Page', description: 'One page at a time' },
    { value: 'double-page', label: 'Double Page', description: 'Two pages side-by-side' },
    { value: 'long-strip', label: 'Long Strip', description: 'Continuous vertical scroll' },
    { value: 'webtoon', label: 'Webtoon', description: 'Optimized for webtoons' },
  ];

  return (
    <>
      {/* Overlay for mobile */}
      <div
        className="reader-controls-overlay"
        onClick={toggleSidebar}
        aria-hidden="true"
      />

      {/* Sidebar */}
      <aside className="reader-controls-sidebar">
        {/* Header */}
        <div className="reader-controls-header">
          <h2 className="text-lg font-semibold text-white">Reader Settings</h2>
          <button
            onClick={toggleSidebar}
            className="reader-controls-close-btn"
            aria-label="Close settings"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="reader-controls-content">

          {/* Display Mode Section */}
          <div className="reader-controls-section">
            <h3 className="reader-controls-section-title">Display Mode</h3>

            {/* Fit Mode */}
            <div className="reader-controls-group">
              <label className="reader-controls-label">Image Fit</label>
              <div className="reader-controls-options">
                {fitModes.map((mode) => (
                  <button
                    key={mode.value}
                    onClick={() => setFitMode(mode.value)}
                    className={`reader-controls-option-btn ${
                      settings.fitMode === mode.value ? 'active' : ''
                    }`}
                    title={mode.description}
                  >
                    <span className="reader-controls-option-label">{mode.label}</span>
                    {settings.fitMode === mode.value && (
                      <svg className="w-4 h-4 ml-auto" fill="currentColor" viewBox="0 0 20 20">
                        <path
                          fillRule="evenodd"
                          d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 11.586l7.293-7.293a1 1 0 011.414 0z"
                          clipRule="evenodd"
                        />
                      </svg>
                    )}
                  </button>
                ))}
              </div>
              <p className="reader-controls-description">
                {fitModes.find((m) => m.value === settings.fitMode)?.description}
              </p>
            </div>
          </div>

          {/* Reading Mode Section */}
          <div className="reader-controls-section">
            <h3 className="reader-controls-section-title">Reading Mode</h3>

            <div className="reader-controls-group">
              <label className="reader-controls-label">Page Layout</label>
              <div className="reader-controls-options">
                {readingModes.map((mode) => (
                  <button
                    key={mode.value}
                    onClick={() => setReadingMode(mode.value)}
                    className={`reader-controls-option-btn ${
                      settings.readingMode === mode.value ? 'active' : ''
                    }`}
                    title={mode.description}
                  >
                    <span className="reader-controls-option-label">{mode.label}</span>
                    {settings.readingMode === mode.value && (
                      <svg className="w-4 h-4 ml-auto" fill="currentColor" viewBox="0 0 20 20">
                        <path
                          fillRule="evenodd"
                          d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 11.586l7.293-7.293a1 1 0 011.414 0z"
                          clipRule="evenodd"
                        />
                      </svg>
                    )}
                  </button>
                ))}
              </div>
              <p className="reader-controls-description">
                {readingModes.find((m) => m.value === settings.readingMode)?.description}
              </p>
            </div>
          </div>

          {/* View Options Section */}
          <div className="reader-controls-section">
            <h3 className="reader-controls-section-title">View Options</h3>

            {/* Dark Mode Toggle */}
            <div className="reader-controls-toggle">
              <div className="flex-1">
                <label className="reader-controls-label">Dark Mode</label>
                <p className="reader-controls-description">Full black background for reading</p>
              </div>
              <button
                onClick={toggleDarkMode}
                className={`reader-controls-toggle-btn ${isDarkMode ? 'active' : ''}`}
                aria-label="Toggle dark mode"
              >
                <span className={`reader-controls-toggle-slider ${isDarkMode ? 'active' : ''}`} />
              </button>
            </div>

            {/* Immersive Mode Toggle */}
            <div className="reader-controls-toggle">
              <div className="flex-1">
                <label className="reader-controls-label">Immersive Mode</label>
                <p className="reader-controls-description">Hide all UI elements for distraction-free reading</p>
              </div>
              <button
                onClick={toggleImmersiveMode}
                className={`reader-controls-toggle-btn ${isImmersiveMode ? 'active' : ''}`}
                aria-label="Toggle immersive mode"
              >
                <span className={`reader-controls-toggle-slider ${isImmersiveMode ? 'active' : ''}`} />
              </button>
            </div>

            {/* Fullscreen Toggle */}
            <div className="reader-controls-toggle">
              <div className="flex-1">
                <label className="reader-controls-label">Fullscreen</label>
                <p className="reader-controls-description">Enter fullscreen mode (Press F11 or Esc to exit)</p>
              </div>
              <button
                onClick={toggleFullscreen}
                className={`reader-controls-toggle-btn ${isFullscreen ? 'active' : ''}`}
                aria-label="Toggle fullscreen"
              >
                <span className={`reader-controls-toggle-slider ${isFullscreen ? 'active' : ''}`} />
              </button>
            </div>

            {/* Show Page Number Toggle */}
            <div className="reader-controls-toggle">
              <div className="flex-1">
                <label className="reader-controls-label">Page Number</label>
                <p className="reader-controls-description">Show page counter</p>
              </div>
              <button
                onClick={() =>
                  useReaderStore.setState((state) => ({
                    settings: {
                      ...state.settings,
                      showPageNumber: !state.settings.showPageNumber,
                    },
                  }))
                }
                className={`reader-controls-toggle-btn ${settings.showPageNumber ? 'active' : ''}`}
                aria-label="Toggle page number"
              >
                <span className={`reader-controls-toggle-slider ${settings.showPageNumber ? 'active' : ''}`} />
              </button>
            </div>
          </div>

          {/* Keyboard Shortcuts Section */}
          <div className="reader-controls-section">
            <h3 className="reader-controls-section-title">Keyboard Shortcuts</h3>
            <div className="reader-controls-shortcuts">
              <div className="reader-controls-shortcut">
                <kbd className="reader-controls-kbd">←</kbd>
                <span className="text-sm text-gray-400">Previous Page</span>
              </div>
              <div className="reader-controls-shortcut">
                <kbd className="reader-controls-kbd">→</kbd>
                <span className="text-sm text-gray-400">Next Page</span>
              </div>
              <div className="reader-controls-shortcut">
                <kbd className="reader-controls-kbd">F11</kbd>
                <span className="text-sm text-gray-400">Fullscreen</span>
              </div>
              <div className="reader-controls-shortcut">
                <kbd className="reader-controls-kbd">I</kbd>
                <span className="text-sm text-gray-400">Immersive Mode</span>
              </div>
              <div className="reader-controls-shortcut">
                <kbd className="reader-controls-kbd">S</kbd>
                <span className="text-sm text-gray-400">Toggle Sidebar</span>
              </div>
            </div>
          </div>
        </div>
      </aside>
    </>
  );
}
