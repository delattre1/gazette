"use client";

import gsap from "gsap";
import { motion } from "motion/react";
import Image from "next/image";
import { useEffect, useRef, useState } from "react";
import { EditionLightbox } from "@/components/lpa/edition-lightbox";
import { EDITION_FACES } from "@/lib/site";
import { cn } from "@/lib/utils";

const scaleAnimation = {
  closed: {
    scale: 0,
    transition: { duration: 0.4, ease: [0.32, 0, 0.67, 0] as const },
    x: "-50%",
    y: "-50%",
  },
  enter: {
    scale: 1,
    transition: { duration: 0.4, ease: [0.76, 0, 0.24, 1] as const },
    x: "-50%",
    y: "-50%",
  },
  initial: { scale: 0, x: "-50%", y: "-50%" },
};

type ModalState = { active: boolean; index: number };
type LightboxState = { open: boolean; index: number };

export type ShowcaseItem = {
  title: string;
  description: string;
  image: string;
  color?: string;
};

const defaultItems: ShowcaseItem[] = EDITION_FACES.map((face) => ({
  title: face.name,
  description: face.description,
  image: face.image,
  color:
    face.id === "planet"
      ? "#f4f1ea"
      : face.id === "times"
        ? "#ebe6dc"
        : "#efe8d3",
}));

type ProjectShowcaseProps = {
  items?: ShowcaseItem[];
  className?: string;
};

export function ProjectShowcase({
  items = defaultItems,
  className,
}: ProjectShowcaseProps) {
  const [modal, setModal] = useState<ModalState>({ active: false, index: 0 });
  const [lightbox, setLightbox] = useState<LightboxState>({
    open: false,
    index: 0,
  });

  return (
    <section
      className={cn("relative w-full", className)}
      onMouseLeave={() => {
        if (!lightbox.open) {
          setModal((current) => ({ ...current, active: false }));
        }
      }}
    >
      <div className="flex w-full flex-col">
        {items.map((project, index) => (
          <EditionRow
            key={project.title}
            description={project.description}
            index={index}
            onOpen={() => setLightbox({ open: true, index })}
            setModal={setModal}
            title={project.title}
          />
        ))}
      </div>
      <EditionPreview hidden={lightbox.open} items={items} modal={modal} />
      <EditionLightbox
        image={items[lightbox.index]?.image ?? ""}
        open={lightbox.open}
        title={items[lightbox.index]?.title ?? ""}
        onClose={() => setLightbox((current) => ({ ...current, open: false }))}
      />
    </section>
  );
}

function EditionRow({
  title,
  description,
  index,
  setModal,
  onOpen,
}: {
  title: string;
  description: string;
  index: number;
  setModal: (state: ModalState) => void;
  onOpen: () => void;
}) {
  return (
    <div
      role="button"
      tabIndex={0}
      className="group flex w-full cursor-pointer items-start justify-between gap-10 border-t border-foreground/20 py-10 transition-all duration-200 last:border-b hover:opacity-50 md:gap-16"
      onMouseEnter={() => setModal({ active: true, index })}
      onClick={onOpen}
      onKeyDown={(event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          onOpen();
        }
      }}
    >
      <h2 className="m-0 shrink-0 font-serif text-[clamp(2.25rem,5vw,3.75rem)] font-normal tracking-tight transition-all duration-300 group-hover:translate-x-2.5">
        {title}
      </h2>
      <p className="max-w-[16rem] shrink-0 text-left text-sm font-light leading-relaxed text-pretty text-muted-foreground transition-all duration-300 sm:max-w-xs md:max-w-sm lg:max-w-md group-hover:translate-x-2.5">
        {description}
      </p>
    </div>
  );
}

function EditionPreview({
  modal,
  items,
  hidden = false,
}: {
  modal: ModalState;
  items: ShowcaseItem[];
  hidden?: boolean;
}) {
  const { active, index } = modal;
  const show = active && !hidden;
  const modalContainer = useRef<HTMLDivElement>(null);
  const cursor = useRef<HTMLDivElement>(null);
  const cursorLabel = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const container = modalContainer.current;
    const cursorEl = cursor.current;
    const labelEl = cursorLabel.current;
    if (!container || !cursorEl || !labelEl) return;

    const xMoveContainer = gsap.quickTo(container, "left", {
      duration: 0.8,
      ease: "power3",
    });
    const yMoveContainer = gsap.quickTo(container, "top", {
      duration: 0.8,
      ease: "power3",
    });
    const xMoveCursor = gsap.quickTo(cursorEl, "left", {
      duration: 0.5,
      ease: "power3",
    });
    const yMoveCursor = gsap.quickTo(cursorEl, "top", {
      duration: 0.5,
      ease: "power3",
    });
    const xMoveCursorLabel = gsap.quickTo(labelEl, "left", {
      duration: 0.45,
      ease: "power3",
    });
    const yMoveCursorLabel = gsap.quickTo(labelEl, "top", {
      duration: 0.45,
      ease: "power3",
    });

    const handleMouseMove = (event: MouseEvent) => {
      const { clientX, clientY } = event;
      xMoveContainer(clientX);
      yMoveContainer(clientY);
      xMoveCursor(clientX);
      yMoveCursor(clientY);
      xMoveCursorLabel(clientX);
      yMoveCursorLabel(clientY);
    };

    window.addEventListener("mousemove", handleMouseMove);
    return () => window.removeEventListener("mousemove", handleMouseMove);
  }, []);

  return (
    <>
      <motion.div
        ref={modalContainer}
        animate={show ? "enter" : "closed"}
        initial="initial"
        variants={scaleAnimation}
        className="pointer-events-none fixed z-50 flex aspect-[620/877] w-[min(28rem,45vw)] items-center justify-center overflow-hidden bg-background shadow-[0_24px_80px_rgba(26,26,26,0.14)]"
      >
        <div
          className="absolute h-full w-full transition-[top] duration-500 ease-[cubic-bezier(0.76,0,0.24,1)]"
          style={{ top: `${index * -100}%` }}
        >
          {items.map((project) => (
            <div
              key={project.title}
              className="flex h-full w-full items-center justify-center p-5"
              style={{ backgroundColor: project.color }}
            >
              <Image
                alt={project.title}
                className="h-full w-full object-contain object-top shadow-sm"
                height={877}
                src={project.image}
                width={620}
              />
            </div>
          ))}
        </div>
      </motion.div>

      <motion.div
        ref={cursor}
        animate={show ? "enter" : "closed"}
        initial="initial"
        variants={scaleAnimation}
        className="pointer-events-none fixed z-[51] flex h-20 w-20 items-center justify-center rounded-full bg-foreground"
      />

      <motion.div
        ref={cursorLabel}
        animate={show ? "enter" : "closed"}
        initial="initial"
        variants={scaleAnimation}
        className="pointer-events-none fixed z-[52] flex h-20 w-20 items-center justify-center rounded-full bg-transparent text-sm font-light text-background"
      >
        View
      </motion.div>
    </>
  );
}
