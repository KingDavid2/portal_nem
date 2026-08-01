import { cn } from "@/lib/utils";
import { attendanceToneClasses } from "./attendance-tones";
import type { AttendanceStatus } from "@/lib/api/attendance";

type Tone = "brand" | "success" | "neutral";

type Props = React.ComponentProps<"section"> & {
  label: string;
  value: React.ReactNode;
  caption?: string;
  icon?: React.ReactNode;
  tone?: Tone;
  attendanceTone?: AttendanceStatus;
};

export function StatCard({
  label,
  value,
  caption,
  icon,
  tone = "neutral",
  attendanceTone,
  className,
  ...props
}: Props) {
  const badge = attendanceTone
    ? attendanceToneClasses[attendanceTone].badge
    : {
        brand: "bg-primary/15 text-primary",
        success: "bg-success/15 text-success",
        neutral: "bg-foreground/10 text-foreground/70",
      }[tone];

  return (
    <section
      className={cn("rounded-[10px] bg-card p-5 shadow-card", className)}
      {...props}
    >
      <div className="flex items-center justify-between text-[15px] text-foreground/70">
        <span>{label}</span>
        {icon && (
          <span
            className={cn(
              "flex size-[38px] items-center justify-center rounded-lg",
              badge,
            )}
          >
            {icon}
          </span>
        )}
      </div>
      <strong className="mt-2 block text-2xl font-medium">{value}</strong>
      {caption && (
        <p className="mt-1 text-[13px] text-foreground/40">{caption}</p>
      )}
    </section>
  );
}
