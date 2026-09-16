"use client";

import { HeroPhone } from "@/components/lpa/HeroPhone";
import { ProjectShowcase } from "@/components/ui/project-showcase";
import { CONTENT_WIDE, LINKS, SECTION_PAD } from "@/lib/site";
import { cn } from "@/lib/utils";

export function EditionSection() {
  return (
    <section className={SECTION_PAD}>
      <div className={cn(CONTENT_WIDE, "hidden md:block")}>
        <div className="mb-12 flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
          <h2 className="font-serif text-[clamp(2.5rem,5vw,4rem)] font-normal tracking-tight">
            Editions.
          </h2>
          <p className="max-w-2xl text-sm font-light leading-relaxed text-pretty text-muted-foreground lg:max-w-xl lg:text-right">
            Three layouts. One photo on your phone, at the hour you chose.
          </p>
        </div>
        <ProjectShowcase />

        <div className="mt-12 flex flex-col items-start gap-3">
          <a
            href="#install"
            className="inline-flex min-h-11 items-center justify-center rounded-full bg-foreground px-6 text-[15px] font-medium text-background transition-transform active:scale-[0.97]"
          >
            Get started
          </a>
          <a
            href={LINKS.index}
            className="text-[15px] text-link transition-opacity hover:opacity-80"
          >
            View on Agent Index
          </a>
        </div>
      </div>

      <div className="md:hidden">
        <h2 className="mb-8 font-serif text-[clamp(2.25rem,9vw,3rem)] font-normal tracking-tight">
          Editions.
        </h2>
        <HeroPhone />
      </div>
    </section>
  );
}
