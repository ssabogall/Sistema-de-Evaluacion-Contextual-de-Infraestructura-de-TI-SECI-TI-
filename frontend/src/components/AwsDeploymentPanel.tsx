import { useCallback, useEffect, useId, useRef, useState } from "react";
import { Cloud, ExternalLink, RefreshCw, Rocket, Trash2 } from "lucide-react";

import {
  createCaseDeployment,
  deleteCaseDeployment,
  getAwsConnection,
  getCaseDeployment,
} from "../api/aws";
import { architectureTitle } from "../architectures";
import { formatDate } from "../format";
import type { AwsConnection, AwsDeployment } from "../types";
import { ErrorMessage } from "./ErrorMessage";

type Operation = "refresh" | "create" | "delete";
type Session = { active: boolean; inFlight: boolean; controller: AbortController | null };

function inProgress(status: string): boolean {
  return status.endsWith("_IN_PROGRESS");
}

function safeApplicationUrl(value: string | undefined): string | null {
  if (!value) return null;
  try {
    const url = new URL(value);
    return ["http:", "https:"].includes(url.protocol) && !url.username && !url.password
      ? url.href
      : null;
  } catch {
    return null;
  }
}

export function AwsDeploymentPanel({ caseId }: { caseId: string }) {
  // Cada caso tiene su propio ciclo de peticiones, incluso si el padre reutiliza el panel.
  return <DeploymentSession key={caseId} caseId={caseId} />;
}

function DeploymentSession({ caseId }: { caseId: string }) {
  const headingId = useId();
  const dialogId = useId();
  const [connection, setConnection] = useState<AwsConnection | null>(null);
  const [deployment, setDeployment] = useState<AwsDeployment | null>(null);
  const [operation, setOperation] = useState<Operation | null>("refresh");
  const [error, setError] = useState<string | null>(null);
  const [confirmation, setConfirmation] = useState<"create" | "delete" | null>(null);
  const sessionRef = useRef<Session>({ active: false, inFlight: false, controller: null });
  const createButton = useRef<HTMLButtonElement>(null);
  const deleteButton = useRef<HTMLButtonElement>(null);

  const execute = useCallback(
    (action: Operation) => {
      const session = sessionRef.current;
      if (!session.active || session.inFlight) return;
      session.inFlight = true;
      const controller = new AbortController();
      session.controller = controller;
      const request =
        action === "refresh"
          ? getAwsConnection(controller.signal).then((nextConnection) => {
              if (!session.active) return null;
              setConnection(nextConnection);
              return nextConnection.status === "connected"
                ? getCaseDeployment(caseId, controller.signal)
                : null;
            })
          : action === "create"
            ? createCaseDeployment(caseId, controller.signal)
            : deleteCaseDeployment(caseId, controller.signal);

      void request
        .then(
          (nextDeployment) => {
            if (session.active) setDeployment(nextDeployment);
          },
          (cause: unknown) => {
            if (session.active) {
              setError(cause instanceof Error ? cause.message : "No fue posible consultar AWS.");
            }
          },
        )
        .finally(() => {
          session.inFlight = false;
          session.controller = null;
          if (session.active) setOperation(null);
        });
    },
    [caseId],
  );

  const startOperation = useCallback(
    (action: Operation) => {
      if (!sessionRef.current.active || sessionRef.current.inFlight) return;
      setOperation(action);
      setError(null);
      void execute(action);
    },
    [execute],
  );

  useEffect(() => {
    const session: Session = { active: true, inFlight: false, controller: null };
    sessionRef.current = session;
    void execute("refresh");
    return () => {
      session.active = false;
      session.controller?.abort();
    };
  }, [execute]);

  const status = deployment?.status;
  const pending = status !== undefined && inProgress(status);
  const absent = status === "NOT_DEPLOYED" || status === "DELETE_COMPLETE";
  const failed = status !== undefined && (status.includes("FAILED") || status.includes("ROLLBACK"));
  const available =
    connection?.status === "connected" &&
    connection.deployments_enabled &&
    deployment !== null &&
    operation === null &&
    error === null &&
    !pending;
  const canCreate = available && absent;
  const canDelete = available && !absent;

  useEffect(() => {
    if (!pending || operation !== null || confirmation !== null) return;
    const timer = window.setTimeout(() => startOperation("refresh"), 10_000);
    return () => window.clearTimeout(timer);
  }, [pending, operation, confirmation, startOperation]);

  function closeConfirmation() {
    setConfirmation(null);
    (confirmation === "create" ? createButton : deleteButton).current?.focus();
  }

  function confirmOperation() {
    if (confirmation === "create" && canCreate) {
      closeConfirmation();
      startOperation("create");
    } else if (confirmation === "delete" && canDelete) {
      closeConfirmation();
      startOperation("delete");
    }
  }

  const applicationUrl = absent ? null : safeApplicationUrl(deployment?.outputs.ApplicationUrl);
  const events = [...(deployment?.events ?? [])]
    .sort((a, b) => (Date.parse(b.timestamp) || 0) - (Date.parse(a.timestamp) || 0))
    .slice(0, 10);

  return (
    <section className="aws-panel" aria-labelledby={headingId} aria-busy={operation !== null}>
      <div className="aws-heading">
        <h2 id={headingId}>
          <Cloud size={18} aria-hidden="true" />
          Estado del despliegue
        </h2>
        <button
          className="aws-icon-button"
          type="button"
          title="Refrescar estado AWS"
          aria-label="Refrescar estado AWS"
          disabled={operation !== null || confirmation !== null}
          onClick={() => startOperation("refresh")}
        >
          <RefreshCw
            size={18}
            className={operation === "refresh" ? "spin" : undefined}
            aria-hidden="true"
          />
        </button>
      </div>

      <dl className="aws-meta">
        <div>
          <dt>Conexión</dt>
          <dd>
            {connection
              ? connection.status === "connected"
                ? "Conectada"
                : "Deshabilitada"
              : "Sin verificar"}
          </dd>
        </div>
        <div>
          <dt>Cuenta AWS</dt>
          <dd>{connection?.account_id ?? "No disponible"}</dd>
        </div>
        <div>
          <dt>Región</dt>
          <dd>{connection?.region ?? "No disponible"}</dd>
        </div>
        {connection?.principal_arn && (
          <div className="aws-meta-wide">
            <dt>Identidad</dt>
            <dd>{connection.principal_arn}</dd>
          </div>
        )}
      </dl>
      {connection?.message && <p className="aws-message">{connection.message}</p>}
      {connection?.status === "connected" && !connection.deployments_enabled && (
        <p className="aws-message">Las operaciones de despliegue están deshabilitadas.</p>
      )}

      {deployment && (
        <>
          <div className="aws-state-row">
            <span>Estado</span>
            <code className={`aws-state${pending ? " is-pending" : failed ? " is-failed" : ""}`}>
              {deployment.status}
            </code>
          </div>
          <dl className="aws-meta">
            <div>
              <dt>Arquitectura</dt>
              <dd>{architectureTitle(deployment.architecture)}</dd>
            </div>
            <div>
              <dt>Región del stack</dt>
              <dd>{deployment.region}</dd>
            </div>
            <div>
              <dt>Nombre del stack</dt>
              <dd>{deployment.stack_name}</dd>
            </div>
            {deployment.stack_id && (
              <div className="aws-meta-wide">
                <dt>ID del stack</dt>
                <dd>{deployment.stack_id}</dd>
              </div>
            )}
          </dl>
          {deployment.last_updated_at && (
            <p className="aws-message">
              Última actualización:{" "}
              <time dateTime={deployment.last_updated_at}>
                {formatDate(deployment.last_updated_at)}
              </time>
            </p>
          )}
          {failed && !pending && (
            <p className="aws-failure-note">
              El despliegue falló o se revirtió. Elimina el stack antes de volver a desplegar.
            </p>
          )}
          {applicationUrl && (
            <a
              className="aws-application-link"
              href={applicationUrl}
              target="_blank"
              rel="noopener noreferrer"
            >
              Abrir aplicación
              <ExternalLink size={16} aria-hidden="true" />
            </a>
          )}
        </>
      )}

      {error && <ErrorMessage message={error} />}
      <p className="aws-progress" role="status">
        {operation === "refresh"
          ? "Consultando AWS..."
          : operation === "create"
            ? "Solicitando despliegue..."
            : operation === "delete"
              ? "Solicitando eliminación..."
              : pending
                ? "Operación en curso en AWS."
                : ""}
      </p>

      <div className="aws-actions">
        <button
          className="primary-button"
          type="button"
          ref={createButton}
          disabled={!canCreate}
          onClick={() => setConfirmation("create")}
        >
          <Rocket size={17} aria-hidden="true" />
          Desplegar
        </button>
        <button
          className="aws-delete-button"
          type="button"
          ref={deleteButton}
          disabled={!canDelete}
          onClick={() => setConfirmation("delete")}
        >
          <Trash2 size={17} aria-hidden="true" />
          Eliminar
        </button>
      </div>

      {confirmation && (
        <div
          className="aws-confirmation"
          role="dialog"
          aria-labelledby={`${dialogId}-title`}
          aria-describedby={`${dialogId}-description`}
          onKeyDown={(event) => {
            if (event.key === "Escape") {
              event.preventDefault();
              closeConfirmation();
            }
          }}
        >
          <h3 id={`${dialogId}-title`}>
            {confirmation === "create" ? "Confirmar costos de AWS" : "Confirmar eliminación"}
          </h3>
          <p id={`${dialogId}-description`}>
            {confirmation === "create"
              ? `Se crearán recursos en la cuenta ${connection?.account_id ?? "conectada"}, región ${deployment?.region}. Estos recursos pueden generar cargos mientras existan. Al confirmar, aceptas asumir esos costos.`
              : `Se eliminará el stack ${deployment?.stack_name} y sus recursos en la cuenta ${connection?.account_id ?? "conectada"}, región ${deployment?.region}. Esta acción puede destruir datos y no se puede deshacer.`}
          </p>
          <div className="aws-actions">
            <button
              className="aws-secondary-button"
              type="button"
              autoFocus
              onClick={closeConfirmation}
            >
              Cancelar
            </button>
            <button
              className={confirmation === "create" ? "primary-button" : "aws-delete-button"}
              type="button"
              disabled={confirmation === "create" ? !canCreate : !canDelete}
              onClick={confirmOperation}
            >
              {confirmation === "create" ? (
                <Rocket size={17} aria-hidden="true" />
              ) : (
                <Trash2 size={17} aria-hidden="true" />
              )}
              {confirmation === "create"
                ? "Confirmar costos y desplegar"
                : "Confirmar eliminación de recursos"}
            </button>
          </div>
        </div>
      )}

      {deployment && (
        <div className="aws-event-log">
          <h3>Últimos eventos</h3>
          {events.length === 0 ? (
            <p className="aws-message">No hay eventos registrados.</p>
          ) : (
            <ol className="aws-events" aria-label="Últimos eventos del despliegue">
              {events.map((event, index) => (
                <li
                  key={`${event.timestamp}-${event.logical_resource_id}-${event.resource_status}-${index}`}
                >
                  <time dateTime={event.timestamp}>{formatDate(event.timestamp)}</time>
                  <div>
                    <strong>{event.logical_resource_id}</strong>
                    <code>{event.resource_status}</code>
                    {event.reason && <p>{event.reason}</p>}
                  </div>
                </li>
              ))}
            </ol>
          )}
        </div>
      )}
    </section>
  );
}
