import { Link } from "./components/Link";
import { AnalyzePage } from "./pages/AnalyzePage";
import { CasePage } from "./pages/CasePage";
import { CasesListPage } from "./pages/CasesListPage";
import { isCasesListPath, matchCasePath, usePathname } from "./router";

function App() {
  const pathname = usePathname();
  const caseId = matchCasePath(pathname);

  let page;
  if (caseId !== null) {
    page = <CasePage key={caseId} caseId={caseId} />;
  } else if (isCasesListPath(pathname)) {
    page = <CasesListPage />;
  } else if (pathname === "/") {
    page = <AnalyzePage />;
  } else {
    page = (
      <section className="entry-section">
        <h1>Página no encontrada</h1>
        <Link className="primary-button" to="/">
          Ir al inicio
        </Link>
      </section>
    );
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand-mark" aria-hidden="true">
          S
        </div>
        <div>
          <strong>SECI-TI</strong>
          <span>Evaluación contextual de infraestructura</span>
        </div>
        <nav className="topbar-nav" aria-label="Principal">
          <Link to="/">Nuevo caso</Link>
          <Link to="/casos">Casos guardados</Link>
        </nav>
      </header>

      <main>{page}</main>
    </div>
  );
}

export default App;
