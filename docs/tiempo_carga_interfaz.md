# Tiempo de carga de la interfaz (RNF-08)

Medición del tiempo de carga de las tres páginas principales del frontend de
SECI-TI. El requisito pide que carguen "en un tiempo razonable (orden de
segundos)" en condiciones normales.

## Umbral adoptado

Se toma como objetivo el umbral **"bueno" de Core Web Vitals: LCP ≤ 2,5 s**
([web.dev — Largest Contentful Paint](https://web.dev/articles/lcp)). Es el
estándar que usan Lighthouse y Chrome para decidir si una página "carga rápido",
y queda dentro del "orden de segundos" que pide el requisito.

## Método

- **Build medido:** `npm run build` del 18 de noviembre de 2026 (`index.html`
  0,60 kB; CSS 18,28 kB; JS 270,73 kB sin comprimir, 83,02 kB con gzip).
- **Servidor:** servidor HTTP estático local con *fallback* SPA a `index.html`
  y **sin compresión**, así que es un escenario conservador.
- **Navegador:** Google Chrome sin caché (contexto nuevo en cada carga),
  ventana de 1366 × 768, controlado con Playwright.
- **API simulada:** las llamadas a `/api/*` se responden con datos válidos
  generados desde los modelos del backend (un caso de la arquitectura B y el
  historial de 18 casos). Se mide la interfaz, no la latencia del backend ni del
  proveedor de IA.
- **Repeticiones:** 1 carga de calentamiento + 10 cargas medidas por página y por
  perfil. Se reporta la mediana y el peor valor de LCP.
- **Perfiles:**
  - *Sin limitación:* red local.
  - *4G lenta + CPU 4x:* el perfil móvil por defecto de Lighthouse (150 ms de
    latencia, 1,6 Mbps de bajada, CPU 4 veces más lenta).

## Resultados (milisegundos, mediana de 10 cargas)

| Perfil | Página | FCP | LCP | LCP peor caso | DOMContentLoaded | Cumple LCP ≤ 2,5 s |
| --- | --- | --- | --- | --- | --- | --- |
| Sin limitación | Analizar (`/`) | 104 | 104 | 132 | 64 | Sí |
| Sin limitación | Historial (`/casos`) | 92 | 92 | 120 | 64 | Sí |
| Sin limitación | Detalle de caso (`/casos/:id`) | 92 | 122 | 144 | 60 | Sí |
| 4G lenta + CPU 4x | Analizar (`/`) | 1944 | 1944 | 1964 | 1848 | Sí |
| 4G lenta + CPU 4x | Historial (`/casos`) | 1900 | 1900 | 1916 | 1831 | Sí |
| 4G lenta + CPU 4x | Detalle de caso (`/casos/:id`) | 1892 | 1992 | 2028 | 1830 | Sí |

FCP = *First Contentful Paint*; LCP = *Largest Contentful Paint*.

## Análisis

- En condiciones normales las tres páginas muestran contenido en **~0,1 s**.
- En el perfil móvil exigente el peor LCP es **2,03 s** (detalle de caso), con
  ~0,5 s de margen sobre el umbral.
- Casi todo el tiempo en el perfil lento es la descarga del único paquete JS
  (~271 kB sin comprimir). Servido con gzip (83 kB), como hace cualquier
  hosting o CDN, el tiempo de descarga bajaría a cerca de un tercio. Por eso
  esta medición es una cota superior.
- El detalle de caso tiene el LCP más alto porque su contenido principal se
  pinta después de recibir el caso del API.

## Limitaciones

- La latencia real del backend y del proveedor de IA no está incluida. El
  análisis con IA tarda varios segundos, pero es una acción del usuario, no
  parte de la carga de página.
- Es una medición de laboratorio, no de usuarios reales.

## Cómo reproducirlo

1. `cd frontend && npm run build && npm run preview`
2. Con el backend corriendo, abrir cada página en Chrome → DevTools →
   **Lighthouse** → modo *Navigation*, dispositivo *Mobile* → *Analyze page load*.
3. Comparar el LCP reportado con el umbral de 2,5 s.
