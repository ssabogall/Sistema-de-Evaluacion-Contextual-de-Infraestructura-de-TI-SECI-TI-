import { useSyncExternalStore } from "react";

// Router mínimo basado en la History API: el proyecto solo necesita tres rutas, así que no
// hace falta una dependencia. Si crece, se puede cambiar por react-router sin tocar las páginas
// (solo usan usePathname, navigate y Link).
const NAVIGATE_EVENT = "seci:navigate";

function subscribe(onChange: () => void): () => void {
  window.addEventListener("popstate", onChange);
  window.addEventListener(NAVIGATE_EVENT, onChange);
  return () => {
    window.removeEventListener("popstate", onChange);
    window.removeEventListener(NAVIGATE_EVENT, onChange);
  };
}

export function usePathname(): string {
  return useSyncExternalStore(
    subscribe,
    () => window.location.pathname,
    () => "/",
  );
}

export function navigate(to: string): void {
  if (to === window.location.pathname) return;
  window.history.pushState({}, "", to);
  window.dispatchEvent(new Event(NAVIGATE_EVENT));
}

export function matchCasePath(pathname: string): string | null {
  const match = /^\/casos\/([^/]+)\/?$/.exec(pathname);
  return match ? decodeURIComponent(match[1]) : null;
}

export function isCasesListPath(pathname: string): boolean {
  return /^\/casos\/?$/.test(pathname);
}
