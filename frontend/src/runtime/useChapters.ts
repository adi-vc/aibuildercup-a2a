/**
 * useChapters — the page's two chapter behaviours (frontend/DESIGN.md):
 *
 *  • the fixed header takes the field colour of the chapter beneath it,
 *    switching at chapter edges (the direction's signature move);
 *  • the parts of each chapter ([data-reveal]) rise in once, staggered by
 *    their --i index, as they enter the viewport.
 *
 * Both are progressive: the page renders complete without them.
 */

import { useEffect, type RefObject } from 'react';

export function useChapters(header: RefObject<HTMLElement | null>, deps: unknown[] = []): void {
  useEffect(() => {
    document.documentElement.classList.add('js');

    const reveal = new IntersectionObserver((entries) => {
      for (const e of entries) {
        if (e.isIntersecting) {
          e.target.classList.add('is-in');
          reveal.unobserve(e.target);
        }
      }
    }, { rootMargin: '0px 0px -8% 0px' });
    document.querySelectorAll('[data-reveal]').forEach((el) => reveal.observe(el));

    let ink: IntersectionObserver | null = null;
    const watchInk = () => {
      ink?.disconnect();
      const h = header.current?.offsetHeight ?? 64;
      // A one-pixel band just under the header: whichever chapter covers it owns the header.
      ink = new IntersectionObserver((entries) => {
        for (const e of entries) {
          const field = (e.target as HTMLElement).dataset.field;
          if (e.isIntersecting && field && header.current) header.current.dataset.field = field;
        }
      }, { rootMargin: `-${h}px 0px -${Math.max(0, window.innerHeight - h - 1)}px 0px` });
      document.querySelectorAll('.chapter[data-field]').forEach((el) => ink!.observe(el));
    };
    watchInk();
    window.addEventListener('resize', watchInk);

    return () => {
      reveal.disconnect();
      ink?.disconnect();
      window.removeEventListener('resize', watchInk);
    };
    // Re-scan when the page's chapters change (manifest loaded, view switched).
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);
}
