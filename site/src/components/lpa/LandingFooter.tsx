import { CONTENT_WIDE, LINKS } from "@/lib/site";

export function LandingFooter() {
  return (
    <footer className="border-t border-foreground/20 px-[4vw] py-10">
      <div
        className={`${CONTENT_WIDE} flex flex-col gap-3 text-xs font-light text-muted-foreground sm:flex-row sm:items-center sm:justify-between`}
      >
        <span>MIT · Hermes Hackathon</span>
        <a
          href={LINKS.github}
          className="transition-colors hover:text-foreground"
        >
          GitHub
        </a>
      </div>
    </footer>
  );
}
