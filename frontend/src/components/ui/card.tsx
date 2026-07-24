import { cn } from "@/lib/utils";
export function Card({ className, ...props }: React.ComponentProps<"section">) { return <section className={cn("rounded-xl bg-card p-5 text-card-foreground shadow-card", className)} {...props} />; }
