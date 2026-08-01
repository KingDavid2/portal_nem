import type { CSSProperties } from "react";

type LordIconElement = React.DetailedHTMLProps<
  React.HTMLAttributes<HTMLElement>,
  HTMLElement
> & {
  src?: string;
  trigger?:
    | "in"
    | "click"
    | "hover"
    | "loop"
    | "loop-on-hover"
    | "morph"
    | "boomerang"
    | "sequence";
  state?: string;
  stroke?: "light" | "regular" | "bold" | string;
  colors?: string;
  target?: string;
  loading?: "lazy" | "interaction" | "delay";
  style?: CSSProperties;
};

declare module "react" {
  // eslint-disable-next-line @typescript-eslint/no-namespace
  namespace JSX {
    interface IntrinsicElements {
      "lord-icon": LordIconElement;
    }
  }
}

export {};
