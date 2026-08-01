import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { EstadoButton } from "./estado-button";
import { StatCard } from "./stat-card";
import {
  ATTENDANCE_TONE_COLORS,
  attendanceToneClasses,
} from "./attendance-tones";

describe("attendance tone tokens", () => {
  it("maps P/A/R/J to LXprh hex colors", () => {
    expect(ATTENDANCE_TONE_COLORS.present).toBe("#72E128");
    expect(ATTENDANCE_TONE_COLORS.absent).toBe("#FF4D49");
    expect(ATTENDANCE_TONE_COLORS.late).toBe("#FDB528");
    expect(ATTENDANCE_TONE_COLORS.excused).toBe("#26C6F9");
  });

  it("applies attendance tone classes on EstadoButton when selected", () => {
    const html = renderToStaticMarkup(
      <>
        <EstadoButton attendanceTone="present" selected>
          P
        </EstadoButton>
        <EstadoButton attendanceTone="absent" selected>
          A
        </EstadoButton>
        <EstadoButton attendanceTone="late" selected>
          R
        </EstadoButton>
        <EstadoButton attendanceTone="excused" selected>
          J
        </EstadoButton>
      </>,
    );
    expect(html).toContain(attendanceToneClasses.present.selected);
    expect(html).toContain(attendanceToneClasses.absent.selected);
    expect(html).toContain(attendanceToneClasses.late.selected);
    expect(html).toContain(attendanceToneClasses.excused.selected);
  });

  it("applies attendance tone classes on StatCard badges", () => {
    const html = renderToStaticMarkup(
      <>
        <StatCard label="Presentes" value="3" attendanceTone="present" icon={<span />} />
        <StatCard label="Ausentes" value="1" attendanceTone="absent" icon={<span />} />
        <StatCard label="Retardos" value="2" attendanceTone="late" icon={<span />} />
        <StatCard label="Justificados" value="0" attendanceTone="excused" icon={<span />} />
      </>,
    );
    expect(html).toContain(attendanceToneClasses.present.badge);
    expect(html).toContain(attendanceToneClasses.absent.badge);
    expect(html).toContain(attendanceToneClasses.late.badge);
    expect(html).toContain(attendanceToneClasses.excused.badge);
  });
});
