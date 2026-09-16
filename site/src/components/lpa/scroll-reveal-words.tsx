"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useSectionScrollProgress } from "@/hooks/use-section-scroll-progress";
import { cn } from "@/lib/utils";

const DIM = 0.2;

function wordOpacity(
  progress: number,
  index: number,
  count: number,
  spread = 0.82,
  window = 0.2,
): number {
  if (count <= 1) {
    return DIM + progress * (1 - DIM);
  }
  const start = (index / (count - 1)) * spread;
  const end = Math.min(start + window, 1);
  if (progress <= start) return DIM;
  if (progress >= end) return 1;
  const t = (progress - start) / (end - start);
  return DIM + t * (1 - DIM);
}

function WordSpan({
  word,
  opacity,
}: {
  word: string;
  opacity: number;
}) {
  return (
    <span className="relative inline-block">
      <span aria-hidden="true" className="select-none" style={{ opacity: DIM }}>
        {word}
      </span>
      <span
        aria-hidden="true"
        className="absolute inset-0"
        style={{ opacity }}
      >
        {word}
      </span>
    </span>
  );
}

export type ScrollRevealWordsProps = {
  lines: readonly string[];
  as?: "p" | "h1" | "h2";
  className?: string;
  runwayVh?: number;
};

export function ScrollRevealWords({
  lines,
  as: Tag = "p",
  className,
  runwayVh = 200,
}: ScrollRevealWordsProps) {
  const sectionRef = useRef<HTMLElement>(null);
  const progress = useSectionScrollProgress(sectionRef);
  const [reducedMotion, setReducedMotion] = useState(false);

  const lineWords = useMemo(
    () => lines.map((line) => line.trim().split(/\s+/).filter(Boolean)),
    [lines],
  );

  const totalWords = useMemo(
    () => lineWords.reduce((n, row) => n + row.length, 0),
    [lineWords],
  );

  const flatLabel = useMemo(() => lines.join(" "), [lines]);

  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    const update = () => setReducedMotion(mq.matches);
    update();
    mq.addEventListener("change", update);
    return () => mq.removeEventListener("change", update);
  }, []);

  let wordIndex = 0;

  return (
    <section
      ref={sectionRef}
      className="relative w-full"
      style={{ minHeight: `${runwayVh}vh` }}
      aria-label={flatLabel}
    >
      <div className="sticky top-0 flex min-h-[100dvh] items-center justify-center px-[4vw]">
        <Tag
          aria-label={flatLabel}
          className={cn(
            "m-0 w-full max-w-[42rem] text-[clamp(2rem,7vw,3.75rem)] font-semibold leading-[1.08] tracking-[-0.03em]",
            className,
          )}
        >
          {lineWords.map((words, lineIdx) => (
            <span key={lineIdx} className="block">
              {words.map((word, i) => {
                const index = wordIndex++;
                const opacity = reducedMotion
                  ? 1
                  : wordOpacity(progress, index, totalWords);
                return (
                  <span key={`${lineIdx}-${word}-${i}`}>
                    <WordSpan word={word} opacity={opacity} />
                    {i < words.length - 1 ? " " : null}
                  </span>
                );
              })}
            </span>
          ))}
        </Tag>
      </div>
    </section>
  );
}
