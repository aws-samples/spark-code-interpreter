// Complete ResizeObserver error suppression utility
export const suppressResizeObserverErrors = () => {
  // Override ResizeObserver constructor
  const OriginalResizeObserver = window.ResizeObserver;
  window.ResizeObserver = class extends OriginalResizeObserver {
    constructor(callback) {
      super((entries, observer) => {
        window.requestAnimationFrame(() => {
          try {
            callback(entries, observer);
          } catch (error) {
            // Silently ignore all ResizeObserver errors
          }
        });
      });
    }
  };

  // Suppress console errors
  const originalError = console.error;
  console.error = (...args) => {
    const message = args[0]?.toString?.() || '';
    if (message.includes('ResizeObserver')) return;
    originalError.apply(console, args);
  };

  // Global error handlers
  window.addEventListener('error', (e) => {
    if (e.message?.includes('ResizeObserver')) {
      e.preventDefault();
      e.stopPropagation();
      return false;
    }
  }, true);

  window.addEventListener('unhandledrejection', (e) => {
    if (e.reason?.message?.includes('ResizeObserver')) {
      e.preventDefault();
      return false;
    }
  }, true);
};