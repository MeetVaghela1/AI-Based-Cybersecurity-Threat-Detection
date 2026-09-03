// api.js — a tiny wrapper around the FastAPI backend.
//
// BASE is configurable:
//   * development (npm run dev) — the Vite dev server proxies /api -> the
//     backend (see vite.config.js), so we call "/api/..." URLs.
//   * production (npm run build) — the app is served BY FastAPI on the same
//     origin, so we call the API routes directly ("/models", "/simulate", ...).
const BASE = import.meta.env.DEV ? "/api" : "";

async function request(path, options) {
  const res = await fetch(`${BASE}${path}`, options);
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      if (body.detail) detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch {
      /* not JSON */
    }
    throw new Error(detail);
  }
  return res.json();
}

export const api = {
  /** GET /models — all trained models with their test-set metrics. */
  models: () => request("/models"),

  /** GET /compare — the full metric comparison data for charts. */
  compare: () => request("/compare"),

  /** GET /tuning-impact — baseline-vs-tuned scores per model. */
  tuningImpact: () => request("/tuning-impact"),

  /** GET /progression — A->E development-progression for Logistic Regression. */
  progression: () => request("/progression"),

  /** GET /training-curves — Phase 3 convergence curves + saved model configs. */
  trainingCurves: () => request("/training-curves"),

  /** GET /attack-info/{type} — plain-language explanation of an attack. */
  attackInfo: (attackType) =>
    request(`/attack-info/${encodeURIComponent(attackType)}`),

  /** POST /simulate — replay recorded test-set rows as "live" traffic. */
  simulate: (dataset, model, count = 15) =>
    request("/simulate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ dataset, model, count }),
    }),

  /** GET /predictions — the server-side stored prediction log. */
  predictions: () => request("/predictions"),
};
