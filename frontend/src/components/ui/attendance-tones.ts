import type { AttendanceStatus } from "@/lib/api/attendance";

/** LXprh frame tokens for P/A/R/J attendance controls. */
export const ATTENDANCE_TONE_COLORS: Record<AttendanceStatus, string> = {
  present: "#72E128",
  absent: "#FF4D49",
  late: "#FDB528",
  excused: "#26C6F9",
};

export const attendanceToneClasses: Record<
  AttendanceStatus,
  { selected: string; badge: string }
> = {
  present: {
    selected: "bg-[#72E128]/15 text-[#72E128]",
    badge: "bg-[#72E128]/15 text-[#72E128]",
  },
  absent: {
    selected: "bg-[#FF4D49]/15 text-[#FF4D49]",
    badge: "bg-[#FF4D49]/15 text-[#FF4D49]",
  },
  late: {
    selected: "bg-[#FDB528]/15 text-[#FDB528]",
    badge: "bg-[#FDB528]/15 text-[#FDB528]",
  },
  excused: {
    selected: "bg-[#26C6F9]/15 text-[#26C6F9]",
    badge: "bg-[#26C6F9]/15 text-[#26C6F9]",
  },
};
