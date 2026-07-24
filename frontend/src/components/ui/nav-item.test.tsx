import { renderToStaticMarkup } from "react-dom/server";
import { House } from "lucide-react";
import { describe, expect, it } from "vitest";
import { NavItem } from "./nav-item";

describe("NavItem", () => {
  it("keeps the active Pencil state primary on hover", () => {
    const html = renderToStaticMarkup(<NavItem href="/schools" label="Escuelas" icon={House} active className="extra" prefetch={false} />);
    expect(html).toContain('aria-current="page"'); expect(html).toContain("bg-primary"); expect(html).toContain("hover:bg-primary"); expect(html).toContain("hover:text-primary-foreground");
  });
  it("keeps inactive items accent-hover only", () => {
    const html = renderToStaticMarkup(<NavItem href="/schools" label="Escuelas" icon={House} />);
    expect(html).not.toContain("aria-current"); expect(html).not.toContain("shadow-card"); expect(html).not.toContain("hover:bg-primary"); expect(html).toContain("hover:bg-sidebar-accent");
  });
});
