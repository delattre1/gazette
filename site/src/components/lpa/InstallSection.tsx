"use client";

import { useState } from "react";
import {
  CONTENT_WIDE,
  INSTALL_COMMANDS,
  LINKS,
  SECTION_PAD,
} from "@/lib/site";

export function InstallSection() {
  const [copied, setCopied] = useState(false);
  const commandText = INSTALL_COMMANDS.join("\n");

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(commandText);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      setCopied(false);
    }
  };

  return (
    <section id="install" className={SECTION_PAD}>
      <div className={CONTENT_WIDE}>
        <div className="mb-12 flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
          <h2 className="font-serif text-[clamp(2.5rem,5vw,4rem)] font-normal tracking-tight">
            Install.
          </h2>
          <p className="max-w-2xl text-sm font-light leading-relaxed text-pretty text-muted-foreground lg:max-w-xl lg:text-right">
            About ten minutes. Docker and a Plow account: one container, one
            phone line.
          </p>
        </div>

        <div className="overflow-x-auto rounded-2xl bg-secondary/80 p-5 md:p-6">
          <pre className="m-0 font-mono text-[0.6875rem] leading-[1.65] tracking-tight text-foreground md:text-xs">
            {INSTALL_COMMANDS.map((line) => (
              <span key={line} className="block">
                {line}
              </span>
            ))}
          </pre>
        </div>

        <button
          type="button"
          onClick={copy}
          className="mt-4 text-[15px] text-link transition-opacity hover:opacity-80"
        >
          {copied ? "Copied" : "Copy commands"}
        </button>

        <p className="mt-8 max-w-lg text-sm font-light leading-relaxed text-muted-foreground">
          Text <strong className="font-medium text-foreground">hi</strong> to
          your new line. City, topics, delivery time in one reply.
        </p>

        <div className="mt-10 flex flex-col gap-3 border-t border-foreground/20 pt-10 text-[15px]">
          <a
            href={LINKS.site}
            className="w-fit text-link transition-opacity hover:opacity-80"
          >
            get-gazette.vercel.app
          </a>
          <a
            href={LINKS.github}
            className="w-fit text-link transition-opacity hover:opacity-80"
          >
            Repository
          </a>
          <a
            href={LINKS.index}
            className="w-fit text-link transition-opacity hover:opacity-80"
          >
            Leaderboard
          </a>
          <a
            href={LINKS.karen}
            className="w-fit text-muted-foreground transition-colors hover:text-foreground"
          >
            Inspired by Karen X. Cheng
          </a>
        </div>
      </div>
    </section>
  );
}
