import { Check, Plus } from "lucide-react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const choiceChipVariants = cva(
  "inline-flex w-fit items-center gap-2 rounded-full border px-4 py-2 text-[13px] font-medium transition-colors outline-none focus-visible:ring-3 focus-visible:ring-ring/50 disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:shrink-0",
  {
    variants: {
      variant: { single: "", multi: "" },
      selected: { true: "", false: "bg-foreground/5 text-foreground/80" },
    },
    compoundVariants: [
      { variant: "single", selected: false, class: "border-foreground/20" },
      { variant: "single", selected: true, class: "border-transparent bg-primary text-primary-foreground" },
      { variant: "multi", selected: false, class: "border-foreground/15" },
      { variant: "multi", selected: true, class: "border-primary bg-primary/15 text-primary" },
    ],
    defaultVariants: { variant: "single", selected: false },
  },
);

/** Pill-shaped toggle used by the planeaciones selection steps.
 *
 * `onSelectedChange` always reports the *toggled* value, so a `single` chip that
 * is already selected reports `false`. Mutually exclusive groups (Escenario)
 * ignore the argument and set their own id; the primitive owns no group and
 * therefore cannot enforce "one always selected" itself.
 *
 * For the same reason it exposes `aria-pressed` (toggle button) rather than
 * `role="radio"`, which is only valid inside an owning `radiogroup`. A call site
 * that does own the group can pass `role`/`aria-checked` through — the prop
 * spread lands after these defaults and overrides them. */
type ChoiceChipProps = Omit<React.ComponentProps<"button">, "type"> & {
  variant?: NonNullable<VariantProps<typeof choiceChipVariants>["variant"]>;
  selected?: boolean;
  onSelectedChange?: (selected: boolean) => void;
};

export function ChoiceChip({ variant = "single", selected = false, onSelectedChange, onClick, className, children, ...props }: ChoiceChipProps) {
  const Icon = selected ? Check : Plus;
  return (
    <button
      type="button"
      aria-pressed={selected}
      className={cn(choiceChipVariants({ variant, selected }), className)}
      onClick={(event) => {
        onClick?.(event);
        onSelectedChange?.(!selected);
      }}
      {...props}
    >
      {variant === "multi" && <Icon aria-hidden className={cn("size-3.5", selected ? "text-primary" : "text-foreground/60")} />}
      {children}
    </button>
  );
}

export { choiceChipVariants };
