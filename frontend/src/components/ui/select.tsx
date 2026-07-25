import * as React from "react"

import { cn } from "@/lib/utils"

/** Native `<select>` primitive. Deliberately native (not a headless listbox):
 * every call site relies on native `<option>` children, keyboard behaviour and
 * `onChange` events.
 *
 * Geometry (`h-10`, `rounded-md`, `px-3`, `text-sm`, `bg-card`) is pinned to the
 * Pencil design for the planeaciones screens — ~40px boxes at radius 6 — which
 * is intentionally NOT `Input`'s `h-8`/`rounded-lg`. The focus, disabled and
 * `aria-invalid` treatments below are borrowed from `input.tsx` because they
 * only apply outside the resting state. `input.tsx`'s
 * `disabled:pointer-events-none` is deliberately NOT adopted: the planeaciones
 * filters go disabled while the school/year/group cascade resolves, and
 * suppressing pointer events would also suppress `cursor-not-allowed`. */
function Select({ className, ...props }: React.ComponentProps<"select">) {
  return (
    <select
      data-slot="select"
      className={cn(
        "h-10 w-full min-w-0 rounded-md border border-input bg-card px-3 text-sm transition-colors outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 disabled:cursor-not-allowed disabled:opacity-50 aria-invalid:border-destructive aria-invalid:ring-3 aria-invalid:ring-destructive/20 dark:aria-invalid:border-destructive/50 dark:aria-invalid:ring-destructive/40",
        className
      )}
      {...props}
    />
  )
}

export { Select }
