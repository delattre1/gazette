"use client";

import { ScrollRevealWords } from "@/components/lpa/scroll-reveal-words";
import { GRADIENT_STATEMENTS } from "@/lib/site";

export function TextGradientManifesto() {
  return (
    <div aria-label="Manifesto" className="bg-background text-foreground">
      {GRADIENT_STATEMENTS.map((block, i) => (
        <ScrollRevealWords
          key={block.lines.join("|")}
          lines={block.lines}
          as={i === 0 ? "h1" : "p"}
          runwayVh={i === 0 ? 180 : 200}
        />
      ))}
    </div>
  );
}
