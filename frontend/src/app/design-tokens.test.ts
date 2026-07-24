import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

const globals = readFileSync(resolve(process.cwd(), "src/app/globals.css"), "utf8");
const layout = readFileSync(resolve(process.cwd(), "src/app/layout.tsx"), "utf8");

describe("M5a design tokens", () => {
  it("registers the semantic Pencil palette and reusable utilities", () => {
    expect(globals).toContain("--background: oklch(0.9767 0.0026 286.35)");
    expect(globals).toContain("--primary: oklch(0.6082 0.2141 276.21)");
    expect(globals).toContain("--success: oklch(0.8120 0.2310 136.53)");
    expect(globals).toContain("--destructive: oklch(0.6724 0.2151 26.15)");
    expect(globals).toContain("--color-success: var(--success)");
    expect(globals).toContain("--shadow-card:");
    expect(globals).toContain("--radius-full:");
  });

  it("loads Inter as the application sans and heading font", () => {
    expect(layout).toContain('import { Geist_Mono, Inter } from "next/font/google"');
    expect(layout).toContain('variable: "--font-inter"');
    expect(globals).toContain("--font-sans: var(--font-inter)");
    expect(globals).toContain("--font-heading: var(--font-inter)");
  });
});

it("registers the runtime card shadow and Pencil ink alpha semantics", () => {
  expect(globals).toContain("--shadow-card: var(--shadow-card-value)");
  expect(globals).toContain("--shadow-card-value: 0 2px 6px oklch(0.2960 0.0443 274.39 / 0.14)");
  expect(globals).toContain("--border: oklch(0.2960 0.0443 274.39 / 0.12)");
});
