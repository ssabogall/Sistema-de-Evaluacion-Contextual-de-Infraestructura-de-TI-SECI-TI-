import type { SavedArchitectureAdvice } from "../types";

export function adviceFixture(summary = "Separar los procesos de venta y notificación."): SavedArchitectureAdvice {
  return {
    generated_at: "2026-11-09T14:30:00Z",
    provider: "Proveedor de prueba",
    model: "modelo-prueba",
    content: {
      summary,
      current_architecture_assessment: "El servidor compartido concentra los fallos.",
      recommendations: [
        {
          title: "Revisar el gasto",
          category: "cost",
          priority: "low",
          effort: "low",
          recommendation: "Medir el costo por pedido.",
          rationale: "El presupuesto es limitado.",
          expected_benefit: "Visibilidad del gasto.",
          tradeoffs: "Requiere etiquetar recursos.",
          evidence: [],
        },
        {
          title: "Aislar las notificaciones",
          category: "application",
          priority: "high",
          effort: "medium",
          recommendation: "Procesar notificaciones mediante una cola.",
          rationale: "Los envíos retrasan la compra.",
          expected_benefit: "Menor latencia de compra.",
          tradeoffs: "Entrega eventual y gestión de reintentos.",
          evidence: ["Las notificaciones se envían durante el pago."],
        },
      ],
      alternatives: [{
        name: "Procesamiento orientado a eventos",
        description: "Separar el procesamiento en consumidores independientes.",
        suitable_when: "Cuando haya picos en los envíos.",
        tradeoffs: "Mayor complejidad de observación.",
        migration_steps: ["Medir los tiempos actuales.", "Migrar un flujo y validar su entrega."],
      }],
      next_steps: ["Validar la latencia con una prueba de carga."],
      assumptions: ["El volumen de pedidos puede medirse."],
      open_questions: ["¿Cuánto retraso en las notificaciones es aceptable?"],
    },
  };
}
