declare module "react-katex" {
  import type { ReactElement, ReactNode } from "react";

  export type MathComponentProps = {
    children?: ReactNode;
    errorColor?: string;
    math?: string;
    renderError?: (error: Error) => ReactNode;
  };

  export function InlineMath(props: MathComponentProps): ReactElement;
  export function BlockMath(props: MathComponentProps): ReactElement;
}
