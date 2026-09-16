import { LINKS, SHELL_CLASS } from "@/lib/site";
import { cn } from "@/lib/utils";

export function LandingNav() {
  return (
    <header className="fixed inset-x-0 top-0 z-50">
      <div
        className={cn(
          SHELL_CLASS,
          "flex h-16 max-w-none items-center justify-between px-[4vw]",
        )}
      >
        <span className="font-serif text-lg tracking-wide text-foreground">
          Gazette
        </span>
        <a
          href={LINKS.github}
          className="text-sm text-muted-foreground transition-colors hover:text-foreground"
        >
          GitHub
        </a>
      </div>
    </header>
  );
}
