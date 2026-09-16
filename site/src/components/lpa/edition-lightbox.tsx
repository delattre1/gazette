"use client";

import { AnimatePresence, motion } from "motion/react";
import Image from "next/image";
import { useEffect } from "react";

type EditionLightboxProps = {
  open: boolean;
  title: string;
  image: string;
  onClose: () => void;
};

export function EditionLightbox({
  open,
  title,
  image,
  onClose,
}: EditionLightboxProps) {
  useEffect(() => {
    if (!open) return;
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previous;
    };
  }, [open]);

  return (
    <AnimatePresence>
      {open ? (
        <motion.div
          animate={{ opacity: 1 }}
          aria-modal="true"
          className="fixed inset-0 z-[100] flex items-center justify-center bg-background/50 p-6 backdrop-blur-md"
          exit={{ opacity: 0 }}
          initial={{ opacity: 0 }}
          role="dialog"
          transition={{ duration: 0.25, ease: [0.4, 0, 0.2, 1] }}
          onClick={onClose}
        >
          <motion.div
            animate={{ opacity: 1, scale: 1 }}
            className="relative flex max-h-[90vh] w-[min(92vw,44rem)] items-center justify-center"
            exit={{ opacity: 0, scale: 0.97 }}
            initial={{ opacity: 0, scale: 0.97 }}
            transition={{ duration: 0.35, ease: [0.76, 0, 0.24, 1] }}
            onClick={(event) => event.stopPropagation()}
          >
            <Image
              alt={title}
              className="h-auto max-h-[90vh] w-full object-contain shadow-[0_32px_80px_rgba(26,26,26,0.2)]"
              height={877}
              priority
              sizes="92vw"
              src={image}
              width={620}
            />
          </motion.div>
        </motion.div>
      ) : null}
    </AnimatePresence>
  );
}
