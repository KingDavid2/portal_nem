import { Button } from "./button";
import { cn } from "@/lib/utils";
import { attendanceToneClasses } from "./attendance-tones";
import type { AttendanceStatus } from "@/lib/api/attendance";

type Props = React.ComponentProps<typeof Button> & {
  selected?: boolean;
  attendanceTone?: AttendanceStatus;
};

export function EstadoButton({
  selected = false,
  attendanceTone,
  className,
  ...props
}: Props) {
  const toneClasses = attendanceTone
    ? attendanceToneClasses[attendanceTone]
    : null;

  return (
    <Button
      aria-pressed={selected}
      variant="ghost"
      size="icon"
      className={cn(
        "size-[34px] rounded-md text-sm text-foreground/70",
        selected && toneClasses
          ? toneClasses.selected
          : selected
            ? "bg-primary/15 text-primary"
            : "bg-foreground/5 hover:bg-foreground/10",
        className,
      )}
      {...props}
    />
  );
}
