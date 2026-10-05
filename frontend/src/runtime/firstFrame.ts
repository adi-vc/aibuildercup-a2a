/**
 * firstFrame.ts — the §64.7 criterion-4 measurement point.
 *
 * "First frame" = the first moment a hold is on screen with its plate (or the
 * plate's fallback) painted under its text layer. Marked once per page as a
 * User Timing mark, exposed on window for measurement harnesses, and posted
 * to the parent frame so an embedding host *may* observe it (it never has to).
 */

export interface FirstFrame {
  /** ms since this document's timeOrigin */
  ms: number;
  beatId: string;
  via: 'plate' | 'parallax' | 'fallback';
}

declare global {
  interface Window {
    __vachanFirstFrame?: FirstFrame;
  }
}

export function markFirstFrame(beatId: string, via: FirstFrame['via']): void {
  if (window.__vachanFirstFrame) return;
  // Wait for the paint that shows it, not just the decode.
  requestAnimationFrame(() => {
    if (window.__vachanFirstFrame) return;
    const ms = performance.now();
    window.__vachanFirstFrame = { ms, beatId, via };
    performance.mark('vachan:first-frame', { detail: { beatId, via } });
    if (window.parent !== window) {
      window.parent.postMessage({ type: 'vachan:first-frame', ms, beatId, via }, '*');
    }
  });
}
