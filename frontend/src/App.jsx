import { useState, useRef } from 'react'
import useApi from './hooks/useApi.js'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend,
} from 'recharts'

const T = {
  bg:      '#080f1a',
  panel:   '#0c1829',
  card:    '#0f1f33',
  border:  '#162840',
  accent:  '#4a9edd',
  green:   '#00e5a0',
  amber:   '#ffb020',
  red:     '#ff5c5c',
  purple:  '#7b6ff5',
  text:    '#d4e8f8',
  textMid: '#7aafd4',
  textDim: '#3a6080',
}

const MONO = "'IBM Plex Mono', monospace"
const BASE_URL = import.meta.env.VITE_API_URL || ''
const PIE_COLORS = [T.green, T.amber, T.red]
const AFF_LABELS = { resolved: 'Resuelta', declared_unresolved: 'Declarada', missing: 'Sin filiación' }

function Skeleton({ h = 20, w = '100%' }) {
  return <div style={{ height: h, width: w, borderRadius: 4, background: T.card, border: `1px solid ${T.border}` }} />
}

function KpiCard({ label, value, sub, color = T.accent }) {
  return (
    <div style={{
      background: T.card, border: `1px solid ${T.border}`, borderRadius: 8,
      padding: '1.25rem 1.5rem', flex: 1, minWidth: 140,
    }}>
      <div style={{ fontSize: 11, color: T.textDim, textTransform: 'uppercase', letterSpacing: 1, marginBottom: 8 }}>
        {label}
      </div>
      <div style={{ fontFamily: MONO, fontSize: 28, fontWeight: 600, color }}>
        {value ?? <Skeleton h={32} w={80} />}
      </div>
      {sub && <div style={{ fontSize: 12, color: T.textMid, marginTop: 4 }}>{sub}</div>}
    </div>
  )
}

function SectionTitle({ children }) {
  return (
    <h2 style={{
      fontSize: 11, fontWeight: 600, textTransform: 'uppercase', letterSpacing: 1.5,
      color: T.textDim, marginBottom: '1rem', borderBottom: `1px solid ${T.border}`, paddingBottom: 8,
    }}>
      {children}
    </h2>
  )
}

function Panel({ children, style }) {
  return (
    <div style={{ background: T.panel, border: `1px solid ${T.border}`, borderRadius: 10, padding: '1.25rem', ...style }}>
      {children}
    </div>
  )
}

const TT = {
  contentStyle: { background: '#0f1f33', border: '1px solid #162840', borderRadius: 6, color: '#d4e8f8' },
  labelStyle:   { color: '#7aafd4' },
  cursor:       { fill: '#162840' },
}

function SyncPanel() {
  const [text, setText]       = useState('')
  const [syncing, setSyncing] = useState(false)
  const [results, setResults] = useState(null)
  const fileRef               = useRef()

  function parseOrcids(raw) {
    return raw.split(/[\n,]+/).map(s => s.trim()).filter(Boolean)
  }

  function onFile(e) {
    const file = e.target.files[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = ev => setText(ev.target.result)
    reader.readAsText(file)
  }

  async function onSync() {
    const orcids = parseOrcids(text)
    if (!orcids.length) return
    setSyncing(true)
    setResults(null)
    try {
      const res = await fetch(`${BASE_URL}/api/sync`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ orcids }),
      })
      const data = await res.json()
      setResults(data.results)
    } catch {
      setResults([{ status: 'error', message: 'Error de red' }])
    } finally {
      setSyncing(false)
    }
  }

  const statusColor = { ok: T.green, not_found: T.amber, error: T.red }

  return (
    <div style={{
      background: T.panel, border: `1px solid ${T.border}`, borderRadius: 10,
      padding: '1rem 1.25rem', marginBottom: '1.5rem',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: '0.75rem' }}>
        <span style={{ fontSize: 11, fontWeight: 600, textTransform: 'uppercase', letterSpacing: 1.5, color: T.textDim }}>
          Sincronizar Investigador
        </span>
        <span style={{ fontSize: 11, color: T.textDim }}>— ingresa ORCIDs o sube un .txt</span>
      </div>

      <div style={{ display: 'flex', gap: 8, alignItems: 'flex-start' }}>
        <textarea
          value={text}
          onChange={e => setText(e.target.value)}
          placeholder={'0000-0002-7313-3766\n0000-0003-3112-5140'}
          rows={2}
          style={{
            flex: 1, background: T.card, border: `1px solid ${T.border}`, borderRadius: 6,
            color: T.text, fontFamily: MONO, fontSize: 12, padding: '0.5rem 0.75rem',
            resize: 'vertical', outline: 'none',
          }}
        />
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          <button
            onClick={() => fileRef.current.click()}
            style={{
              background: T.card, border: `1px solid ${T.border}`, borderRadius: 6,
              color: T.textMid, fontSize: 12, padding: '0.45rem 0.9rem', cursor: 'pointer',
            }}
          >
            Subir .txt
          </button>
          <input ref={fileRef} type="file" accept=".txt" style={{ display: 'none' }} onChange={onFile} />
          <button
            onClick={onSync}
            disabled={syncing || !text.trim()}
            style={{
              background: syncing || !text.trim() ? T.card : T.accent,
              border: `1px solid ${syncing || !text.trim() ? T.border : T.accent}`,
              borderRadius: 6, color: syncing || !text.trim() ? T.textDim : T.bg,
              fontSize: 12, fontWeight: 600, padding: '0.45rem 0.9rem', cursor: syncing ? 'wait' : 'pointer',
            }}
          >
            {syncing ? 'Sincronizando…' : 'Sincronizar'}
          </button>
        </div>
      </div>

      {results && (
        <div style={{ marginTop: '0.75rem', display: 'flex', flexDirection: 'column', gap: 6 }}>
          {results.map((r, i) => (
            <div key={i} style={{
              display: 'flex', alignItems: 'center', gap: 10, fontSize: 12,
              background: T.card, borderRadius: 6, padding: '0.4rem 0.75rem',
              borderLeft: `3px solid ${statusColor[r.status] || T.textDim}`,
            }}>
              <span style={{ fontFamily: MONO, color: T.textDim }}>{r.orcid}</span>
              {r.status === 'ok' && <>
                <span style={{ color: T.text }}>{r.name}</span>
                <span style={{ color: T.green, fontFamily: MONO, marginLeft: 'auto' }}>
                  +{r.works_synced} works
                </span>
              </>}
              {r.status === 'not_found' && <span style={{ color: T.amber }}>No encontrado en OpenAlex</span>}
              {r.status === 'error'     && <span style={{ color: T.red }}>{r.message}</span>}
            </div>
          ))}
          {results.some(r => r.status === 'ok') && (
            <button
              onClick={() => window.location.reload()}
              style={{
                alignSelf: 'flex-start', marginTop: 4,
                background: 'transparent', border: `1px solid ${T.accent}`,
                borderRadius: 6, color: T.accent, fontSize: 12, padding: '0.4rem 0.9rem', cursor: 'pointer',
              }}
            >
              Recargar datos
            </button>
          )}
        </div>
      )}
    </div>
  )
}

export default function App() {
  const { data: kpis }        = useApi('/api/analytics/kpis')
  const { data: annual }      = useApi('/api/analytics/annual')
  const { data: sdgData }     = useApi('/api/analytics/sdg')
  const { data: researchers } = useApi('/api/researchers')
  const { data: affSummary }  = useApi('/api/researchers/affiliation/summary')
  const { data: unresolved }  = useApi('/api/researchers/affiliation/unresolved')
  const { data: works }       = useApi('/api/works?limit=10')

  const pieParts = affSummary
    ? [
        { name: AFF_LABELS.resolved,            value: affSummary.resolved },
        { name: AFF_LABELS.declared_unresolved, value: affSummary.declared_unresolved },
        { name: AFF_LABELS.missing,             value: affSummary.missing },
      ].filter(d => d.value > 0)
    : []

  return (
    <div style={{ background: T.bg, minHeight: '100vh', color: T.text, paddingBottom: '4rem' }}>

      {/* ── HEADER ── */}
      <div style={{
        background: T.panel, borderBottom: `1px solid ${T.border}`,
        padding: '1rem 2rem', display: 'flex', alignItems: 'center', gap: 12,
      }}>
        <div style={{
          background: T.accent, borderRadius: 6, padding: '4px 10px',
          fontFamily: MONO, fontSize: 12, fontWeight: 600, color: T.bg,
        }}>UACJ·SCI</div>
        <span style={{ fontSize: 16, fontWeight: 600 }}>Sistema de Inteligencia Científica</span>
        <span style={{ marginLeft: 'auto', fontSize: 12, color: T.textDim, fontFamily: MONO }}>piloto v0.1</span>
      </div>

      <div style={{ maxWidth: 1200, margin: '0 auto', padding: '2rem 1.5rem' }}>

        <SyncPanel />

        {/* ── KPI CARDS ── */}
        <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', marginBottom: '2rem' }}>
          <KpiCard label="Total Works"    value={kpis?.total_works}                                                   sub="publicaciones indexadas" color={T.accent} />
          <KpiCard label="Citaciones"     value={kpis ? kpis.total_citations.toLocaleString() : null}                sub="citas recibidas"         color={T.green} />
          <KpiCard label="Leakage Rate"   value={kpis ? `${kpis.leakage_rate}%` : null}                              sub="sin filiación UACJ"      color={kpis && kpis.leakage_rate > 20 ? T.red : T.green} />
          <KpiCard label="Acceso Abierto" value={kpis ? `${kpis.oa_percentage}%` : null}                             sub="publicaciones OA"        color={T.purple} />
        </div>

        {/* ── PRODUCCIÓN ANUAL ── */}
        <Panel style={{ marginBottom: '1.5rem' }}>
          <SectionTitle>Producción Anual</SectionTitle>
          {annual && annual.length > 0 ? (
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={annual} margin={{ top: 4, right: 8, bottom: 4, left: -10 }}>
                <XAxis dataKey="year" tick={{ fill: T.textDim, fontSize: 12 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: T.textDim, fontSize: 12 }} axisLine={false} tickLine={false} />
                <Tooltip {...TT} />
                <Bar dataKey="count" fill={T.accent} radius={[4, 4, 0, 0]} name="Works" />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <Skeleton h={200} />
          )}
        </Panel>

        {/* ── FILIACIÓN + INVESTIGADORES ── */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1.5fr', gap: '1.5rem', marginBottom: '1.5rem' }}>

          <Panel>
            <SectionTitle>Estado de Filiación</SectionTitle>
            {pieParts.length > 0 ? (
              <>
                <ResponsiveContainer width="100%" height={190}>
                  <PieChart>
                    <Pie data={pieParts} cx="50%" cy="50%" innerRadius={52} outerRadius={76}
                      dataKey="value" paddingAngle={3}>
                      {pieParts.map((_, i) => <Cell key={i} fill={PIE_COLORS[i]} />)}
                    </Pie>
                    <Tooltip {...TT} />
                    <Legend iconType="circle" iconSize={8}
                      formatter={v => <span style={{ color: T.textMid, fontSize: 12 }}>{v}</span>} />
                  </PieChart>
                </ResponsiveContainer>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginTop: 4 }}>
                  {pieParts.map((p, i) => (
                    <div key={p.name} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13 }}>
                      <span style={{ color: PIE_COLORS[i] }}>{p.name}</span>
                      <span style={{ fontFamily: MONO, color: T.text }}>
                        {p.value} <span style={{ color: T.textDim }}>
                          ({affSummary ? Math.round(p.value / affSummary.total * 100) : 0}%)
                        </span>
                      </span>
                    </div>
                  ))}
                </div>
              </>
            ) : (
              <Skeleton h={270} />
            )}
          </Panel>

          <Panel>
            <SectionTitle>Investigadores</SectionTitle>
            {researchers ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                {researchers.map(r => (
                  <div key={r.id} style={{
                    background: T.card, borderRadius: 8, padding: '0.75rem 1rem', border: `1px solid ${T.border}`,
                  }}>
                    <div style={{ fontWeight: 600, fontSize: 14, marginBottom: 6 }}>{r.full_name}</div>
                    <div style={{ display: 'flex', gap: 16, fontSize: 12, color: T.textMid, fontFamily: MONO }}>
                      <span><span style={{ color: T.accent }}>{r.works_count}</span> works</span>
                      <span><span style={{ color: T.green }}>{r.cited_by_count}</span> citas</span>
                      <span>h-index <span style={{ color: T.purple }}>{r.h_index}</span></span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {[1, 2, 3].map(i => <Skeleton key={i} h={64} />)}
              </div>
            )}
          </Panel>
        </div>

        {/* ── ODS ── */}
        {sdgData && sdgData.length > 0 && (
          <Panel style={{ marginBottom: '1.5rem' }}>
            <SectionTitle>Objetivos de Desarrollo Sostenible</SectionTitle>
            <ResponsiveContainer width="100%" height={Math.max(180, sdgData.length * 36)}>
              <BarChart data={sdgData} layout="vertical" margin={{ left: 140, right: 40, top: 4, bottom: 4 }}>
                <XAxis type="number" tick={{ fill: T.textDim, fontSize: 11 }} axisLine={false} tickLine={false} />
                <YAxis type="category" dataKey="sdg_label" width={140}
                  tick={{ fill: T.textMid, fontSize: 12 }} axisLine={false} tickLine={false} />
                <Tooltip {...TT} />
                <Bar dataKey="count" fill={T.purple} radius={[0, 4, 4, 0]} name="Works" />
              </BarChart>
            </ResponsiveContainer>
          </Panel>
        )}

        {/* ── FILIACIÓN DECLARADA SIN RESOLVER ── */}
        {unresolved && unresolved.length > 0 && (
          <Panel style={{ marginBottom: '1.5rem' }}>
            <SectionTitle>Filiación Declarada Sin Resolver ({unresolved.length})</SectionTitle>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {unresolved.map(w => (
                <div key={w.work_id} style={{
                  background: T.card, borderRadius: 6, padding: '0.75rem 1rem',
                  borderLeft: `3px solid ${T.amber}`,
                }}>
                  <div style={{ fontSize: 13, fontWeight: 500, marginBottom: 4 }}>{w.title}</div>
                  <div style={{ display: 'flex', gap: 16, fontSize: 12, color: T.textMid }}>
                    <span>{w.researcher_name}</span>
                    <span style={{ fontFamily: MONO }}>{w.publication_year}</span>
                    {w.raw_affiliation_string && (
                      <span style={{ color: T.textDim, fontStyle: 'italic' }}>
                        "{w.raw_affiliation_string.slice(0, 80)}{w.raw_affiliation_string.length > 80 ? '…' : ''}"
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </Panel>
        )}

        {/* ── WORKS RECIENTES ── */}
        <Panel>
          <SectionTitle>Works Recientes</SectionTitle>
          {works && works.length > 0 ? (
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                <thead>
                  <tr style={{ borderBottom: `1px solid ${T.border}` }}>
                    {['Título', 'Investigador', 'Año', 'Tipo', 'Citas', 'OA', 'Filiación'].map(h => (
                      <th key={h} style={{
                        textAlign: 'left', padding: '0.5rem 0.75rem', color: T.textDim,
                        fontWeight: 500, fontSize: 11, textTransform: 'uppercase', letterSpacing: 1,
                      }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {works.map(w => {
                    const affColor = { resolved: T.green, declared_unresolved: T.amber, missing: T.red }
                    const c = affColor[w.affiliation_status] || T.textDim
                    return (
                      <tr key={w.id} style={{ borderBottom: `1px solid ${T.border}33` }}>
                        <td style={{ padding: '0.6rem 0.75rem', maxWidth: 320 }}>
                          <div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', color: T.text }}>
                            {w.title || <span style={{ color: T.textDim }}>Sin título</span>}
                          </div>
                        </td>
                        <td style={{ padding: '0.6rem 0.75rem', color: T.textMid, whiteSpace: 'nowrap' }}>{w.researcher_name}</td>
                        <td style={{ padding: '0.6rem 0.75rem', fontFamily: MONO, color: T.textMid }}>{w.publication_year}</td>
                        <td style={{ padding: '0.6rem 0.75rem', color: T.textDim, fontSize: 11 }}>{w.type}</td>
                        <td style={{ padding: '0.6rem 0.75rem', fontFamily: MONO, color: T.accent }}>{w.cited_by_count}</td>
                        <td style={{ padding: '0.6rem 0.75rem' }}>
                          {w.is_oa
                            ? <span style={{ color: T.green, fontSize: 11, fontFamily: MONO }}>OA</span>
                            : <span style={{ color: T.textDim, fontSize: 11 }}>—</span>}
                        </td>
                        <td style={{ padding: '0.6rem 0.75rem' }}>
                          <span style={{
                            fontSize: 11, fontFamily: MONO, padding: '2px 8px', borderRadius: 4,
                            background: c + '22', color: c,
                          }}>
                            {w.affiliation_status?.replace('_', ' ') || '—'}
                          </span>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {[1, 2, 3, 4].map(i => <Skeleton key={i} h={40} />)}
            </div>
          )}
        </Panel>

      </div>
    </div>
  )
}
