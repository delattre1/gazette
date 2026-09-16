export type EditionFace = {
  id: "planet" | "times" | "herald";
  name: string;
  description: string;
  image: string;
};

export const EDITION_FACES: EditionFace[] = [
  {
    id: "planet",
    name: "Planet",
    description:
      "Color by default. A photograph in the center, type on both sides.",
    image: "/editions/planet.png",
  },
  {
    id: "times",
    name: "Times",
    description: "Black and white broadsheet. Lead photo up top, even columns.",
    image: "/editions/times.png",
  },
  {
    id: "herald",
    name: "Herald",
    description: "1912 cafe paper. Walnut ink, always sepia.",
    image: "/editions/herald.png",
  },
];

export const INSTALL_COMMANDS = [
  "git clone https://github.com/plow-pbc/plow-agents.git",
  'export PATH="$PWD/plow-agents/bin:$PATH"',
  "plow-agents login --new-line",
  "git clone https://github.com/MAUXII/gazette.git",
  "cd gazette && plow-agents mint ln_xxx",
  "docker compose up --build -d",
] as const;

export const LINKS = {
  site: "https://get-gazette.vercel.app",
  github: "https://github.com/MAUXII/gazette",
  index: "https://aiworthusing.com/agent-index/gazette",
  karen: "https://x.com/karenxcheng/status/2097383854923538770",
} as const;

/** Max content width (iPhone-minimal column) */
export const SHELL_CLASS = "mx-auto w-full max-w-[26.25rem] px-5";

/** Shared landing layout */
export const SECTION_PAD = "px-[4vw] py-[clamp(4.5rem,12vh,6rem)]";
export const CONTENT_WIDE = "mx-auto w-full max-w-4xl";
export const ROW_BORDER =
  "border-t border-foreground/20 transition-all duration-200 hover:opacity-50";

export type ManifestoStatement = {
  lines: readonly string[];
};

/** Scroll-reveal manifesto blocks */
export const GRADIENT_STATEMENTS: ManifestoStatement[] = [
  { lines: ["One page instead", "of five apps."] },
  { lines: ["A real front page → headline, columns, photograph."] },
  { lines: ["Written while you sleep.", "Delivered as a photo on your phone."] },
];

export const WHY_ITEMS = [
  {
    title: "Cron",
    body: "Runs while you sleep. Tokens report even if you never reply.",
  },
  {
    title: "Plow",
    body: "Your own phone line. No model API keys on your machine.",
  },
  {
    title: "Share",
    body: "Every edition is a PNG worth posting on X or Discord.",
  },
] as const;

export const FACT_ITEMS = [
  { value: "3", body: "Templates. Planet ships first, in color." },
  { value: "0", body: "Model API keys on your machine." },
  { value: "1", body: "Message per day. No noise." },
] as const;
