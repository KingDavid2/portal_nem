"use client";

import { defineElement } from "@lordicon/element";

/** Brand primary (`--primary` ≈ #666cff) + soft lavender companion. */
const BRAND_COLORS = "primary:#666cff,secondary:#a39cf4";

if (typeof window !== "undefined" && !customElements.get("lord-icon")) {
  defineElement();
}

type MagicWandIconProps = {
  size?: number;
  className?: string;
};

/**
 * Lordicon wired-outline magic wand — light stroke, brand colors,
 * hover-pinch state with loop trigger.
 * @see https://lordicon.com/icons/wired/outline/2844-magic-wand
 */
export function MagicWandIcon({ size = 64, className }: MagicWandIconProps) {
  return (
    <span
      className={className}
      style={{ width: size, height: size, display: "inline-flex" }}
      aria-hidden
    >
      <lord-icon
        src="/quizzy/magic-wand.json"
        trigger="loop"
        state="hover-pinch"
        stroke="light"
        colors={BRAND_COLORS}
        style={{ width: "100%", height: "100%" }}
      />
    </span>
  );
}
