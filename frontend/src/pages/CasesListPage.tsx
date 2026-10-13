import { useEffect, useState } from "react";

import { listCases } from "../api/cases";
import { architectureTitle } from "../architectures";
import { ErrorMessage } from "../components/ErrorMessage";
import { Link } from "../components/Link";
import { formatDate } from "../format";
import type { CaseSummary } from "../types";

type ListResult = { cases: CaseSummary[] } | { error: Error };

export function CasesListPage() {
  const [result, setResult] = useState<ListResult | null>(null);

  useEffect(() => {
    let cancelled = false;
    listCases().then(
      (cases) => {
        if (!cancelled) setResult({ cases });
      },
      (error: Error) => {
        if (!cancelled) setResult({ error });
      },
    );
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <section className="case-section" aria-labelledby="cases-title">
      <div className="section-kicker">Registro</div>
      <h1 id="cases-title">Casos guardados</h1>
      <p className="lead">Cada caso confirmado queda guardado con su recomendación y su cálculo.</p>

      {result === null && <p className="lead">Cargando casos...</p>}
      {result && "error" in result && <ErrorMessage message={result.error.message} />}
      {result && "cases" in result && result.cases.length === 0 && (
        <p className="empty-list">
          Aún no hay casos guardados. <Link to="/">Analiza el primero.</Link>
        </p>
      )}
      {result && "cases" in result && result.cases.length > 0 && (
        <ul className="case-list">
          {result.cases.map((item) => (
            <li key={item.id}>
              <Link className="case-item" to={`/casos/${item.id}`}>
                <span className="case-item-text">{item.business_case_excerpt}</span>
                <span className="case-item-meta">
                  <span className="case-badge">{architectureTitle(item.architecture)}</span>
                  {item.trade_off && <span className="case-badge is-warning">Ajustado</span>}
                  <time dateTime={item.created_at}>{formatDate(item.created_at)}</time>
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
