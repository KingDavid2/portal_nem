import { renderToStaticMarkup } from "react-dom/server";
import { House } from "lucide-react";
import { describe, expect, it } from "vitest";
import { NavItem } from "./nav-item";

describe("NavItem", () => {
  it("renders its accessible label and active navigation state", () => {
    const html = renderToStaticMarkup(<NavItem href="/schools" label="Escuelas" icon={House} active className="extra" prefetch={false} />);
    expect(html).toContain("Escuelas");
    expect(html).toContain('aria-current="page"'); expect(html).toContain("extra"); expect(html).toContain("bg-primary"); expect(html).toContain("text-primary-foreground"); expect(html).toContain("shadow-card");
  });
});
