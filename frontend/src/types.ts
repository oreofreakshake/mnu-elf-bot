export type DocumentStatus = "queued" | "processing" | "completed" | "failed"

export interface DocumentRecord {
  id: string
  filename: string
  sizeBytes: number
  status: DocumentStatus
  isActive: boolean
  stage: string
  pageCount: number
  pagesProcessed: number
  recordsExtracted: number
  issuesFound: number
  error: string | null
  createdAt: string
  completedAt: string | null
}

export interface Entry {
  id: string
  sectionId: string
  course: string
  semester: number
  subCode: string
  subjectName: string
  sessionType: string
  lecturer: string
  time: string
  room: string
  sourcePage: number
  sourceRow: number
  pageWidth: number
  pageHeight: number
  bbox: { x0: number; top: number; x1: number; bottom: number }
  confidence: number
  valid: boolean
  reviewed: boolean
}

export interface Issue {
  id: string
  entryId: string | null
  page: number
  reason: string
  status: "open" | "resolved"
  rawData: Record<string, unknown>
  correctedData: Record<string, unknown> | null
}

export type UserRole = "user" | "reviewer" | "admin"

export interface SubjectSelection {
  id: string
  course: string
  subCode: string
}

export interface TelegramUserRecord {
  id: string
  telegramUserId: number
  username: string | null
  firstName: string | null
  lastName: string | null
  languageCode: string | null
  role: UserRole
  isActive: boolean
  notificationsEnabled: boolean
  createdAt: string
  lastSeenAt: string
  subjectCount: number
  subjects: SubjectSelection[]
}

export interface TelegramAuthData {
  id: number
  first_name: string
  last_name?: string
  username?: string
  photo_url?: string
  auth_date: number
  hash: string
}
