import { CONTENT_WIDE, FACT_ITEMS, ROW_BORDER, SECTION_PAD } from "@/lib/site";
import { cn } from "@/lib/utils";

export function FactsSection() {
  return (
    <section className={SECTION_PAD}>
      <div className={CONTENT_WIDE}>
        <h2 className="mb-12 font-serif text-[clamp(2.5rem,5vw,4rem)] font-normal tracking-tight">
          Facts.
        </h2>

        <div className="flex flex-col">
          {FACT_ITEMS.map((item) => (
            <div
              key={item.value}
              className={cn(
                ROW_BORDER,
                "group flex items-baseline justify-between gap-8 py-10",
              )}
            >
              <span className="font-serif text-[clamp(3rem,8vw,5rem)] font-normal leading-none tracking-tight transition-transform duration-300 group-hover:translate-x-2.5">
                {item.value}
              </span>
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
