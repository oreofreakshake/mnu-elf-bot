import axios from "axios"
import type { DocumentRecord, Entry, Issue, TelegramAuthData, TelegramUserRecord, UserRole } from "@/types"

export const API_URL = import.meta.env.VITE_API_URL ?? ""
const api = axios.create({ baseURL: `${API_URL}/api`, withCredentials: true })

export function apiErrorMessage(error: unknown, fallback: string) {
  if (axios.isAxiosError<{ detail?: string }>(error)) return error.response?.data?.detail ?? fallback
  return error instanceof Error ? error.message : fallback
}

export const getAuthConfig = async () => (await api.get<{ telegramBotUsername: string }>("/auth/config")).data
export const getCurrentUser = async () => (await api.get<TelegramUserRecord>("/auth/me")).data
export const loginWithTelegram = async (payload: TelegramAuthData) =>
  (await api.post<TelegramUserRecord>("/auth/telegram", payload)).data
export const loginForDevelopment = async (token: string) =>
  (await api.post<TelegramUserRecord>("/auth/development", { token })).data
export const logout = async () => (await api.post<{ signedOut: boolean }>("/auth/logout")).data
export const getUsers = async () => (await api.get<TelegramUserRecord[]>("/users")).data
export const updateUserRole = async (id: string, role: UserRole) =>
  (await api.patch<TelegramUserRecord>(`/users/${id}/role`, { role })).data

export const getDocuments = async () => (await api.get<DocumentRecord[]>("/documents")).data
export const getDocument = async (id: string) => (await api.get<DocumentRecord>(`/documents/${id}`)).data
export const getEntries = async (id: string) => (await api.get<Entry[]>(`/documents/${id}/entries`)).data
export const getIssues = async (id: string) => (await api.get<Issue[]>(`/documents/${id}/issues`)).data

export async function uploadDocument(file: File, onProgress: (value: number) => void) {
  const body = new FormData()
  body.append("file", file)
  return (
    await api.post<DocumentRecord>("/documents", body, {
      onUploadProgress: (event) => {
        if (event.total) onProgress(Math.round((event.loaded / event.total) * 100))
      },
    })
  ).data
}

export async function updateEntry(entry: Entry) {
  return (
    await api.patch<Entry>(`/entries/${entry.id}`, {
      sub_code: entry.subCode,
      subject_name: entry.subjectName,
      session_type: entry.sessionType,
      lecturer: entry.lecturer,
      time: entry.time,
      room: entry.room,
    })
  ).data
}

export const retryDocument = async (id: string) => (await api.post<DocumentRecord>(`/documents/${id}/retry`)).data
export const activateDocument = async (id: string) => (await api.post<DocumentRecord>(`/documents/${id}/activate`)).data
