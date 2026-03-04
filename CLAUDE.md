# UACJ · Sistema de Inteligencia Científica
**Repositorio:** https://github.com/Dcruz656/uacj-sci  
**Stack:** React + Vite · FastAPI · Neon PostgreSQL · Vercel  
**Estado:** Piloto v0.1 · 2 investigadores sincronizados · 83 works en DB

---

## Contexto institucional

Sistema de auditoría y análisis de producción científica para la Universidad Autónoma de Ciudad Juárez (UACJ). El problema central es que publicaciones de investigadores UACJ no aparecen correctamente atribuidas a la institución en OpenAlex/Scopus/WoS, afectando rankings universitarios.

El sistema clasifica cada publicación en 3 estados de filiación:
- `resolved` → OpenAlex identificó UACJ correctamente. Cuentan en rankings.
- `declared_unresolved` → El autor escribió UACJ pero OpenAlex no lo resolvió. Fix: alias en ror.org.
- `missing` → Sin mención de UACJ. Requiere contactar al investigador.

**UACJ ROR ID:** `03mp1pv08`  
**UACJ OpenAlex ID:** `I186621756`

---

## Stack tecnológico — DECISIONES DEFINITIVAS

> No proponer alternativas. No cambiar el stack.

| Capa | Tecnología |
|------|-----------|
| Frontend | React 18 + Vite + Recharts |
| Backend | FastAPI (Python 3.11+) |
| Base de datos | **Neon PostgreSQL** (psycopg2) |
| Deploy | **Vercel** (frontend + backend serverless) |
| Datos | OpenAlex API (polite pool, sin API key) |
| Estilos | CSS inline con tema oscuro azul navy |
| Fuente | IBM Plex Sans + IBM Plex Mono |

---

## Estructura del proyecto

```
uacj-sci/
├── backend/
│   ├── api/
│   │   ├── main.py          ← FastAPI app + CORS + include_router
│   │   ├── index.py         ← Entry point Vercel serverless
│   │   └── routes/
│   │       ├── researchers.py
│   │       ├── works.py
│   │       └── analytics.py
│   ├── core/
│   │   └── config.py        ← Settings (pydantic-settings, lee .env)
│   ├── db/
│   │   ├── connection.py    ← get_conn() context manager con psycopg2
│   │   ├── init.py          ← Crea tablas en Neon desde schema.sql
│   │   └── queries.py       ← TODAS las queries SQL. Nunca SQL inline en routes.
│   └── extractors/
│       └── openalex.py      ← Cliente OpenAlex con throttle + retry (tenacity)
├── frontend/
│   └── src/
│       ├── App.jsx          ← Dashboard principal (tema oscuro azul)
│       └── hooks/
│           └── useApi.js    ← Hook para fetch al API. Usar siempre este hook.
├── scripts/
│   └── sync_researchers.py  ← Pobla Neon desde OpenAlex por ORCID
├── schema.sql               ← DDL completo. 8 tablas + 3 vistas + índices
└── vercel.json              ← Routing: /api/* → backend, /* → frontend
```

---

## Base de datos — Schema

### Tablas principales

| Tabla | PK | Descripción |
|-------|----|-------------|
| `researchers` | `id` (ORCID) | Investigadores UACJ |
| `works` | `id` (OpenAlex ID) | Publicaciones indexadas |
| `authorships` | `id` (hash) | **Tabla central.** Relaciona work+researcher con `affiliation_status` |
| `journals` | `id` | Catálogo de revistas con cuartil SJR y flag predatoria |
| `institutions` | `ror_id` | Instituciones colaboradoras |
| `collaborations` | `id` | Co-autorías institucionales |
| `sdg_classifications` | `id` | ODS 1-17 con confidence score |
| `apc_payments` | `id` | Pagos APC estimados o reales |

### Vistas analíticas (no modificar)
- `v_researcher_summary` → métricas agregadas por investigador
- `v_annual_production` → producción por año
- `v_apc_summary` → gasto APC por facultad y cuartil

### Campo crítico: `affiliation_status`
```
resolved             → 49 works (59%)   — sin acción
declared_unresolved  →  6 works  (7.2%) — alias ROR
missing              → 28 works (33.7%) — contactar autor
```

---

## API REST — Endpoints implementados

Base URL local: `http://localhost:8000`  
En producción Vercel: `/api/*` se enruta al backend serverless.

| Endpoint | Descripción |
|----------|-------------|
| `GET /health` | Status + conexión Neon |
| `GET /analytics/kpis` | total_works, citations, leakage_rate, affiliation |
| `GET /analytics/annual` | Producción por año desde 2010 |
| `GET /analytics/sdg` | ODS 1-17: works count + avg confidence |
| `GET /analytics/apc` | Total USD/MXN, promedio por artículo |
| `GET /researchers/` | Lista investigadores. Param: `?faculty=ICB` |
| `GET /researchers/{id}` | Detalle por ORCID |
| `GET /researchers/affiliation` | Distribución por investigador |
| `GET /researchers/affiliation/summary` | Totales globales |
| `GET /researchers/affiliation/unresolved` | Works declared_unresolved + raw string |
| `GET /works/` | Params: `researcher_id`, `year`, `status`, `limit` |

---

## Variables de entorno

### backend/.env (crear desde .env.example)
```
DATABASE_URL=postgresql://user:pass@ep-xxx.aws.neon.tech/neondb?sslmode=require
OPENALEX_EMAIL=auditoria@uacj.mx
UACJ_ROR_ID=03mp1pv08
UACJ_OPENALEX_ID=I186621756
```

### frontend/.env.local
```
VITE_API_URL=        ← vacío en dev (usa proxy Vite → localhost:8000)
                     ← en producción: URL del backend en Vercel
```

---

## Setup local — orden exacto

```bash
# 1. Backend
cd backend
pip install -r requirements.txt
cp .env.example .env
# Editar .env con tu DATABASE_URL de Neon

# 2. Inicializar DB en Neon
cd ..
python -m backend.db.init

# 3. Sincronizar investigadores
python scripts/sync_researchers.py 0000-0002-7313-3766 0000-0003-3112-5140

# 4. Levantar API
uvicorn backend.api.main:app --reload --port 8000

# 5. Frontend (en otra terminal)
cd frontend
npm install
npm run dev
# Dashboard en http://localhost:5173
```

---

## Estado actual del proyecto

### ✅ Completo
- Schema SQL (8 tablas + 3 vistas + índices)
- Script de sincronización OpenAlex → Neon
- Backend FastAPI con todos los endpoints
- Conexión Neon PostgreSQL (psycopg2)
- Hook `useApi.js` para fetch desde React
- Vite config con proxy al backend
- `vercel.json` con routing frontend/backend
- 2 investigadores sincronizados → 83 works en Neon
- Dashboard React con 6 vistas y tema oscuro azul

### ⚡ Pendiente (hacer en este orden)
1. **Conectar frontend al API** — reemplazar datos hardcodeados en App.jsx
2. **Crear repo en GitHub** — `github.com/Dcruz656/uacj-sci`
3. **Deploy en Vercel** — conectar repo, agregar DATABASE_URL en env vars
4. **Sincronizar investigadores restantes** — agregar ORCIDs al script
5. **Módulos fase 2** — revistas predatorias, mapa colaboraciones, exportar PDF

---

## Tarea inmediata — Conectar App.jsx al API

App.jsx tiene datos hardcodeados en constantes al inicio del archivo.
Deben reemplazarse usando el hook `useApi`:

```jsx
// hooks/useApi.js — ya implementado
const { data, loading, error } = useApi('/analytics/kpis');

// Reemplazar estas constantes en App.jsx:
// const produccionAnual = [ { year: "2019", pub: 38 ... } ]
// const filiacion = [ { name: "Resuelta", value: 40 ... } ]
// const investigadores = [ ... ]
// etc.

// Por estas llamadas al API:
const { data: kpis,        loading: loadingKpis }   = useApi('/analytics/kpis');
const { data: annual,      loading: loadingAnnual }  = useApi('/analytics/annual');
const { data: sdgData,     loading: loadingSdg }     = useApi('/analytics/sdg');
const { data: researchers, loading: loadingRes }     = useApi('/researchers/');
const { data: affSummary }  = useApi('/researchers/affiliation/summary');
const { data: unresolved }  = useApi('/researchers/affiliation/unresolved');
const { data: works }       = useApi('/works/?limit=10');
```

Cada vista debe mostrar un skeleton/spinner mientras `loading === true`.

---

## Datos reales sincronizados (Feb 2025)

| Métrica | Valor |
|---------|-------|
| Total works | 83 |
| Total citaciones | 402 |
| Filiación resuelta | 49 (59%) |
| Declarada no resuelta | 6 (7.2%) |
| Sin filiación | 28 (33.7%) |

### Por investigador

| Investigador | Works | Citas | h-index | Fuga |
|-------------|-------|-------|---------|------|
| Óscar A. Esparza Del Villar | 66 | 391 | 10 | 31.8% |
| Luis Manuel Lara Rodríguez | 17 | 11 | 2 | 41.2% |

### ODS dominantes (dato real — diferente al perfil publicado)
1. ODS 5 · Igualdad de Género → **19 works** ⚠️ inesperado
2. ODS 10 · Reducción de Desigualdades → 10 works
3. ODS 16 · Paz y Justicia → 9 works
4. ODS 3 · Salud → 8 works (esperado pero en 4° lugar)

---

## Reglas para Claude Code

### ✅ HACER
- `psycopg2` para conectar a Neon (nunca DuckDB ni SQLite)
- Queries SQL solo en `backend/db/queries.py`
- `useApi()` hook para todos los fetch del frontend
- `ON CONFLICT DO UPDATE` en todos los upserts
- Variables de entorno para `DATABASE_URL` (nunca hardcodear)
- Respetar tema oscuro azul navy del dashboard
- Respetar estructura de carpetas definida
- Commits pequeños y descriptivos en inglés

### ❌ NO HACER
- Proponer DuckDB, SQLite u otras DBs
- SQL inline en routes o componentes React
- `fetch()` directo sin usar el hook `useApi`
- Cambiar colores, fuentes o estilo visual del dashboard
- Crear carpetas fuera de la estructura definida
- Hardcodear credenciales en ningún archivo
- Cambiar el stack tecnológico

---

## Tema visual del dashboard

```js
// Colores exactos — no modificar
const T = {
  bg:     "#080f1a",   // fondo principal
  panel:  "#0c1829",   // fondo de paneles
  card:   "#0f1f33",   // fondo de cards
  border: "#162840",
  accent: "#4a9edd",   // azul principal
  green:  "#00e5a0",   // verde éxito
  amber:  "#ffb020",   // amarillo advertencia
  red:    "#ff5c5c",   // rojo error/fuga
  purple: "#7b6ff5",   // purple secundario
  text:   "#d4e8f8",   // texto principal
  textMid:"#7aafd4",   // texto secundario
  textDim:"#3a6080",   // texto tenue
};

// Fuentes
// IBM Plex Sans — texto general
// IBM Plex Mono — números, KPIs, badges
```
