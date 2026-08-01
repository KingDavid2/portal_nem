import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { MarkdownContent } from "./markdown-content";

describe("MarkdownContent", () => {
  it("renders bold text as strong", () => {
    const html = renderToStaticMarkup(
      <MarkdownContent>Hola **mundo**</MarkdownContent>,
    );
    expect(html).toContain("<strong");
    expect(html).toContain("mundo");
  });

  it("renders a list from markdown bullets", () => {
    const html = renderToStaticMarkup(
      <MarkdownContent>{"- uno\n- dos"}</MarkdownContent>,
    );
    expect(html).toContain("<ul");
    expect(html).toContain("<li");
    expect(html).toContain("uno");
    expect(html).toContain("dos");
  });

  it("renders links with safe target and rel", () => {
    const html = renderToStaticMarkup(
      <MarkdownContent>[SEP](https://www.gob.mx/sep)</MarkdownContent>,
    );
    expect(html).toContain('href="https://www.gob.mx/sep"');
    expect(html).toContain('target="_blank"');
    expect(html).toContain('rel="noopener noreferrer"');
    expect(html).toContain("SEP");
  });
});
