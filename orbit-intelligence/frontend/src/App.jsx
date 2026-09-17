import { useMemo, useState } from "react";

import OrbitViewer from "./OrbitViewer.jsx";


const API_BASE =
  import.meta.env.VITE_API_BASE_URL ||
  "http://127.0.0.1:8000";


// Multi-day arc. A 18-hour arc is too short for a reliable
// elliptical solution from Find_Orb and often fails or
// produces near-parabolic / high-uncertainty elements.
const SAMPLE_OBSERVATIONS = [
  {
    time_utc: "2026-09-05T02:15:00Z",
    ra_deg: 148.4123,
    dec_deg: 11.2341,
    magnitude: 18.4,
  },
  {
    time_utc: "2026-09-06T04:40:00Z",
    ra_deg: 149.1056,
    dec_deg: 11.4872,
    magnitude: 18.3,
  },
  {
    time_utc: "2026-09-07T07:05:00Z",
    ra_deg: 149.8124,
    dec_deg: 11.7518,
    magnitude: 18.2,
  },
  {
    time_utc: "2026-09-08T09:30:00Z",
    ra_deg: 150.5341,
    dec_deg: 12.0285,
    magnitude: 18.1,
  },
  {
    time_utc: "2026-09-09T11:55:00Z",
    ra_deg: 151.2718,
    dec_deg: 12.3174,
    magnitude: 18.2,
  },
  {
    time_utc: "2026-09-10T14:20:00Z",
    ra_deg: 152.0253,
    dec_deg: 12.6186,
    magnitude: 18.3,
  },
];


function formatNumber(value, digits = 4) {
  if (
    value === null ||
    value === undefined ||
    Number.isNaN(Number(value))
  ) {
    return "—";
  }

  return Number(value).toFixed(digits);
}


function formatErrorDetail(detail) {
  if (!detail) {
    return "Orbit determination failed.";
  }

  if (typeof detail === "string") {
    return detail;
  }

  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (typeof item === "string") {
          return item;
        }

        if (item && typeof item === "object") {
          return item.msg || JSON.stringify(item);
        }

        return String(item);
      })
      .join("\n");
  }

  if (typeof detail === "object") {
    return detail.msg || JSON.stringify(detail);
  }

  return String(detail);
}


function Metric({
  label,
  value,
  unit = "",
}) {
  return (
    <div className="metric">
      <div className="metric-label">
        {label}
      </div>

      <div className="metric-value">
        {value}
        {unit && (
          <span className="metric-unit">
            {unit}
          </span>
        )}
      </div>
    </div>
  );
}


export default function App() {
  const [objectName, setObjectName] =
    useState("MHA-TEST");

  const [observations, setObservations] =
    useState(SAMPLE_OBSERVATIONS);

  const [result, setResult] =
    useState(null);

  const [loading, setLoading] =
    useState(false);

  const [error, setError] =
    useState("");

  const elements =
    result?.elements || {};

  const updateObservation = (
    index,
    field,
    value
  ) => {
    setObservations((current) =>
      current.map((observation, i) => {
        if (i !== index) {
          return observation;
        }

        return {
          ...observation,
          [field]:
            field === "time_utc"
              ? value
              : Number(value),
        };
      })
    );
  };

  const addObservation = () => {
    const previous =
      observations[observations.length - 1];

    setObservations([
      ...observations,
      {
        ...previous,
        time_utc: "2026-09-11T00:00:00Z",
      },
    ]);
  };

  const removeObservation = (index) => {
    if (observations.length <= 3) {
      return;
    }

    setObservations(
      observations.filter((_, i) => i !== index)
    );
  };

  const loadDemo = () => {
    setObjectName("MHA-TEST");
    setObservations(SAMPLE_OBSERVATIONS);
    setResult(null);
    setError("");
  };

  const solve = async () => {
    setLoading(true);
    setError("");
    setResult(null);

    try {
      const response = await fetch(
        `${API_BASE}/api/orbit/solve`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            object_name: objectName,
            observations,
          }),
        }
      );

      let data;

      try {
        data = await response.json();
      } catch {
        throw new Error(
          `Backend returned non-JSON response (HTTP ${response.status}). ` +
          "Is the API running and is VITE_API_BASE_URL correct?"
        );
      }

      if (!response.ok) {
        throw new Error(
          formatErrorDetail(data.detail) ||
          `Orbit determination failed (HTTP ${response.status}).`
        );
      }

      setResult(data);
    } catch (err) {
      setError(
        err.message ||
        "Could not connect to the backend. Check that the API is running and CORS is allowed."
      );
    } finally {
      setLoading(false);
    }
  };

  const orbitReady =
    Boolean(result?.orbit_path_au?.length);

  const statusText = useMemo(() => {
    if (loading) {
      return "SOLVING ORBIT";
    }

    if (orbitReady) {
      return "SOLUTION READY";
    }

    return "AWAITING OBSERVATIONS";
  }, [loading, orbitReady]);

  return (
    <div className="app">
      <header className="topbar">
        <div>
          <div className="eyebrow">
            ORBITAL INTELLIGENCE
          </div>

          <h1>
            FIND_ORB
            <span>
              /
              TRAJECTORY LAB
            </span>
          </h1>
        </div>

        <div className="status-pill">
          <span className="status-dot" />
          {statusText}
        </div>
      </header>

      <main className="layout">
        <section className="control-panel">
          <div className="panel-header">
            <div>
              <div className="section-kicker">
                OBSERVATION INPUT
              </div>

              <h2>
                Astrometric observations
              </h2>
            </div>

            <button
              className="ghost-button"
              onClick={loadDemo}
              type="button"
            >
              LOAD DEMO
            </button>
          </div>

          <label className="field-label">
            OBJECT DESIGNATION

            <input
              value={objectName}
              onChange={(event) =>
                setObjectName(event.target.value)
              }
              placeholder="2026 AB"
            />
          </label>

          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>UTC</th>
                  <th>RA °</th>
                  <th>DEC °</th>
                  <th>MAG</th>
                  <th />
                </tr>
              </thead>

              <tbody>
                {observations.map(
                  (observation, index) => (
                    <tr key={index}>
                      <td>
                        <input
                          className="table-input time-input"
                          value={observation.time_utc}
                          onChange={(event) =>
                            updateObservation(
                              index,
                              "time_utc",
                              event.target.value
                            )
                          }
                        />
                      </td>

                      <td>
                        <input
                          className="table-input"
                          type="number"
                          step="0.0001"
                          value={observation.ra_deg}
                          onChange={(event) =>
                            updateObservation(
                              index,
                              "ra_deg",
                              event.target.value
                            )
                          }
                        />
                      </td>

                      <td>
                        <input
                          className="table-input"
                          type="number"
                          step="0.0001"
                          value={observation.dec_deg}
                          onChange={(event) =>
                            updateObservation(
                              index,
                              "dec_deg",
                              event.target.value
                            )
                          }
                        />
                      </td>

                      <td>
                        <input
                          className="table-input"
                          type="number"
                          step="0.1"
                          value={observation.magnitude}
                          onChange={(event) =>
                            updateObservation(
                              index,
                              "magnitude",
                              event.target.value
                            )
                          }
                        />
                      </td>

                      <td>
                        <button
                          className="remove-button"
                          onClick={() =>
                            removeObservation(index)
                          }
                          type="button"
                        >
                          ×
                        </button>
                      </td>
                    </tr>
                  )
                )}
              </tbody>
            </table>
          </div>

          <div className="control-actions">
            <button
              className="secondary-button"
              onClick={addObservation}
              type="button"
            >
              + ADD OBSERVATION
            </button>

            <button
              className="solve-button"
              onClick={solve}
              disabled={loading}
              type="button"
            >
              {loading
                ? "RUNNING FIND_ORB..."
                : "DETERMINE ORBIT →"}
            </button>
          </div>

          {error && (
            <div className="error-box">
              <strong>
                ORBIT SOLVER ERROR
              </strong>

              <span className="error-detail">
                {error}
              </span>
            </div>
          )}

          <div className="info-box">
            <strong>
              ENGINE
            </strong>

            <p>
              Observations are passed to the
              non-interactive Find_Orb engine.
              The backend does not invent an
              orbital solution. A multi-day arc
              is required for a reliable fit.
            </p>
          </div>
        </section>

        <section className="visual-panel">
          <div className="viewer-header">
            <div>
              <div className="section-kicker">
                TRAJECTORY VISUALISATION
              </div>

              <h2>
                Heliocentric orbit
              </h2>
            </div>

            {result && (
              <div className="engine-badge">
                FIND_ORB
              </div>
            )}
          </div>

          <div className="viewer">
            <OrbitViewer
              orbitPath={
                result?.orbit_path_au || []
              }
            />

            {!orbitReady && !loading && (
              <div className="viewer-empty">
                <div className="crosshair">
                  +
                </div>

                <span>
                  RUN AN ORBIT SOLUTION
                </span>

                <small>
                  The fitted trajectory will
                  appear here.
                </small>
              </div>
            )}

            {loading && (
              <div className="viewer-loading">
                <div className="loader" />

                <span>
                  FIND_ORB IS FITTING
                  OBSERVATIONS
                </span>
              </div>
            )}
          </div>

          <div className="metrics">
            <Metric
              label="SEMI-MAJOR AXIS"
              value={formatNumber(elements.a)}
              unit="AU"
            />

            <Metric
              label="ECCENTRICITY"
              value={formatNumber(elements.e, 5)}
            />

            <Metric
              label="INCLINATION"
              value={formatNumber(elements.i, 3)}
              unit="°"
            />

            <Metric
              label="PERIHELION"
              value={formatNumber(
                elements.perihelion_au
              )}
              unit="AU"
            />

            <Metric
              label="APHELION"
              value={formatNumber(
                elements.aphelion_au
              )}
              unit="AU"
            />

            <Metric
              label="ORBITAL PERIOD"
              value={formatNumber(
                elements.period_years,
                3
              )}
              unit="yr"
            />
          </div>
        </section>
      </main>

      <footer>
        <span>
          ORBIT INTELLIGENCE v0.1
        </span>

        <span>
          ASTROMETRY → ORBIT DETERMINATION
          → TRAJECTORY
        </span>
      </footer>
    </div>
  );
}
