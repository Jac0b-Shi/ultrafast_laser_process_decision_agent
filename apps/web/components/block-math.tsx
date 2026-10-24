import katex from "katex";
import type { ReactNode } from "react";

type Props = {
  math: string;
  renderError?: (error: Error) => ReactNode;
};

export function BlockMath({ math, renderError }: Props) {
  try {
    const html = katex.renderToString(math, {
      displayMode: true,
      throwOnError: true,
      trust: false,
    });
    return <div dangerouslySetInnerHTML={{ __html: html }} />;
  } catch (error) {
    return renderError?.(error instanceof Error ? error : new Error(String(error))) ?? <code>{math}</code>;
  }
}
