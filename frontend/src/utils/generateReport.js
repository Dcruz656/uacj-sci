import { jsPDF } from 'jspdf'

// ── Palette (RGB arrays for jsPDF) ──────────────────────────────────────────
const C = {
  navy:    [8,   15,  26],
  panel:   [12,  24,  41],
  card:    [15,  31,  51],
  border:  [22,  40,  64],
  accent:  [74,  158, 221],
  green:   [0,   229, 160],
  amber:   [255, 176, 32],
  red:     [255, 92,  92],
  purple:  [123, 111, 245],
  text:    [212, 232, 248],
  textMid: [122, 175, 212],
  textDim: [58,  96,  128],
}

const M  = 14        // left/right margin (mm)
const W  = 210       // A4 width
const H  = 297       // A4 height
const CW = W - M * 2 // content width

// ── Low-level helpers ────────────────────────────────────────────────────────
const fill   = (doc, c) => doc.setFillColor(c[0], c[1], c[2])
const txt    = (doc, c) => doc.setTextColor(c[0], c[1], c[2])
const stroke = (doc, c) => doc.setDrawColor(c[0], c[1], c[2])

function pageBase(doc) {
  fill(doc, C.navy)
  doc.rect(0, 0, W, H, 'F')
}

function topStripe(doc) {
  fill(doc, C.accent)
  doc.rect(0, 0, W, 5, 'F')
}

function pageFooter(doc, pageNum) {
  fill(doc, C.panel)
  doc.rect(0, H - 12, W, 12, 'F')
  fill(doc, C.accent)
  doc.rect(0, H - 1.5, W, 1.5, 'F')
  txt(doc, C.textDim)
  doc.setFontSize(7.5)
  doc.setFont('helvetica', 'normal')
  doc.text('UACJ · Sistema de Inteligencia Cientifica', M, H - 4.5)
  doc.text(`Pagina ${pageNum}`, W - M, H - 4.5, { align: 'right' })
}

function sectionHeader(doc, label, y) {
  txt(doc, C.textDim)
  doc.setFontSize(7.5)
  doc.setFont('helvetica', 'bold')
  doc.text(label.toUpperCase(), M, y)
  const tw = doc.getTextWidth(label.toUpperCase())
  stroke(doc, C.border)
  doc.setLineWidth(0.3)
  doc.line(M + tw + 4, y - 0.5, M + CW, y - 0.5)
}

// ── KPI card with colored left border ────────────────────────────────────────
function kpiBox(doc, x, y, w, h, label, value, color) {
  fill(doc, C.card)
  doc.roundedRect(x, y, w, h, 2, 2, 'F')
  fill(doc, color)
  doc.rect(x, y, 2.5, h, 'F')
  txt(doc, C.textDim)
  doc.setFontSize(7)
  doc.setFont('helvetica', 'normal')
  doc.text(label.toUpperCase(), x + 5, y + 7)
  txt(doc, color)
  doc.setFontSize(16)
  doc.setFont('helvetica', 'bold')
  doc.text(String(value ?? '—'), x + 5, y + 17)
}

// ── Stacked horizontal affiliation bar ───────────────────────────────────────
function affiliationBar(doc, x, y, w, h, resolved, declared, missing, total) {
  const rW = total > 0 ? (resolved  / total) * w : 0
  const dW = total > 0 ? (declared  / total) * w : 0
  const mW = w - rW - dW
  fill(doc, C.card)
  doc.roundedRect(x, y, w, h, 2, 2, 'F')
  if (rW > 0) { fill(doc, C.green); doc.rect(x,        y, rW, h, 'F') }
  if (dW > 0) { fill(doc, C.amber); doc.rect(x + rW,   y, dW, h, 'F') }
  if (mW > 0) { fill(doc, C.red);   doc.rect(x + rW + dW, y, mW, h, 'F') }
}

// ── Vertical bar chart ───────────────────────────────────────────────────────
function barChartVertical(doc, data, x, y, w, h, labelKey, valueKey, color) {
  if (!data || data.length === 0) return
  const maxVal = Math.max(...data.map(d => Number(d[valueKey]) || 0))
  if (maxVal === 0) return
  const spacing = w / data.length
  const barW    = Math.min(spacing - 2, 10)

  // baseline
  stroke(doc, C.border)
  doc.setLineWidth(0.3)
  doc.line(x, y + h, x + w, y + h)

  data.forEach((d, i) => {
    const val  = Number(d[valueKey]) || 0
    const barH = (val / maxVal) * h
    const bx   = x + i * spacing + (spacing - barW) / 2
    const by   = y + h - barH
    fill(doc, color)
    doc.roundedRect(bx, by, barW, Math.max(barH, 0.5), 1, 1, 'F')
    // x-axis label
    txt(doc, C.textDim)
    doc.setFontSize(6.5)
    doc.setFont('helvetica', 'normal')
    doc.text(String(d[labelKey] || ''), bx + barW / 2, y + h + 5, { align: 'center' })
    // value above bar
    if (val > 0) {
      txt(doc, C.textMid)
      doc.setFontSize(6.5)
      doc.text(String(val), bx + barW / 2, by - 1.5, { align: 'center' })
    }
  })
}

// ── Horizontal bar (for ODS) ─────────────────────────────────────────────────
function horizontalBar(doc, x, y, w, h, value, maxVal, color) {
  const barW = maxVal > 0 ? Math.max((value / maxVal) * w, 0) : 0
  fill(doc, C.card)
  doc.roundedRect(x, y, w, h, 1, 1, 'F')
  if (barW > 0) {
    fill(doc, color)
    doc.roundedRect(x, y, barW, h, 1, 1, 'F')
  }
}

// ── Main export function ─────────────────────────────────────────────────────
export function generateReport({ kpis, annual, sdgData, researchers, affSummary, unresolved, works, selected }) {
  const doc     = new jsPDF({ orientation: 'portrait', unit: 'mm', format: 'a4' })
  const now     = new Date()
  const dateStr = now.toLocaleDateString('es-MX', { year: 'numeric', month: 'long', day: 'numeric' })

  // ═══════════════════════════════════════════════════════════════════════════
  // PAGE 1 — COVER
  // ═══════════════════════════════════════════════════════════════════════════
  pageBase(doc)
  topStripe(doc)

  // UACJ·SCI badge
  fill(doc, C.accent)
  doc.roundedRect(M, 12, 22, 7, 2, 2, 'F')
  txt(doc, C.navy)
  doc.setFontSize(8)
  doc.setFont('helvetica', 'bold')
  doc.text('UACJ·SCI', M + 1.5, 17)

  // Title
  txt(doc, C.textMid)
  doc.setFontSize(12)
  doc.setFont('helvetica', 'normal')
  doc.text('Sistema de', M, 32)
  doc.text('Inteligencia', M, 39)
  txt(doc, C.accent)
  doc.setFontSize(22)
  doc.setFont('helvetica', 'bold')
  doc.text('Cientifica', M, 49)

  // Institution subtitle
  txt(doc, C.textDim)
  doc.setFontSize(9)
  doc.setFont('helvetica', 'normal')
  doc.text('Universidad Autonoma de Ciudad Juarez', M, 56)

  // Filter badge (if researcher selected)
  let afterTitle = 62
  if (selected) {
    fill(doc, C.panel)
    doc.roundedRect(M, 60, CW, 9, 2, 2, 'F')
    fill(doc, C.accent)
    doc.rect(M, 60, 2.5, 9, 'F')
    txt(doc, C.textMid)
    doc.setFontSize(8)
    doc.setFont('helvetica', 'normal')
    doc.text('Filtro:', M + 5, 65.5)
    txt(doc, C.accent)
    doc.setFont('helvetica', 'bold')
    doc.text(selected.full_name, M + 19, 65.5)
    afterTitle = 74
  }

  // Generation date
  txt(doc, C.textDim)
  doc.setFontSize(7.5)
  doc.setFont('helvetica', 'normal')
  doc.text(`Generado: ${dateStr}`, W - M, afterTitle - 2, { align: 'right' })

  // Separator
  const sepY = afterTitle + 2
  stroke(doc, C.border)
  doc.setLineWidth(0.3)
  doc.line(M, sepY, M + CW, sepY)

  // KPI Cards (4 across)
  const kpiY = sepY + 6
  const kpiW = (CW - 9) / 4
  const kpiH = 28
  if (kpis) {
    kpiBox(doc, M,                    kpiY, kpiW, kpiH, 'Total Works',    kpis.total_works,                                    C.accent)
    kpiBox(doc, M + (kpiW + 3),       kpiY, kpiW, kpiH, 'Citaciones',     (kpis.total_citations || 0).toLocaleString('es'),    C.green)
    kpiBox(doc, M + (kpiW + 3) * 2,   kpiY, kpiW, kpiH, 'Leakage Rate',   `${kpis.leakage_rate}%`,                            kpis.leakage_rate > 20 ? C.red : C.green)
    kpiBox(doc, M + (kpiW + 3) * 3,   kpiY, kpiW, kpiH, 'Acceso Abierto', `${kpis.oa_percentage}%`,                           C.purple)
  }

  // Affiliation section
  const affY = kpiY + kpiH + 12
  sectionHeader(doc, 'Estado de Filiacion UACJ', affY)

  if (affSummary && affSummary.total > 0) {
    const barY = affY + 6
    affiliationBar(doc, M, barY, CW, 11, affSummary.resolved, affSummary.declared_unresolved, affSummary.missing, affSummary.total)

    // Legend row
    const lgY = barY + 18
    const lgItems = [
      { label: 'Resuelta',               count: affSummary.resolved,            color: C.green },
      { label: 'Declarada sin resolver', count: affSummary.declared_unresolved, color: C.amber },
      { label: 'Sin filiacion (fuga)',   count: affSummary.missing,             color: C.red },
    ]
    lgItems.forEach((item, i) => {
      const lx = M + i * (CW / 3)
      fill(doc, item.color)
      doc.circle(lx + 2, lgY - 1, 1.5, 'F')
      txt(doc, C.textMid)
      doc.setFontSize(8)
      doc.setFont('helvetica', 'normal')
      doc.text(item.label, lx + 5.5, lgY)
      const pct = Math.round((item.count / affSummary.total) * 100)
      txt(doc, C.text)
      doc.setFont('helvetica', 'bold')
      doc.text(`${item.count}  (${pct}%)`, lx + 5.5 + doc.getTextWidth(item.label) + 2, lgY)
    })
  }

  pageFooter(doc, 1)

  // ═══════════════════════════════════════════════════════════════════════════
  // PAGE 2 — PRODUCTION & STATS
  // ═══════════════════════════════════════════════════════════════════════════
  doc.addPage()
  pageBase(doc)
  topStripe(doc)

  let y2 = 13

  // Annual bar chart
  sectionHeader(doc, 'Produccion Anual', y2)
  y2 += 5
  if (annual && annual.length > 0) {
    barChartVertical(doc, annual, M, y2, CW, 48, 'year', 'count', C.accent)
    y2 += 60
  } else {
    y2 += 10
  }

  // Researchers table
  sectionHeader(doc, 'Investigadores', y2)
  y2 += 7
  if (researchers && researchers.length > 0) {
    const rCols = [M + 2, M + 78, M + 100, M + 120, M + 140]
    fill(doc, C.panel)
    doc.rect(M, y2 - 5, CW, 8, 'F')
    txt(doc, C.textDim)
    doc.setFontSize(7.5)
    doc.setFont('helvetica', 'bold')
    ;['Nombre', 'Works', 'Citas', 'h-index', 'Institucion'].forEach((h, i) => doc.text(h, rCols[i], y2))
    y2 += 6

    researchers.forEach((r, idx) => {
      if (idx % 2 === 0) { fill(doc, C.card); doc.rect(M, y2 - 4, CW, 8, 'F') }
      const name = r.full_name.length > 33 ? r.full_name.slice(0, 32) + '...' : r.full_name
      txt(doc, C.text);    doc.setFontSize(8); doc.setFont('helvetica', 'normal'); doc.text(name, rCols[0], y2)
      txt(doc, C.accent);  doc.text(String(r.works_count    || 0), rCols[1], y2)
      txt(doc, C.green);   doc.text(String(r.cited_by_count || 0), rCols[2], y2)
      txt(doc, C.purple);  doc.text(String(r.h_index        || 0), rCols[3], y2)
      txt(doc, C.textMid); doc.text(r.institution || 'UACJ',        rCols[4], y2)
      y2 += 8
    })
    y2 += 6
  }

  // Top 5 SDG horizontal bars
  if (sdgData && sdgData.length > 0) {
    sectionHeader(doc, 'Top Objetivos de Desarrollo Sostenible (ODS)', y2)
    y2 += 8
    const top5   = [...sdgData].sort((a, b) => (b.count || 0) - (a.count || 0)).slice(0, 5)
    const maxSDG = top5[0]?.count || 1
    const bH     = 5

    top5.forEach(sdg => {
      const label = (sdg.sdg_label || '').length > 38 ? (sdg.sdg_label || '').slice(0, 37) + '...' : (sdg.sdg_label || '')
      txt(doc, C.textMid)
      doc.setFontSize(7.5)
      doc.setFont('helvetica', 'normal')
      doc.text(label, M + 2, y2)
      const bx = M + 82
      const bw = CW - 82 - 18
      horizontalBar(doc, bx, y2 - bH + 1, bw, bH, sdg.count || 0, maxSDG, C.purple)
      txt(doc, C.text)
      doc.setFont('helvetica', 'bold')
      doc.text(String(sdg.count || 0), bx + bw + 3, y2)
      y2 += bH + 5
    })
  }

  pageFooter(doc, 2)

  // ═══════════════════════════════════════════════════════════════════════════
  // PAGE 3+ — WORKS TABLE
  // ═══════════════════════════════════════════════════════════════════════════
  doc.addPage()
  pageBase(doc)
  topStripe(doc)

  let pageNum = 3
  let wy = 13

  const wCols   = [M + 2, M + 90, M + 117, M + 129, M + 142, M + 156]
  const wHdrs   = ['Titulo', 'Investigador', 'Anio', 'Citas', 'OA', 'Filiacion']
  const affC    = { resolved: C.green, declared_unresolved: C.amber, missing: C.red }

  function worksHeader(yPos) {
    sectionHeader(doc, 'Publicaciones', yPos)
    yPos += 7
    fill(doc, C.panel)
    doc.rect(M, yPos - 5, CW, 8, 'F')
    txt(doc, C.textDim)
    doc.setFontSize(7.5)
    doc.setFont('helvetica', 'bold')
    wHdrs.forEach((h, i) => doc.text(h, wCols[i], yPos))
    return yPos + 6
  }

  wy = worksHeader(wy)

  if (works && works.length > 0) {
    works.forEach((w, idx) => {
      if (wy > H - 20) {
        pageFooter(doc, pageNum)
        doc.addPage()
        pageBase(doc)
        topStripe(doc)
        pageNum++
        wy = 13
        wy = worksHeader(wy)
      }
      if (idx % 2 === 0) { fill(doc, C.card); doc.rect(M, wy - 4, CW, 8, 'F') }

      const title  = (w.title || 'Sin titulo').length > 52 ? (w.title || 'Sin titulo').slice(0, 51) + '...' : (w.title || 'Sin titulo')
      const rname  = (w.researcher_name || '').length > 22 ? (w.researcher_name || '').slice(0, 21) + '...' : (w.researcher_name || '')
      const color  = affC[w.affiliation_status] || C.textDim
      const afflbl = (w.affiliation_status || '—').replace(/_/g, ' ')

      doc.setFontSize(7.5)
      doc.setFont('helvetica', 'normal')
      txt(doc, C.text);    doc.text(title,                        wCols[0], wy)
      txt(doc, C.textMid); doc.text(rname,                        wCols[1], wy)
      txt(doc, C.textMid); doc.text(String(w.publication_year || '—'), wCols[2], wy)
      txt(doc, C.accent);  doc.text(String(w.cited_by_count  ?? '—'),  wCols[3], wy)

      if (w.is_oa) { txt(doc, C.green);   doc.setFont('helvetica', 'bold'); doc.text('OA', wCols[4], wy); doc.setFont('helvetica', 'normal') }
      else          { txt(doc, C.textDim); doc.text('—', wCols[4], wy) }

      txt(doc, color)
      doc.setFont('helvetica', 'bold')
      doc.text(afflbl.slice(0, 16), wCols[5], wy)
      doc.setFont('helvetica', 'normal')

      wy += 8
    })
  }

  pageFooter(doc, pageNum)

  // ═══════════════════════════════════════════════════════════════════════════
  // PAGE CONDITIONAL — UNRESOLVED AFFILIATIONS
  // ═══════════════════════════════════════════════════════════════════════════
  if (unresolved && unresolved.length > 0) {
    pageNum++
    doc.addPage()
    pageBase(doc)
    topStripe(doc)

    let uy = 13
    sectionHeader(doc, `Filiacion Declarada Sin Resolver (${unresolved.length})`, uy)
    uy += 7

    txt(doc, C.textDim)
    doc.setFontSize(7.5)
    doc.setFont('helvetica', 'normal')
    doc.text('Estas publicaciones mencionan UACJ como afiliacion pero no estan correctamente indexadas en OpenAlex.', M, uy)
    doc.text('Accion requerida: crear alias en ror.org para el ID de UACJ (03mp1pv08).', M, uy + 5)
    uy += 13

    unresolved.forEach(w => {
      if (uy > H - 25) {
        pageFooter(doc, pageNum)
        doc.addPage()
        pageBase(doc)
        topStripe(doc)
        pageNum++
        uy = 13
      }

      fill(doc, C.card)
      doc.roundedRect(M, uy, CW, 20, 2, 2, 'F')
      fill(doc, C.amber)
      doc.rect(M, uy, 2.5, 20, 'F')

      txt(doc, C.text)
      doc.setFontSize(8.5)
      doc.setFont('helvetica', 'bold')
      const tit = (w.title || 'Sin titulo').length > 88 ? (w.title || 'Sin titulo').slice(0, 87) + '...' : (w.title || 'Sin titulo')
      doc.text(tit, M + 5, uy + 7)

      txt(doc, C.textMid)
      doc.setFontSize(7.5)
      doc.setFont('helvetica', 'normal')
      doc.text(`${w.researcher_name || ''}  ·  ${w.publication_year || ''}`, M + 5, uy + 13)

      if (w.raw_affiliation_string) {
        txt(doc, C.textDim)
        doc.setFontSize(7)
        const raw = w.raw_affiliation_string.length > 105 ? w.raw_affiliation_string.slice(0, 104) + '...' : w.raw_affiliation_string
        doc.text(`"${raw}"`, M + 5, uy + 18)
      }

      uy += 24
    })

    pageFooter(doc, pageNum)
  }

  // ── Save ──────────────────────────────────────────────────────────────────
  const filename = selected
    ? `UACJ-SCI-${selected.full_name.replace(/\s+/g, '_')}.pdf`
    : `UACJ-SCI-Reporte-${now.toISOString().slice(0, 10)}.pdf`
  doc.save(filename)
}
