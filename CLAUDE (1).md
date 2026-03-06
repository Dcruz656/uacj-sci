# UACJ · Sistema de Inteligencia Científica
**Repo:** https://github.com/Dcruz656/uacj-sci  
**Stack:** React + Vite · FastAPI · Neon PostgreSQL · Vercel (frontend) · Railway (backend)  
**Estado:** Piloto v0.1 · 2 investigadores sincronizados · 83 works en DB

---

## 1. Contexto institucional

Sistema de auditoría de producción científica para la Universidad Autónoma de Ciudad Juárez (UACJ). Clasifica cada publicación en 3 estados de filiación institucional:

- `resolved` → OpenAlex identificó UACJ correctamente. Cuentan en rankings.
- `declared_unresolved` → Autor escribió UACJ pero OpenAlex no lo resolvió. Fix: alias en ror.org (ROR ID: 03mp1pv08).
- `missing` → Sin mención de UACJ. Requiere contactar al investigador.

**Datos actuales:** 83 works · 402 citas · 59% resuelto · 33.7% fuga

---

## 2. Stack — DEFINITIVO, no proponer alternativas

| Capa | Tecnología | Deploy |
|------|-----------|--------|
| Frontend | React 18 + Vite + Recharts | **Vercel** |
| Backend | FastAPI (Python 3.11+) | **Railway** |
| Base de datos | Neon PostgreSQL | Neon cloud |
| Sync datos | Python script local | Local (manual) |
| Repo | GitHub | github.com/Dcruz656/uacj-sci |

---

## 3. Estructura de carpetas

```
uacj-sci/
├── CLAUDE.md
├── schema.sql               ← DDL completo para Neon
├── vercel.json              ← Solo frontend
├── .gitignore
├── backend/
│   ├── requirements.txt
│   ├── .env.example
│   ├── api/
│   │   ├── __init__.py
│   │   ├── main.py          ← FastAPI app + CORS + routers
│   │   ├── index.py         ← Entry point Railway
│   │   └── routes/
│   │       ├── __init__.py
│   │       ├── researchers.py
│   │       ├── works.py
│   │       └── analytics.py
│   ├── core/
│   │   ├── __init__.py
│   │   └── config.py        ← pydantic-settings, lee .env
│   ├── db/
│   │   ├── __init__.py
│   │   ├── connection.py    ← psycopg2 context manager
│   │   ├── init.py          ← crea tablas en Neon
│   │   └── queries.py       ← TODAS las queries SQL aquí
│   └── extractors/
│       ├── __init__.py
│       └── openalex.py      ← cliente OpenAlex + throttle + retry
├── frontend/
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js       ← proxy /api → localhost:8000 en dev
│   ├── .env.example
│   ├── .env.local
│   └── src/
│       ├── main.jsx
│       ├── App.jsx          ← dashboard principal (tema oscuro azul)
│       └── hooks/
│           └── useApi.js    ← hook fetch reutilizable
└── scripts/
    └── sync_researchers.py  ← pobla Neon desde OpenAlex por ORCID
```

---

## 4. Variables de entorno

### backend/.env
```
DATABASE_URL=postgresql://user:pass@ep-xxx.aws.neon.tech/neondb?sslmode=require
OPENALEX_EMAIL=auditoria@uacj.mx
UACJ_ROR_ID=03mp1pv08
UACJ_OPENALEX_ID=I186621756
```

### frontend/.env.local
```
VITE_API_URL=http://localhost:8000   ← dev local
# En producción Vercel usar la URL de Railway
```

---

## 5. Setup local

```bash
# Terminal 1 — Backend
cd backend
pip install -r requirements.txt
cp .env.example .env
# pegar DATABASE_URL de Neon en .env

python -m backend.db.init                          # crea tablas en Neon
python scripts/sync_researchers.py \
  0000-0002-7313-3766 \
  0000-0003-3112-5140                              # sincroniza investigadores

uvicorn backend.api.main:app --reload --port 8000  # levanta API

# Terminal 2 — Frontend
cd frontend
npm install
npm run dev
# abre http://localhost:5173
```

---

## 6. Deploy

### Backend → Railway
1. railway.app → New Project → Deploy from GitHub repo
2. Seleccionar `Dcruz656/uacj-sci`
3. Root directory: `backend`
4. Start command: `uvicorn api.main:app --host 0.0.0.0 --port $PORT`
5. Variables de entorno en Railway: agregar `DATABASE_URL`
6. Railway genera una URL pública, ej: `https://uacj-sci-backend.railway.app`

### Frontend → Vercel
1. vercel.com → New Project → Import `Dcruz656/uacj-sci`
2. Root directory: `frontend`
3. Framework: Vite
4. Variables de entorno en Vercel: `VITE_API_URL=https://uacj-sci-backend.railway.app`
5. Deploy

### vercel.json (solo frontend, sin backend)
```json
{
  "version": 2,
  "builds": [{ "src": "frontend/package.json", "use": "@vercel/static-build", "config": { "distDir": "dist" } }],
  "routes": [{ "src": "/(.*)", "dest": "frontend/$1" }]
}
```

---

## 7. API REST — endpoints implementados

| Endpoint | Descripción |
|----------|-------------|
| `GET /health` | status + conexión Neon |
| `GET /analytics/kpis` | total_works, citations, leakage_rate, affiliation |
| `GET /analytics/annual` | producción por año desde 2010 |
| `GET /analytics/sdg` | ODS 1-17: works + avg confidence |
| `GET /analytics/apc` | total USD/MXN, promedio |
| `GET /researchers/` | lista con métricas. param: `?faculty=ICB` |
| `GET /researchers/{id}` | detalle por ORCID |
| `GET /researchers/affiliation` | distribución por investigador |
| `GET /researchers/affiliation/summary` | totales globales |
| `GET /researchers/affiliation/unresolved` | works declared_unresolved + raw string |
| `GET /works/` | params: researcher_id, year, status, limit |

---

## 8. Estado actual

### ✅ Ya implementado
- Schema SQL completo (8 tablas + 3 vistas + índices)
- Script sync_researchers.py funcional y probado
- Backend FastAPI con todos los endpoints funcional
- Conexión Neon PostgreSQL con psycopg2
- Hook useApi.js en frontend
- Vite proxy config
- Dashboard React con 6 vistas y tema oscuro azul navy
- 83 works reales en Neon (2 investigadores)

### ⚡ Pendiente — hacer en este orden

**Tarea 1 — Actualizar vercel.json**
Cambiar a configuración solo-frontend (Railway maneja el backend).
El vercel.json actual intenta deployar FastAPI en Vercel, lo cual no aplica.
Reemplazar con:
```json
{
  "version": 2,
  "buildCommand": "cd frontend && npm install && npm run build",
  "outputDirectory": "frontend/dist",
  "framework": null
}
```

**Tarea 2 — Conectar App.jsx al API real**
App.jsx tiene datos hardcodeados. Reemplazar con useApi():
```jsx
// useApi ya está implementado en hooks/useApi.js
// BASE URL viene de import.meta.env.VITE_API_URL

// Reemplazar las constantes estáticas por:
const { data: kpis,        loading: kpisLoading }   = useApi('/analytics/kpis');
const { data: annual,      loading: annualLoading }  = useApi('/analytics/annual');
const { data: sdgData }                              = useApi('/analytics/sdg');
const { data: researchers }                          = useApi('/researchers/');
const { data: affSummary }                           = useApi('/researchers/affiliation/summary');
const { data: unresolved }                           = useApi('/researchers/affiliation/unresolved');
const { data: works }                                = useApi('/works/?limit=20');

// Cada vista debe manejar loading con un skeleton simple:
if (loading) return <div style={{color: T.textDim}}>Cargando...</div>;
if (error)   return <div style={{color: T.red}}>Error: {error}</div>;
```

**Tarea 3 — Adaptar nombres de campos**
El API devuelve campos en snake_case. App.jsx usa nombres distintos.
Mapeo necesario:
```
API annual[].works      → App pub
API annual[].citations  → App cit
API sdgData[].sdg_number → App code
API sdgData[].sdg_label  → App label
API sdgData[].works      → App val
API researchers[].total_works → App pub
API researchers[].cited_by_count → App cit
API researchers[].full_name → App nombre
```

**Tarea 4 — Push y deploy**
```bash
git add .
git commit -m "connect frontend to API, update vercel.json for Railway setup"
git push origin main
```
Después configurar Railway y Vercel como se describe en la sección 6.

---

## 9. Datos reales en Neon (referencia)

| Investigador | Works | Citas | h-index | Fuga |
|-------------|-------|-------|---------|------|
| Óscar A. Esparza Del Villar (ICB) | 66 | 391 | 10 | 31.8% |
| Luis Manuel Lara Rodríguez (ICSA) | 17 | 11 | 2 | 41.2% |

**ODS dominantes (dato real — distinto al perfil publicado):**
1. ODS 5 · Igualdad de Género → 19 works ⚠️
2. ODS 10 · Reducción de Desigualdades → 10 works
3. ODS 16 · Paz y Justicia → 9 works
4. ODS 3 · Salud → 8 works (esperado pero en 4° lugar)

---

## 10. Reglas

### ✅ Siempre
- `psycopg2` para Neon — nunca DuckDB ni SQLite
- SQL solo en `backend/db/queries.py` — nunca inline en routes
- `useApi()` para todos los fetch — nunca fetch() directo en componentes
- `ON CONFLICT DO UPDATE` en todos los upserts
- `DATABASE_URL` siempre desde variable de entorno
- Respetar tema oscuro azul navy y fuentes IBM Plex

### ❌ Nunca
- Proponer cambiar el stack (React, FastAPI, Neon, Vercel, Railway)
- SQL en archivos de routes o componentes React
- Hardcodear credenciales
- Cambiar colores o fuentes del dashboard
- Crear carpetas fuera de la estructura definida

---

## 11. Tema visual — colores exactos

```js
const T = {
  bg:      "#080f1a",  // fondo principal
  panel:   "#0c1829",  // paneles
  card:    "#0f1f33",  // cards
  border:  "#162840",
  accent:  "#4a9edd",  // azul principal
  green:   "#00e5a0",  // éxito / resuelto
  amber:   "#ffb020",  // advertencia / no resuelto
  red:     "#ff5c5c",  // error / fuga
  purple:  "#7b6ff5",
  text:    "#d4e8f8",
  textMid: "#7aafd4",
  textDim: "#3a6080",
  grid:    "#0f2035",
};
// Fuentes: IBM Plex Sans (texto) · IBM Plex Mono (números/KPIs)
```
