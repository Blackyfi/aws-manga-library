# Manga Reader Features

## Overview

A professional, feature-rich manga reading experience with full customization options, dark mode, and immersive reading capabilities.

---

## ✨ Key Features

### 1. **Full Black Dark Mode** ✓
- Maximum black background (#000000) for optimal reading in dark environments
- Reduces eye strain during long reading sessions
- Toggle on/off via settings sidebar
- Persists across sessions

### 2. **Collapsible Settings Sidebar** ✓
- Located on the right side of the screen
- Can be completely hidden or shown
- Contains all reader settings and customization options
- Accessible via settings button in top bar or keyboard shortcut `S`
- Smooth slide-in/slide-out animations

### 3. **Image Fit Modes** ✓
Choose how manga pages are displayed:

- **Fit to Screen**: Entire image fits within the viewport (default)
- **Fit to Width**: Image width matches screen width (good for vertical scrolling)
- **Fit to Height**: Image height matches screen height
- **Original Size**: Display image at its native resolution

### 4. **Reading Modes** ✓
Multiple reading modes supported:

- **Single Page**: One page at a time with click navigation (recommended)
- **Double Page**: Two pages side-by-side (for spreads)
- **Long Strip**: Continuous vertical scroll
- **Webtoon**: Optimized for webtoon-style comics

### 5. **Click-Based Page Navigation** ✓
Intuitive navigation zones:

- **Click LEFT side** → Previous page
- **Click RIGHT side** → Next page
- **Center zone** → No action (reserved for UI interactions)
- Visual indicators on hover show navigation directions

### 6. **Keyboard Navigation** ✓
Full keyboard support:

| Key | Action |
|-----|--------|
| `←` Left Arrow | Previous page |
| `→` Right Arrow | Next page |
| `↑` Up Arrow | Previous page |
| `↓` Down Arrow | Next page |
| `S` | Toggle settings sidebar |
| `I` | Toggle immersive mode |
| `F11` | Toggle fullscreen (browser) |
| `Esc` | Exit reader (when not fullscreen) |

### 7. **Immersive Mode** ✓
Distraction-free reading experience:

- Hides ALL UI elements (top bar, progress tracker, chapter navigation, hints)
- Only the manga page is visible
- Perfect for focused reading sessions
- Toggle with `I` key or via settings
- Automatically hides sidebar when enabled

### 8. **Fullscreen Support** ✓
- Native browser fullscreen API integration
- Toggle via settings sidebar
- Combines with immersive mode for ultimate reading experience
- Automatically detects fullscreen state changes

### 9. **Progress Tracking** ✓
Real-time reading progress display:

- Current page / Total pages counter
- Percentage complete
- Visual progress bar with gradient
- Chapter and manga title display
- Automatically hidden in immersive mode

### 10. **Chapter Navigation** ✓
Easy switching between chapters:

- Previous/Next chapter buttons at bottom of screen
- Automatically disabled at start/end of manga
- Smooth transitions between chapters
- Optional auto-advance to next chapter (configurable)

### 11. **Image Preloading** ✓
Smooth reading experience:

- Preloads next 3 pages by default (configurable)
- Eliminates loading delays during reading
- Smart resource management

### 12. **Settings Persistence** ✓
All settings are saved:

- Reader mode preferences
- Image fit mode
- Dark mode state
- Sidebar visibility
- Stored in browser localStorage
- Persists across sessions and page reloads

### 13. **Responsive Design** ✓
Works on all devices:

- Desktop optimized (recommended)
- Tablet support
- Mobile-friendly layout
- Adaptive controls and UI sizing

### 14. **Loading States** ✓
Professional loading experience:

- Animated loading spinner
- Smooth fade-in transitions
- Error handling with retry option
- Loading indicators for images

### 15. **Visual Polish** ✓
Beautiful design details:

- Smooth animations and transitions
- Gradient effects on UI elements
- Backdrop blur for overlays
- Hover effects on interactive elements
- Professional color scheme

---

## 🎮 Usage Guide

### Starting the Reader

Navigate to any chapter page:
```
/manga/[manga-id]/[chapter-id]
```

### Basic Reading Flow

1. **Open chapter** - Reader loads with your saved settings
2. **Click right** to advance pages
3. **Click left** to go back
4. **Press `I`** for immersive mode when ready to focus
5. **Press `S`** to adjust settings anytime

### Recommended Settings for Best Experience

**For maximum immersion:**
- ✓ Dark Mode: ON
- ✓ Immersive Mode: ON
- ✓ Fullscreen: ON
- ✓ Fit Mode: Fit to Screen
- ✓ Show Page Number: OFF (or ON if you prefer)

**For comfortable reading:**
- ✓ Dark Mode: ON
- ✓ Immersive Mode: OFF
- ✓ Fit Mode: Fit to Screen or Fit to Width
- ✓ Show Page Number: ON

---

## 🏗️ Technical Architecture

### Component Structure

```
MangaReader (Orchestrator)
├── PageViewer (Image display + click zones)
├── ReaderControls (Settings sidebar)
├── ProgressTracker (Page counter + progress bar)
└── Chapter Navigation (Prev/Next chapter buttons)
```

### State Management

- **Zustand Store** (`readerStore.ts`)
  - Centralized state for all reader settings
  - Persistent storage via localStorage
  - Type-safe actions and selectors

### Styling

- **CSS Modules** approach
- Responsive breakpoints
- CSS animations and transitions
- Custom scrollbar styling
- Dark mode optimized

### Performance Optimizations

1. **Image Preloading**: Next 3 pages preloaded in background
2. **Lazy Loading**: Components load only when needed
3. **Memoization**: Prevents unnecessary re-renders
4. **Optimized Images**: WebP format from CDN with optimization params

---

## 🎨 Customization

### Adding New Fit Modes

Edit `readerStore.ts` and add to `FitMode` type:

```typescript
export type FitMode =
  | 'fit-width'
  | 'fit-height'
  | 'fit-screen'
  | 'original'
  | 'your-custom-mode'; // Add here
```

### Changing Colors

Edit `reader.css`:

```css
/* Main background in dark mode */
.manga-reader {
  background: #000; /* Change this */
}

/* Accent colors */
.progress-tracker-fill {
  background: linear-gradient(to right, #3b82f6, #8b5cf6); /* Change this */
}
```

### Adjusting Preload Count

Edit `readerStore.ts`:

```typescript
const defaultSettings: ReaderSettings = {
  // ...
  preloadPages: 3, // Change this number
};
```

---

## 🐛 Troubleshooting

### Images Not Loading

1. Check browser console for errors
2. Verify image URLs are accessible
3. Check CDN configuration
4. Try clicking the "Retry" button

### Fullscreen Not Working

1. Requires user interaction to trigger
2. Some browsers may block fullscreen API
3. Try using F11 key instead
4. Check browser permissions

### Settings Not Saving

1. Check localStorage is enabled in browser
2. Clear browser cache and try again
3. Check browser console for errors
4. Verify localStorage quota not exceeded

### Performance Issues

1. Reduce `preloadPages` count
2. Use "Fit to Screen" or "Fit to Width" modes
3. Close other browser tabs
4. Clear browser cache

---

## 📱 Browser Support

### Fully Supported
- ✓ Chrome 90+
- ✓ Firefox 88+
- ✓ Safari 14+
- ✓ Edge 90+

### Partially Supported
- ⚠️ Mobile Safari (fullscreen limited)
- ⚠️ Older browsers (may lack some features)

---

## 🚀 Future Enhancements

Potential features for future releases:

- [ ] Bookmark system
- [ ] Reading history
- [ ] Multiple page view (side-by-side)
- [ ] Zoom and pan controls
- [ ] Customizable click zones
- [ ] Reading timer
- [ ] Custom color themes
- [ ] Page transition animations
- [ ] Offline reading mode
- [ ] Social features (sharing, comments)

---

## 📄 Files Reference

### Core Components
- `MangaReader.tsx` - Main orchestrator
- `PageViewer.tsx` - Image display and navigation
- `ReaderControls.tsx` - Settings sidebar
- `ProgressTracker.tsx` - Progress display

### State & Logic
- `readerStore.ts` - Zustand state management
- `ThemeProvider.tsx` - Theme context provider

### Styling
- `reader.css` - Complete reader styles
- `globals.css` - Base styles

### Routes
- `app/manga/[id]/[chapter]/page.tsx` - Chapter page route

### Types
- `types/chapter.ts` - TypeScript type definitions

---

## 📝 License

Part of the AWS Manga Library project.

---

**Enjoy your immersive manga reading experience! 📚✨**
