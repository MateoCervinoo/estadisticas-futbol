import { Partido } from '../../src/services/api'

export const ARGENTINA_TIME_ZONE = 'America/Argentina/Buenos_Aires'

export const DAY_LABEL_FORMAT: Intl.DateTimeFormatOptions = {
  timeZone: ARGENTINA_TIME_ZONE,
  weekday: 'short',
  day: '2-digit',
  month: 'short',
}

export const CLOCK_LABEL_FORMAT: Intl.DateTimeFormatOptions = {
  timeZone: ARGENTINA_TIME_ZONE,
  weekday: 'short',
  day: '2-digit',
  month: 'short',
  hour: '2-digit',
  minute: '2-digit',
  second: '2-digit',
}

export const TOURNAMENT_LABELS: Record<string, string> = {
  Mundial: 'Mundial',
  Clasificatorias: 'Clasificatorias',
  Amistoso: 'Amistoso',
  'Copa América': 'Copa América',
  Eurocopa: 'Eurocopa',
  'Nations League': 'Nations League',
  Confederaciones: 'Copa Confederaciones',
  'Copa Africana de Naciones': 'Copa Africana',
  'Copa Asiática': 'Copa Asiática',
  'Copa Oro': 'Copa Oro',
  'Juegos Olímpicos': 'Juegos Olímpicos',
  FIFA_WORLD_CUP: 'Mundial',
  WORLD_CUP: 'Mundial',
}

export const STAGE_LABELS: Record<string, string> = {
  GROUP_STAGE: 'Fase de Grupos',
  LAST_32: 'Dieciseisavos de Final',
  ROUND_OF_32: 'Dieciseisavos de Final',
  LAST_16: 'Octavos de Final',
  ROUND_OF_16: 'Octavos de Final',
  QUARTER_FINALS: 'Cuartos de Final',
  SEMI_FINALS: 'Semifinales',
  THIRD_PLACE: 'Tercer Puesto',
  FINAL: 'Final',
}

export const formatScore = (score: number | null) => (
  score === null || score === undefined ? '-' : String(score)
)

export const parseMatchDate = (iso: string) => {
  const value = String(iso ?? '').trim()
  if (!value) return new Date(Number.NaN)
  const hasTimezone = /(?:Z|[+-]\d{2}:\d{2})$/i.test(value)
  return new Date(hasTimezone ? value : `${value}Z`)
}

export const formatDate = (iso: string) => {
  try {
    return parseMatchDate(iso).toLocaleString('es-AR', {
      timeZone: ARGENTINA_TIME_ZONE,
      weekday: 'short',
      day: '2-digit',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return iso
  }
}

export const formatDateLabel = (iso: string) => {
  try {
    return parseMatchDate(iso).toLocaleDateString('es-AR', DAY_LABEL_FORMAT)
  } catch {
    return iso
  }
}

export const formatClock = (date: Date) => {
  try {
    return date.toLocaleString('es-AR', CLOCK_LABEL_FORMAT)
  } catch {
    return date.toISOString()
  }
}

export const dateKey = (iso: string) => {
  try {
    const parts = new Intl.DateTimeFormat('en-CA', {
      timeZone: ARGENTINA_TIME_ZONE,
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
    }).formatToParts(parseMatchDate(iso))

    const year = parts.find((part) => part.type === 'year')?.value
    const month = parts.find((part) => part.type === 'month')?.value
    const day = parts.find((part) => part.type === 'day')?.value

    return year && month && day ? `${year}-${month}-${day}` : iso.slice(0, 10)
  } catch {
    return iso.slice(0, 10)
  }
}

export const isPlayed = (partido: Partido) => {
  if (['NS', 'TIMED', 'SCHEDULED', 'IN_PLAY', 'PAUSED'].includes(partido.status)) return false
  const hasScore = partido.home_score !== null
    && partido.home_score !== undefined
    && partido.away_score !== null
    && partido.away_score !== undefined

  return hasScore || ['FT', 'AET', 'PEN'].includes(partido.status)
}

export const tournamentOf = (partido: Partido) => {
  const rawTournament = partido.tournament?.trim()
  if (!rawTournament) return 'Desconocido'
  return TOURNAMENT_LABELS[rawTournament] ?? rawTournament
}

export const stageOf = (partido: Partido) => {
  const rawStage = partido.stage?.trim()
  if (!rawStage) return ''
  return STAGE_LABELS[rawStage] ?? rawStage
}

export const groupOf = (partido: Partido) => {
  const rawGroup = partido.group?.trim()
  if (!rawGroup) return 'Sin grupo'
  return rawGroupLabel(rawGroup)
}

export const rawStageLabel = (stage: string) => STAGE_LABELS[stage] ?? stage

export const rawGroupLabel = (group: string) => group.replace('GROUP_', 'Grupo ')

const teamToFlag: Record<string, string> = {
  albania: 'al',
  algeria: 'dz',
  argentina: 'ar',
  australia: 'au',
  austria: 'at',
  belgium: 'be',
  belgica: 'be',
  bolivia: 'bo',
  bosnia: 'ba',
  'bosnia and herzegovina': 'ba',
  brazil: 'br',
  brasil: 'br',
  bulgaria: 'bg',
  cameroon: 'cm',
  camerun: 'cm',
  canada: 'ca',
  chile: 'cl',
  china: 'cn',
  colombia: 'co',
  'costa rica': 'cr',
  croatia: 'hr',
  croacia: 'hr',
  cuba: 'cu',
  'czech republic': 'cz',
  dinamarca: 'dk',
  denmark: 'dk',
  ecuador: 'ec',
  egypt: 'eg',
  egipto: 'eg',
  england: 'gb-eng',
  escocia: 'gb-sct',
  espana: 'es',
  estados_unidos: 'us',
  'estados unidos': 'us',
  finland: 'fi',
  finlandia: 'fi',
  france: 'fr',
  francia: 'fr',
  germany: 'de',
  ghana: 'gh',
  greece: 'gr',
  grecia: 'gr',
  haiti: 'ht',
  honduras: 'hn',
  hungary: 'hu',
  hungria: 'hu',
  iceland: 'is',
  india: 'in',
  iran: 'ir',
  ireland: 'ie',
  irlanda: 'ie',
  islandia: 'is',
  israel: 'il',
  italy: 'it',
  italia: 'it',
  'ivory coast': 'ci',
  jamaica: 'jm',
  japan: 'jp',
  japon: 'jp',
  mexico: 'mx',
  montenegro: 'me',
  morocco: 'ma',
  marruecos: 'ma',
  netherlands: 'nl',
  nigeria: 'ng',
  'north macedonia': 'mk',
  norway: 'no',
  noruega: 'no',
  panama: 'pa',
  paraguay: 'py',
  peru: 'pe',
  poland: 'pl',
  polonia: 'pl',
  portugal: 'pt',
  qatar: 'qa',
  'republic of ireland': 'ie',
  romania: 'ro',
  russia: 'ru',
  saudi_arabia: 'sa',
  'saudi arabia': 'sa',
  scotland: 'gb-sct',
  senegal: 'sn',
  serbia: 'rs',
  slovakia: 'sk',
  slovenia: 'si',
  south_africa: 'za',
  'south africa': 'za',
  south_korea: 'kr',
  'south korea': 'kr',
  spain: 'es',
  sweden: 'se',
  suecia: 'se',
  switzerland: 'ch',
  suiza: 'ch',
  tunisia: 'tn',
  turkey: 'tr',
  turquia: 'tr',
  ukraine: 'ua',
  uruguay: 'uy',
  usa: 'us',
  'united states': 'us',
  venezuela: 've',
  wales: 'gb-wls',
}

const normalizeTeamForFlag = (team: string) => (
  team
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .trim()
    .toLowerCase()
)

export const flagClass = (team: string, explicitCode?: string | null) => {
  const code = (explicitCode || teamToFlag[normalizeTeamForFlag(team)] || team.slice(0, 2)).toLowerCase()
  return `fi fi-${code}`
}
