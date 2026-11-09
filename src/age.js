// Admission must include children younger than 36 months. A 36-month minimum is excluded.
export function underThree(item) {
  if (!Number.isFinite(item.minMonths) || item.minMonths < 0 || item.minMonths >= 36) return false
  const text = `${item.title || ''} ${item.ageText || ''}`.normalize('NFKC').toLowerCase()
  const rules = [
    /\bm\/(\d{1,2})\b/g,
    /\b(\d{1,2})\s*\+(?!\s*(?:meses|mês|anos?|years?|months?|a\b))/g,
    /(?:a partir d[eo]s?|desde (?:os )?|maiores de|mais de|idade m[ií]nima(?: de)?|m[ií]nimo(?: de)?)\s*(\d{1,2})\s*(meses|mês|anos?|years?|months?|a\b)/g,
    /\+\s*(\d{1,2})\s*(meses|anos?|a\b)/g,
    /\b(\d{1,2})\s*\+\s*(meses|anos?|a\b)/g,
    /\b(\d{1,2})\s*(meses|anos?|a\b)\s*\+/g,
    /\b(\d{1,2})\s*(?:[-–—]|aos|a|até)\s*\d{1,2}\s*(meses|anos?|years?|months?)\b/g,
    /\b(\d{1,2})\s*(meses|anos?)\s*(?:[-–—]|aos|a|até)\s*\d{1,2}\s*(?:meses|anos?)\b/g
  ]
  return !rules.some(rule => [...text.matchAll(rule)].some(match => Number(match[1]) * (/^(mes|mês|month)/.test(match[2]) ? 1 : 12) >= 36))
}
