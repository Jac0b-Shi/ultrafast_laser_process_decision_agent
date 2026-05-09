export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });

  if (!response.ok) {
    const body = await response.text();
    if (body) {
      let parsed: { detail?: unknown } | null = null;
      try {
        parsed = JSON.parse(body) as { detail?: unknown };
      } catch {
        parsed = null;
      }
      if (typeof parsed?.detail === "string") {
        throw new Error(parsed.detail);
      }
      if (
        parsed?.detail &&
        typeof parsed.detail === "object" &&
        "message" in parsed.detail &&
        typeof parsed.detail.message === "string"
      ) {
        throw new Error(parsed.detail.message);
      }
    }
    throw new Error(body || `HTTP ${response.status}`);
  }

  return response.json() as Promise<T>;
}
