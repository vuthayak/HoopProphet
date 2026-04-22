import '@testing-library/jest-dom';

// Mock ResizeObserver which is not available in jsdom
class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}
window.ResizeObserver = ResizeObserver;
window.LocalResizeObserver = ResizeObserver;
