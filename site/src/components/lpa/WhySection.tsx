import {
  CONTENT_WIDE,
  LINKS,
  ROW_BORDER,
  SECTION_PAD,
  WHY_ITEMS,
} from "@/lib/site";
import { cn } from "@/lib/utils";

export function WhySection() {
  return (
    <section className={SECTION_PAD}>
      <div className={CONTENT_WIDE}>
        <div className="mb-12 flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
          <h2 className="font-serif text-[clamp(2.5rem,5vw,4rem)] font-normal tracking-tight">
            Why.
          </h2>
          <p className="max-w-2xl text-sm font-light leading-relaxed text-pretty text-muted-foreground lg:max-w-xl lg:text-right">
            Inspired by{" "}
            <a
              href={LINKS.karen}
              className="text-foreground/80 underline decoration-foreground/20 underline-offset-[3px] transition-colors hover:text-foreground hover:decoration-foreground/50"
            >
              Karen X. Cheng&apos;s morning newspaper
            </a>
            . Installable, open source, on the Agent Index.
          </p>
        </div>

        <div className="flex flex-col">
          {WHY_ITEMS.map((item) => (
            <div
              key={item.title}
              className={cn(
                ROW_BORDER,
                "group flex flex-col gap-3 py-10 md:flex-row md:items-baseline md:justify-between md:gap-12",
              )}
            >
              <h3 className="shrink-0 font-serif text-[clamp(1.75rem,3vw,2.25rem)] font-normal tracking-tight transition-transform duration-300 group-hover:translate-x-2.5">
                {item.title}
              </h3>
              <p className="max-w-sm shrink-0 text-left text-sm font-light leading-relaxed text-pretty text-muted-foreground transition-transform duration-300 sm:max-w-xs md:max-w-sm lg:max-w-md group-hover:translate-x-2.5">
                {item.body}
              </p>
            </div>
          ))}
          <div className="border-t border-foreground/20" />
        </div>
      </div>
    </section>
  );
}
