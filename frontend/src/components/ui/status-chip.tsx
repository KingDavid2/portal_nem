import { cva, type VariantProps } from "class-variance-authority"; import { cn } from "@/lib/utils";
const variants=cva("inline-flex rounded-full px-2.5 py-1 text-xs font-medium",{variants:{tone:{brand:"bg-primary/15 text-primary",success:"bg-success/15 text-success",neutral:"bg-foreground/10 text-foreground/70",danger:"bg-destructive/15 text-destructive"}},defaultVariants:{tone:"neutral"}});
export function StatusChip({ tone,className,...props}:React.ComponentProps<"span">&VariantProps<typeof variants>){return <span className={cn(variants({tone}),className)} {...props}/>;}
