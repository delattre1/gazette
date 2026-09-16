"use client";

import { EditionLightbox } from "@/components/lpa/edition-lightbox";
import { EDITION_FACES, LINKS } from "@/lib/site";
import { cn } from "@/lib/utils";
import Image from "next/image";
import { useState } from "react";

export function HeroPhone() {
  const [faceIdx, setFaceIdx] = useState(0);
  const [fading, setFading] = useState(false);
  const [lightboxOpen, setLightboxOpen] = useState(false);
  const face = EDITION_FACES[faceIdx];

  const pickFace = (index: number) => {
    if (index === faceIdx || fading) return;
    setFading(true);
    window.setTimeout(() => {
      setFaceIdx(index);
      setFading(false);
    }, 200);
  };

  return (
    <div className="flex w-full flex-col gap-6">
      <div className="relative">
        <button
          type="button"
          aria-label={`Open ${face.name} edition`}
          onClick={() => setLightboxOpen(true)}
          className={cn(
            "relative block w-full overflow-hidden rounded-2xl shadow-[0_16px_48px_rgba(26,26,26,0.1)]",
            "transition-[opacity,transform] duration-300 ease-out",
            fading ? "scale-[0.99] opacity-70" : "scale-100 opacity-100",
          )}
        >
          <div className="relative aspect-[620/877] w-full bg-[#eceae4]">
            {EDITION_FACES.map((edition, index) => (
              <Image
                key={edition.id}
                src={edition.image}
                alt={`${edition.name} edition`}
                fill
                priority={index === 0}
                sizes="(max-width: 768px) 92vw, 420px"
                className={cn(
                  "object-cover object-top transition-opacity duration-300 ease-out",
                  index === faceIdx ? "opacity-100" : "opacity-0",
                )}
              />
            ))}
          </div>
        </button>

        <div
          className="absolute inset-x-0 bottom-4 flex justify-center px-4"
          role="tablist"
          aria-label="Edition layout"
        >
          <div className="inline-flex rounded-full border border-white/50 bg-white/30 p-1 shadow-[0_8px_32px_rgba(26,26,26,0.12)] backdrop-blur-xl">
            {EDITION_FACES.map((edition, index) => (
              <button
                key={edition.id}
                type="button"
                role="tab"
                aria-selected={index === faceIdx}
                onClick={() => pickFace(index)}
                className={cn(
                  "rounded-full px-4 py-2 text-[13px] font-medium transition-all duration-300",
                  index === faceIdx
                    ? "bg-white/70 text-foreground shadow-[0_2px_12px_rgba(26,26,26,0.1)] backdrop-blur-md"
                    : "text-foreground/55",
                )}
              >
                {edition.name}
              </button>
            ))}
          </div>
        </div>
      </div>

      <p
        className={cn(
          "text-left text-sm font-light leading-relaxed text-pretty text-muted-foreground",
          "transition-opacity duration-300",
          fading ? "opacity-0" : "opacity-100",
        )}
      >
        {face.description}
      </p>

      <div className="flex flex-col items-start gap-3 pt-2">
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

      <EditionLightbox
        image={face.image}
        open={lightboxOpen}
        title={face.name}
        onClose={() => setLightboxOpen(false)}
      />
    </div>
  );
}
