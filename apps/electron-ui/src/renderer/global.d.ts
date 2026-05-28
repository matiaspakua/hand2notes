import type { H2nBridge } from '../preload';

declare global {
  interface Window {
    h2n: H2nBridge;
  }
}

export {};
