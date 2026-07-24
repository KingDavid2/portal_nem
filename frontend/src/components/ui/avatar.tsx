import { cn } from "@/lib/utils";
type Props = React.ComponentProps<"span"> & { name: string; size?: "sm" | "md" };
export function Avatar({ name, size = "md", className, ...props }: Props) { const initials=name.split(/\s+/).map((part)=>part[0]).join("").slice(0,2).toUpperCase(); return <span aria-label={name} className={cn("inline-flex items-center justify-center rounded-full bg-primary/15 font-medium text-primary",size === "sm" ? "size-7 text-xs" : "size-[38px] text-sm",className)} {...props}>{initials}</span>; }
