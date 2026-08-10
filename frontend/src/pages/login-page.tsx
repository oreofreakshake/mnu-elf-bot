import { useMutation, useQuery } from "@tanstack/react-query"
import { AlertCircle, LoaderCircle } from "lucide-react"
import { useEffect, useRef, useState } from "react"
import { Brand } from "@/components/brand"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { getAuthConfig, loginForDevelopment, loginWithTelegram } from "@/lib/api"
import type { TelegramAuthData, TelegramUserRecord } from "@/types"

declare global {
  interface Window {
    onTelegramAuth?: (user: TelegramAuthData) => void
  }
}

export function LoginPage({ onLogin }: { onLogin: (user: TelegramUserRecord) => void }) {
  const widgetRef = useRef<HTMLDivElement>(null)
  const [developmentToken, setDevelopmentToken] = useState("")
  const config = useQuery({ queryKey: ["auth-config"], queryFn: getAuthConfig })
  const mutation = useMutation({ mutationFn: loginWithTelegram, onSuccess: onLogin })
  const developmentMutation = useMutation({ mutationFn: loginForDevelopment, onSuccess: onLogin })
  const isLocal = ["localhost", "127.0.0.1", "::1"].includes(window.location.hostname)

  useEffect(() => {
    const username = config.data?.telegramBotUsername
    if (isLocal || !username || !widgetRef.current) return
    window.onTelegramAuth = (user) => mutation.mutate(user)
    const script = document.createElement("script")
    script.src = "https://telegram.org/js/telegram-widget.js?22"
    script.async = true
    script.setAttribute("data-telegram-login", username.replace(/^@/, ""))
    script.setAttribute("data-size", "large")
    script.setAttribute("data-radius", "10")
    script.setAttribute("data-request-access", "write")
    script.setAttribute("data-onauth", "window.onTelegramAuth(user)")
    widgetRef.current.replaceChildren(script)
    return () => {
      delete window.onTelegramAuth
      widgetRef.current?.replaceChildren()
    }
  }, [config.data?.telegramBotUsername, isLocal, mutation.mutate])

  return (
    <main className="grid min-h-screen place-items-center px-5 py-12">
      <section className="w-full max-w-sm text-center">
        <h1 className="mt-8 text-2xl font-bold tracking-tight">Sign in</h1>
        <p className="mt-2 text-sm text-muted-foreground">Manage and publish MNU timetable data.</p>

        <div className="mt-8 grid place-items-center">
          {config.isLoading ? (
            <LoaderCircle className="h-6 w-6 animate-spin text-primary" />
          ) : isLocal ? (
            <div className="flex w-full gap-2">
              <Input
                type="password"
                value={developmentToken}
                onChange={(event) => setDevelopmentToken(event.target.value)}
                placeholder="Development access token"
                onKeyDown={(event) =>
                  event.key === "Enter" && developmentToken && developmentMutation.mutate(developmentToken)
                }
              />
              <Button
                className="shrink-0"
                disabled={!developmentToken || developmentMutation.isPending}
                onClick={() => developmentMutation.mutate(developmentToken)}
              >
                {developmentMutation.isPending ? <LoaderCircle className="h-4 w-4 animate-spin" /> : "Sign in"}
              </Button>
            </div>
          ) : config.data?.telegramBotUsername ? (
            <div ref={widgetRef} />
          ) : (
            <p className="text-sm text-muted-foreground">Telegram login is not configured.</p>
          )}
        </div>
        {(mutation.isError || developmentMutation.isError) && (
          <p className="mt-3 flex items-center justify-center gap-2 text-sm text-red-600">
            <AlertCircle className="h-4 w-4" /> Sign-in failed.
          </p>
        )}
      </section>
    </main>
  )
}
