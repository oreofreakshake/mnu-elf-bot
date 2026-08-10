import { LayoutDashboard, LogOut, Users } from "lucide-react"
import { Brand } from "@/components/brand"
import { Button } from "@/components/ui/button"

export type DashboardView = "dashboard" | "users"

interface AppHeaderProps {
  view: DashboardView
  isAdmin: boolean
  onNavigate: (view: DashboardView) => void
  onLogout: () => void
}

export function AppHeader({ view, isAdmin, onNavigate, onLogout }: AppHeaderProps) {
  return (
    <header className="sticky top-0 z-30 border-b bg-white/95 backdrop-blur">
      <div className="mx-auto grid h-16 max-w-6xl grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)] items-center gap-3 px-4 sm:px-6">
        <Brand />
        <nav className="flex items-center gap-1">
          <Button variant={view === "dashboard" ? "secondary" : "ghost"} onClick={() => onNavigate("dashboard")}>
            <LayoutDashboard className="h-4 w-4" />
            <span className="hidden sm:inline">Documents</span>
          </Button>
          {isAdmin && (
            <Button variant={view === "users" ? "secondary" : "ghost"} onClick={() => onNavigate("users")}>
              <Users className="h-4 w-4" />
              <span className="hidden sm:inline">Users</span>
            </Button>
          )}
        </nav>
        <Button className="justify-self-end" variant="outline" size="icon" onClick={onLogout} aria-label="Sign out">
          <LogOut className="h-4 w-4" />
        </Button>
      </div>
    </header>
  )
}
