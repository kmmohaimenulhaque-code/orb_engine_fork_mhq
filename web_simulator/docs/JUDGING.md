# Space Apps 2026 – Judging Alignment

## Impact
- Uses real orbital mechanics (poliastro, validated open-source)
- Path to real NASA/Celestrak/JPL data
- Educates and demonstrates orbit determination science

## Creativity
- Interactive 3D Cesium visualization with ground tracks
- Residual endpoint designed as bridge to Find_Orb
- Clean dual-mode input (Keplerian + future TLE/observations)

## Validity
- Explicit assumptions documented
- Synthetic residuals clearly labeled as demo
- Engine choice (poliastro) is peer-reviewed and widely used
- Clear separation between current MVP and future Find_Orb integration

## Relevance
- Directly addresses orbital determination & visualization
- Built on top of the spirit of the provided orb_engine (Find_Orb) fork
- NASA data ready (Horizons, TLEs, MPC)

## Presentation
- Professional dark UI
- One-command backend + simple frontend
- Live API docs at /docs
- Fallback: pre-loaded samples so demo never fails

## Honest Limits (important for Validity score)
- Full Find_Orb C++ wrapping deferred (too heavy for 48 h)
- Ground-track conversion is approximate (ITRS simplification)
- No live observation ingestion yet
- Covariance ellipsoids are future work

These limits are stated openly – judges reward honesty + clear next steps.
