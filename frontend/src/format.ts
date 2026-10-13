const DATE_FORMAT = new Intl.DateTimeFormat("es-CO", { dateStyle: "medium", timeStyle: "short" });

export function formatDate(isoDate: string): string {
  const date = new Date(isoDate);
  return Number.isNaN(date.getTime()) ? isoDate : DATE_FORMAT.format(date);
}

export function formatPercent(weight: number): string {
  return `${(weight * 100).toLocaleString("es-CO", { maximumFractionDigits: 1 })} %`;
}

export function formatScore(value: number): string {
  return value.toLocaleString("es-CO", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}
