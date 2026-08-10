import { useQuery, useQueryClient } from "@tanstack/react-query"
import {
  AlertCircle,
  CheckCircle2,
  ChevronRight,
  FileText,
  LoaderCircle,
  type LucideIcon,
  RefreshCcw,
  Send,
} from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { UploadPanel } from "@/components/upload-panel"
import { getDocuments } from "@/lib/api"
import { statusStyle } from "@/lib/document-status"
import { cn, formatBytes, formatDate } from "@/lib/utils"

export function DashboardPage({ onOpen }: { onOpen: (id: string) => void }) {
  const queryClient = useQueryClient()
  const documents = useQuery({
    queryKey: ["documents"],
    queryFn: getDocuments,
    refetchInterval: (query) =>
      query.state.data?.some((item) => ["queued", "processing"].includes(item.status)) ? 1500 : false,
  })
  const rows = documents.data ?? []
  const totalRecords = rows.reduce((sum, item) => sum + item.recordsExtracted, 0)
  const totalIssues = rows.reduce((sum, item) => sum + item.issuesFound, 0)
  const dashboardStats: Array<{ label: string; value: number; Icon: LucideIcon; iconColor: string; iconBg: string }> = [
    { label: "Documents", value: rows.length, Icon: FileText, iconColor: "text-blue-600", iconBg: "bg-blue-50" },
    {
      label: "Rows extracted",
      value: totalRecords,
      Icon: CheckCircle2,
      iconColor: "text-emerald-600",
      iconBg: "bg-emerald-50",
    },
    {
      label: "Review flags",
      value: totalIssues,
      Icon: AlertCircle,
      iconColor: "text-amber-600",
      iconBg: "bg-amber-50",
    },
  ]

  return (
    <main className="mx-auto w-full max-w-6xl px-4 pb-16 pt-8 sm:px-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold tracking-tight sm:text-3xl">Documents</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Upload, review, and publish timetable data to the MNUelf bot.
        </p>
      </div>
      <section className="mb-6 grid gap-4 sm:grid-cols-3">
        {dashboardStats.map(({ label, value, Icon, iconColor, iconBg }) => (
          <Card key={label}>
            <CardContent className="flex items-center justify-between p-5">
              <div>
                <p className="text-sm text-muted-foreground">{label}</p>
                <p className="mt-1 text-2xl font-bold">{value}</p>
              </div>
              <div className={cn("grid h-10 w-10 place-items-center rounded-xl", iconBg)}>
                <Icon className={cn("h-5 w-5", iconColor)} />
              </div>
            </CardContent>
          </Card>
        ))}
      </section>
      <div className="mb-6">
        <UploadPanel
          onUploaded={(document) => {
            void queryClient.invalidateQueries({ queryKey: ["documents"] })
            onOpen(document.id)
          }}
        />
      </div>
      <Card>
        <CardHeader className="flex-row items-center justify-between space-y-0">
          <div>
            <CardTitle>Recent documents</CardTitle>
            <CardDescription className="mt-1">Processing history and review readiness</CardDescription>
          </div>
          <Button variant="ghost" size="icon" onClick={() => void documents.refetch()} aria-label="Refresh documents">
            <RefreshCcw className={cn("h-4 w-4", documents.isFetching && "animate-spin")} />
          </Button>
        </CardHeader>
        <CardContent>
          {documents.isLoading ? (
            <div className="flex h-40 items-center justify-center text-muted-foreground">
              <LoaderCircle className="mr-2 h-5 w-5 animate-spin" /> Loading documents
            </div>
          ) : rows.length === 0 ? (
            <div className="flex h-40 flex-col items-center justify-center rounded-lg border border-dashed text-center text-muted-foreground">
              <FileText className="mb-3 h-7 w-7" />
              <p className="font-medium text-foreground">No documents yet</p>
              <p className="mt-1 text-sm">Your first upload will appear here.</p>
            </div>
          ) : (
            <div className="divide-y">
              {rows.map((document) => {
                const progress = document.pageCount
                  ? (document.pagesProcessed / document.pageCount) * 100
                  : document.status === "completed"
                    ? 100
                    : 5
                return (
                  <button
                    type="button"
                    key={document.id}
                    onClick={() => onOpen(document.id)}
                    className="group grid w-full grid-cols-[auto_1fr_auto] items-center gap-4 py-4 text-left first:pt-0 last:pb-0"
                  >
                    <div className="grid h-11 w-11 place-items-center rounded-xl bg-secondary text-primary">
                      <FileText className="h-5 w-5" />
                    </div>
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="truncate font-medium">{document.filename}</span>
                        <Badge variant={statusStyle[document.status].variant}>
                          {statusStyle[document.status].label}
                        </Badge>
                        {document.isActive && (
                          <Badge className="gap-1">
                            <Send className="h-3 w-3" /> Live in bot
                          </Badge>
                        )}
                      </div>
                      <div className="mt-1 flex flex-wrap gap-x-3 text-xs text-muted-foreground">
                        <span>{formatBytes(document.sizeBytes)}</span>
                        <span>{document.recordsExtracted} rows</span>
                        <span>{document.issuesFound} flags</span>
                        <span>{formatDate(document.createdAt)}</span>
                      </div>
                      {["queued", "processing"].includes(document.status) && (
                        <Progress value={progress} className="mt-3 max-w-lg" />
                      )}
                    </div>
                    <ChevronRight className="h-5 w-5 text-muted-foreground transition-transform group-hover:translate-x-1 group-hover:text-primary" />
                  </button>
                )
              })}
            </div>
          )}
        </CardContent>
      </Card>
    </main>
  )
}
