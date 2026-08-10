import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { LoaderCircle } from "lucide-react"
import { useState } from "react"
import { AppHeader, type DashboardView } from "@/components/app-header"
import { getCurrentUser, logout } from "@/lib/api"
import { DashboardPage } from "@/pages/dashboard-page"
import { LoginPage } from "@/pages/login-page"
import { ReviewPage } from "@/pages/review-page"
import { UsersPage } from "@/pages/users-page"

export default function App() {
  const queryClient = useQueryClient()
  const me = useQuery({ queryKey: ["me"], queryFn: getCurrentUser, retry: false })
  const [documentId, setDocumentId] = useState<string | null>(() =>
    new URLSearchParams(window.location.search).get("document"),
  )
  const [view, setView] = useState<DashboardView>(() =>
    new URLSearchParams(window.location.search).get("view") === "users" ? "users" : "dashboard",
  )
  const logoutMutation = useMutation({
    mutationFn: logout,
    onSuccess: () => {
      queryClient.clear()
      setDocumentId(null)
      setView("dashboard")
    },
  })

  function openDocument(id: string | null) {
    setDocumentId(id)
    const url = new URL(window.location.href)
    if (id) url.searchParams.set("document", id)
    else url.searchParams.delete("document")
    window.history.pushState({}, "", url)
  }

  function navigate(next: DashboardView) {
    setView(next)
    setDocumentId(null)
    const url = new URL(window.location.href)
    url.searchParams.delete("document")
    if (next === "users") url.searchParams.set("view", "users")
    else url.searchParams.delete("view")
    window.history.pushState({}, "", url)
  }

  if (me.isLoading)
    return (
      <div className="grid min-h-screen place-items-center">
        <LoaderCircle className="h-7 w-7 animate-spin text-primary" />
      </div>
    )
  if (!me.data) return <LoginPage onLogin={(user) => queryClient.setQueryData(["me"], user)} />

  const currentUser = me.data
  return (
    <div className="min-h-screen">
      <AppHeader
        view={view}
        isAdmin={currentUser.role === "admin"}
        onNavigate={navigate}
        onLogout={() => logoutMutation.mutate()}
      />
      {documentId ? (
        <ReviewPage id={documentId} onBack={() => openDocument(null)} canPublish={currentUser.role === "admin"} />
      ) : view === "users" && currentUser.role === "admin" ? (
        <UsersPage currentUser={currentUser} />
      ) : (
        <DashboardPage onOpen={openDocument} />
      )}
    </div>
  )
}
