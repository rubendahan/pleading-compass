export function reportBoundaryError(error: unknown, context: Record<string, unknown> = {}) {
  if (typeof window === "undefined") return;
  console.error(
    "Unhandled application error",
    { route: window.location.pathname, ...context },
    error,
  );
}
