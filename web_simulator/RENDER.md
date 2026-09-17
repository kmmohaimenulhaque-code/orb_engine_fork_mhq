# Deploy on Render (Mobile-friendly guide)

## Exact Settings

1. Go to https://dashboard.render.com → **New +** → **Web Service**
2. Connect repo: `kmmohaimenulhaque-code/orb_engine_fork_mhq`
3. Fill these fields:

| Field            | Value |
|------------------|-------|
| **Name**         | `nasa-orbit-sim` |
| **Region**       | Singapore (or closest) |
| **Branch**       | `Fix-needed` |
| **Root Directory** | `web_simulator` |
| **Runtime**      | Python 3 |
| **Build Command** | `pip install -r backend/requirements.txt` |
| **Start Command** | `cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT` |
| **Instance Type** | Free |

4. Click **Create Web Service**

## After deploy

- Frontend (3D simulator): `https://YOUR-SERVICE.onrender.com/`
- API docs: `https://YOUR-SERVICE.onrender.com/docs`
- Health: `https://YOUR-SERVICE.onrender.com/health`

## Notes

- First deploy on free tier can take 2–5 minutes.
- Free tier sleeps after ~15 min inactivity (first request will be slow).
- Cesium terrain may need a free Cesium Ion token for production quality (optional).
