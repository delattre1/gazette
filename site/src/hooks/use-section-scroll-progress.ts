"use client";

import { useEffect, useState, type RefObject } from "react";

/**
 * 0→1 while scrolling through a tall section (sticky text inside).
 * Uses layout math only, no Framer/GSAP, so it stays predictable.
 */
export function useSectionScrollProgress(
  ref: RefObject<HTMLElement | null>,
): number {
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    let frame = 0;

    const measure = () => {
      const node = ref.current;
      if (!node) return;

      const rect = node.getBoundingClientRect();
      const top = rect.top + window.scrollY;
      const height = node.offsetHeight;
      const view = window.innerHeight;
      const travel = Math.max(height - view, 1);
      const raw = (window.scrollY - top) / travel;

      setProgress(Math.min(1, Math.max(0, raw)));
    };

    const onScroll = () => {
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(measure);
    };

    measure();
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onScroll);

    return () => {
      cancelAnimationFrame(frame);
      window.removeEventListener("scroll", onScroll);
      window.removeEventListener("resize", onScroll);
    };
  }, [ref]);

  return progress;
}
