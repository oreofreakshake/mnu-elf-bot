import { useEffect, useMemo, useRef, useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { createColumnHelper, flexRender, getCoreRowModel, getFilteredRowModel, useReactTable } from "@tanstack/react-table"
import {
  AlertCircle,
  ArrowLeft,
  CheckCircle2,
  ChevronRight,
  Clock3,
  Download,
  FileJson,
  FileSearch,
  FileText,
  LayoutDashboard,
  LoaderCircle,
  LogOut,
  RefreshCcw,
  Send,
  Search,
  ShieldCheck,
  Sparkles,
  UploadCloud,
  UserCog,
  Users,
  X,
  type LucideIcon,
} from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Progress } from "@/components/ui/progress"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import {
  activateDocument,
  getAuthConfig,
  getCurrentUser,
  getDocument,
  getDocuments,
  getEntries,
  getIssues,
  getUsers,
  loginForDevelopment,
  loginWithTelegram,
  logout,
  resultUrl,
  retryDocument,
  updateEntry,
  updateUserRole,
  uploadDocument,
} from "@/lib/api"
import { cn, formatBytes, formatDate } from "@/lib/utils"
import type { DocumentRecord, Entry, TelegramAuthData, TelegramUserRecord, UserRole } from "@/types"

declare global {
  interface Window {
    onTelegramAuth?: (user: TelegramAuthData) => void
  }
}

const statusStyle = {
  queued: { label: "Queued", variant: "secondary" as const },
  processing: { label: "Processing", variant: "default" as const },
  completed: { label: "Ready", variant: "success" as const },
  failed: { label: "Failed", variant: "destructive" as const },
}

function Brand() {
  return (
    <div className="flex items-center gap-3">
      <div className="grid h-10 w-10 place-items-center rounded-xl bg-primary text-primary-foreground shadow-lg shadow-primary/25">
        <FileSearch className="h-5 w-5" />
      </div>
      <div>
        <div className="font-bold tracking-tight">Timetable Lens</div>
        <div className="text-xs text-muted-foreground">PDF extraction workspace</div>
      </div>
    </div>
  )
}

function UploadPanel({ onUploaded }: { onUploaded: (document: DocumentRecord) => void }) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [dragging, setDragging] = useState(false)
  const [progress, setProgress] = useState(0)
  const mutation = useMutation({
    mutationFn: (file: File) => uploadDocument(file, setProgress),
    onSuccess: onUploaded,
  })

  function submit(file?: File) {
    if (!file || mutation.isPending) return
    setProgress(0)
    mutation.mutate(file)
  }

  return (
    <Card className="overflow-hidden border-primary/15 bg-gradient-to-br from-white to-violet-50/70">
      <CardContent className="p-4 sm:p-6">
        <div
          className={cn(
            "relative flex min-h-64 cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed p-7 text-center transition-all",
            dragging ? "border-primary bg-primary/5 scale-[.995]" : "border-primary/25 bg-white/65 hover:border-primary/55 hover:bg-white",
          )}
          onClick={() => inputRef.current?.click()}
          onDragEnter={(event) => { event.preventDefault(); setDragging(true) }}
          onDragOver={(event) => event.preventDefault()}
          onDragLeave={() => setDragging(false)}
          onDrop={(event) => {
            event.preventDefault()
            setDragging(false)
            submit(event.dataTransfer.files[0])
          }}
          role="button"
          tabIndex={0}
          onKeyDown={(event) => event.key === "Enter" && inputRef.current?.click()}
        >
          <input ref={inputRef} type="file" accept="application/pdf,.pdf" className="hidden" onChange={(event) => submit(event.target.files?.[0])} />
          <div className="mb-5 grid h-14 w-14 place-items-center rounded-2xl bg-primary/10 text-primary">
            {mutation.isPending ? <LoaderCircle className="h-7 w-7 animate-spin" /> : <UploadCloud className="h-7 w-7" />}
          </div>
          <h2 className="text-xl font-semibold tracking-tight">Drop a timetable PDF here</h2>
          <p className="mt-2 max-w-md text-sm leading-6 text-muted-foreground">
            Native tables are parsed locally. Unclear pages are isolated for review instead of being guessed.
          </p>
          <Button className="mt-5" disabled={mutation.isPending}>
            {mutation.isPending ? `Uploading ${progress}%` : "Choose PDF"}
          </Button>
          {mutation.isPending && <Progress value={progress} className="mt-5 max-w-xs" />}
          {mutation.isError && (
            <div className="mt-4 flex items-center gap-2 text-sm text-red-600">
              <AlertCircle className="h-4 w-4" />
              {mutation.error instanceof Error ? mutation.error.message : "Upload failed"}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}

function Dashboard({ onOpen }: { onOpen: (id: string) => void }) {
  const queryClient = useQueryClient()
  const documents = useQuery({
    queryKey: ["documents"],
    queryFn: getDocuments,
    refetchInterval: (query) => query.state.data?.some((item) => ["queued", "processing"].includes(item.status)) ? 1500 : false,
  })
  const rows = documents.data ?? []
  const totalRecords = rows.reduce((sum, item) => sum + item.recordsExtracted, 0)
  const totalIssues = rows.reduce((sum, item) => sum + item.issuesFound, 0)
  const dashboardStats: Array<{
    label: string
    value: number
    Icon: LucideIcon
    iconColor: string
    iconBg: string
  }> = [
    { label: "Documents", value: rows.length, Icon: FileText, iconColor: "text-blue-600", iconBg: "bg-blue-50" },
    { label: "Rows extracted", value: totalRecords, Icon: CheckCircle2, iconColor: "text-emerald-600", iconBg: "bg-emerald-50" },
    { label: "Review flags", value: totalIssues, Icon: AlertCircle, iconColor: "text-amber-600", iconBg: "bg-amber-50" },
  ]

  return (
    <main className="mx-auto w-full max-w-7xl px-4 pb-16 pt-10 sm:px-6 lg:px-8">
      <section className="mb-10 grid gap-8 lg:grid-cols-[1.05fr_.95fr] lg:items-center">
        <div className="py-4">
          <Badge className="mb-5 gap-1.5"><Sparkles className="h-3.5 w-3.5" /> Deterministic extraction</Badge>
          <h1 className="max-w-3xl text-balance text-4xl font-bold tracking-[-.04em] sm:text-5xl lg:text-6xl">
            Turn complex timetables into <span className="text-primary">trusted JSON.</span>
          </h1>
          <p className="mt-5 max-w-2xl text-base leading-7 text-muted-foreground sm:text-lg">
            Upload, validate every extracted row, correct flagged values, and publish trusted schedules directly to the Telegram bot.
          </p>
          <div className="mt-7 flex flex-wrap gap-5 text-sm text-muted-foreground">
            <span className="flex items-center gap-2"><ShieldCheck className="h-4 w-4 text-emerald-600" /> Reviewed results</span>
            <span className="flex items-center gap-2"><FileJson className="h-4 w-4 text-primary" /> JSON-ready exports</span>
            <span className="flex items-center gap-2"><Clock3 className="h-4 w-4 text-blue-600" /> Resumable jobs</span>
          </div>
        </div>
        <UploadPanel
          onUploaded={(document) => {
            void queryClient.invalidateQueries({ queryKey: ["documents"] })
            onOpen(document.id)
          }}
        />
      </section>

      <section className="mb-6 grid gap-4 sm:grid-cols-3">
        {dashboardStats.map(({ label, value, Icon, iconColor, iconBg }) => (
          <Card key={label} className="shadow-none">
            <CardContent className="flex items-center justify-between p-5">
              <div><p className="text-sm text-muted-foreground">{label}</p><p className="mt-1 text-2xl font-bold">{value}</p></div>
              <div className={cn("grid h-10 w-10 place-items-center rounded-xl", iconBg)}><Icon className={cn("h-5 w-5", iconColor)} /></div>
            </CardContent>
          </Card>
        ))}
      </section>

      <Card className="shadow-none">
        <CardHeader className="flex-row items-center justify-between space-y-0">
          <div><CardTitle>Recent documents</CardTitle><CardDescription className="mt-1">Processing history and review readiness</CardDescription></div>
          <Button variant="ghost" size="icon" onClick={() => void documents.refetch()} aria-label="Refresh documents"><RefreshCcw className={cn("h-4 w-4", documents.isFetching && "animate-spin")} /></Button>
        </CardHeader>
        <CardContent>
          {documents.isLoading ? (
            <div className="flex h-40 items-center justify-center text-muted-foreground"><LoaderCircle className="mr-2 h-5 w-5 animate-spin" /> Loading documents</div>
          ) : rows.length === 0 ? (
            <div className="flex h-40 flex-col items-center justify-center rounded-lg border border-dashed text-center text-muted-foreground"><FileText className="mb-3 h-7 w-7" /><p className="font-medium text-foreground">No documents yet</p><p className="mt-1 text-sm">Your first upload will appear here.</p></div>
          ) : (
            <div className="divide-y">
              {rows.map((document) => {
                const progress = document.pageCount ? (document.pagesProcessed / document.pageCount) * 100 : document.status === "completed" ? 100 : 5
                return (
                  <button key={document.id} onClick={() => onOpen(document.id)} className="group grid w-full grid-cols-[auto_1fr_auto] items-center gap-4 py-4 text-left first:pt-0 last:pb-0">
                    <div className="grid h-11 w-11 place-items-center rounded-xl bg-secondary text-primary"><FileText className="h-5 w-5" /></div>
                    <div className="min-w-0">
                      <div className="flex items-center gap-2"><span className="truncate font-medium">{document.filename}</span><Badge variant={statusStyle[document.status].variant}>{statusStyle[document.status].label}</Badge>{document.isActive && <Badge className="gap-1"><Send className="h-3 w-3" /> Live in bot</Badge>}</div>
                      <div className="mt-1 flex flex-wrap gap-x-3 text-xs text-muted-foreground"><span>{formatBytes(document.sizeBytes)}</span><span>{document.recordsExtracted} rows</span><span>{document.issuesFound} flags</span><span>{formatDate(document.createdAt)}</span></div>
                      {["queued", "processing"].includes(document.status) && <Progress value={progress} className="mt-3 max-w-lg" />}
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

const columnHelper = createColumnHelper<Entry>()

function ReviewWorkspace({ id, onBack, canPublish }: { id: string; onBack: () => void; canPublish: boolean }) {
  const queryClient = useQueryClient()
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [filter, setFilter] = useState("")
  const [issuesOnly, setIssuesOnly] = useState(false)
  const [draft, setDraft] = useState<Entry | null>(null)
  const document = useQuery({
    queryKey: ["document", id],
    queryFn: () => getDocument(id),
    refetchInterval: (query) => ["queued", "processing"].includes(query.state.data?.status ?? "") ? 1200 : false,
  })
  const entries = useQuery({ queryKey: ["entries", id], queryFn: () => getEntries(id), enabled: document.data?.status === "completed" })
  const issues = useQuery({ queryKey: ["issues", id], queryFn: () => getIssues(id), enabled: document.data?.status === "completed" })
  const openIssueEntryIds = useMemo(() => new Set((issues.data ?? []).filter((item) => item.status === "open" && item.entryId).map((item) => item.entryId!)), [issues.data])
  const shownEntries = useMemo(() => issuesOnly ? (entries.data ?? []).filter((entry) => openIssueEntryIds.has(entry.id) || !entry.valid) : entries.data ?? [], [entries.data, issuesOnly, openIssueEntryIds])
  const selected = draft ?? shownEntries.find((entry) => entry.id === selectedId) ?? shownEntries[0] ?? null

  const saveMutation = useMutation({
    mutationFn: updateEntry,
    onSuccess: (saved) => {
      queryClient.setQueryData<Entry[]>(["entries", id], (current) => current?.map((entry) => entry.id === saved.id ? saved : entry))
      void queryClient.invalidateQueries({ queryKey: ["issues", id] })
      setDraft(null)
    },
  })
  const retryMutation = useMutation({ mutationFn: () => retryDocument(id), onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["document", id] }) })
  const activateMutation = useMutation({
    mutationFn: () => activateDocument(id),
    onSuccess: (published) => {
      queryClient.setQueryData(["document", id], published)
      void queryClient.invalidateQueries({ queryKey: ["documents"] })
    },
  })

  const columns = useMemo(() => [
    columnHelper.accessor("subCode", { header: "Code", cell: (info) => <span className="font-semibold text-foreground">{info.getValue()}</span> }),
    columnHelper.accessor("subjectName", { header: "Subject", cell: (info) => <span className="block max-w-64 truncate">{info.getValue()}</span> }),
    columnHelper.accessor("sessionType", { header: "Type", cell: (info) => <Badge variant="secondary">{info.getValue()}</Badge> }),
    columnHelper.accessor("lecturer", { header: "Lecturer", cell: (info) => <span className="block max-w-48 truncate">{info.getValue()}</span> }),
    columnHelper.accessor("time", { header: "Time" }),
    columnHelper.accessor("sourcePage", { header: "Page", cell: (info) => `p. ${info.getValue()}` }),
    columnHelper.display({ id: "status", header: "Check", cell: ({ row }) => openIssueEntryIds.has(row.original.id) || !row.original.valid ? <Badge variant="warning">Review</Badge> : row.original.reviewed ? <Badge variant="success">Verified</Badge> : <CheckCircle2 className="h-4 w-4 text-emerald-600" /> }),
  ], [openIssueEntryIds])

  const table = useReactTable({
    data: shownEntries,
    columns,
    state: { globalFilter: filter },
    onGlobalFilterChange: setFilter,
    getCoreRowModel: getCoreRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
  })

  if (document.isLoading || !document.data) return <div className="grid min-h-screen place-items-center"><LoaderCircle className="h-7 w-7 animate-spin text-primary" /></div>
  const doc = document.data
  const progress = doc.pageCount ? (doc.pagesProcessed / doc.pageCount) * 100 : doc.status === "completed" ? 100 : 4
  const openIssues = (issues.data ?? []).filter((item) => item.status === "open").length

  return (
    <main className="mx-auto w-full max-w-[1800px] px-4 pb-10 pt-6 sm:px-6">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
        <div className="flex min-w-0 items-center gap-3">
          <Button variant="outline" size="icon" onClick={onBack} aria-label="Back to dashboard"><ArrowLeft className="h-4 w-4" /></Button>
          <div className="min-w-0"><h1 className="truncate text-xl font-bold tracking-tight">{doc.filename}</h1><p className="mt-1 text-sm text-muted-foreground">{formatBytes(doc.sizeBytes)} · uploaded {formatDate(doc.createdAt)}</p></div>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant={statusStyle[doc.status].variant}>{statusStyle[doc.status].label}</Badge>
          {doc.status === "completed" && (
            <>
              {doc.isActive ? (
                <Badge className="h-10 gap-1.5 px-4"><Send className="h-3.5 w-3.5" /> Live in Telegram bot</Badge>
              ) : canPublish ? (
                <Button
                  variant="outline"
                  disabled={openIssues > 0 || activateMutation.isPending}
                  onClick={() => activateMutation.mutate()}
                  title={openIssues ? "Resolve all review flags before publishing" : "Publish this timetable to the bot"}
                >
                  {activateMutation.isPending ? <LoaderCircle className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
                  Publish to Telegram
                </Button>
              ) : null}
              <Button asChild><a href={resultUrl(id)}><Download className="h-4 w-4" /> Download JSON</a></Button>
            </>
          )}
        </div>
      </div>

      {doc.status !== "completed" ? (
        <Card className="mx-auto mt-20 max-w-2xl overflow-hidden">
          <CardHeader className="items-center text-center"><div className="mb-3 grid h-14 w-14 place-items-center rounded-2xl bg-primary/10 text-primary">{doc.status === "failed" ? <X className="h-7 w-7" /> : <LoaderCircle className="h-7 w-7 animate-spin" />}</div><CardTitle>{doc.status === "failed" ? "Processing stopped" : "Reading your timetable"}</CardTitle><CardDescription>{doc.error ?? doc.stage}</CardDescription></CardHeader>
          <CardContent><Progress value={progress} className="h-2.5" /><div className="mt-3 flex justify-between text-xs text-muted-foreground"><span>{doc.pagesProcessed} pages processed</span><span>{doc.pageCount || "—"} total pages</span></div>{doc.status === "failed" && <Button className="mt-6 w-full" onClick={() => retryMutation.mutate()} disabled={retryMutation.isPending}><RefreshCcw className="h-4 w-4" /> Retry extraction</Button>}</CardContent>
        </Card>
      ) : (
        <>
          <section className="mb-5 grid gap-3 sm:grid-cols-4">
            {[["Pages", doc.pageCount], ["Rows", doc.recordsExtracted], ["Review flags", openIssues], ["Confidence", openIssues ? "Needs review" : "Validated"]].map(([label, value]) => <Card key={String(label)} className="shadow-none"><CardContent className="p-4"><p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">{String(label)}</p><p className="mt-1 text-xl font-bold">{String(value)}</p></CardContent></Card>)}
          </section>

          <div className="grid gap-5 xl:grid-cols-[minmax(0,1.45fr)_minmax(360px,.55fr)]">
            <Card className="min-w-0 shadow-none">
              <CardHeader className="border-b p-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div><CardTitle>Extracted schedule</CardTitle><CardDescription className="mt-1">Select a row to inspect or correct its extracted values.</CardDescription></div>
                  <div className="flex items-center gap-2"><div className="relative"><Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" /><Input value={filter} onChange={(event) => setFilter(event.target.value)} placeholder="Search rows…" className="w-56 pl-9" /></div><Button variant={issuesOnly ? "default" : "outline"} onClick={() => setIssuesOnly(!issuesOnly)}><AlertCircle className="h-4 w-4" /> Flags</Button></div>
                </div>
              </CardHeader>
              <CardContent className="p-0">
                <div className="max-h-[720px] overflow-auto">
                  <Table>
                    <TableHeader className="sticky top-0 z-10 bg-card"><TableRow>{table.getHeaderGroups()[0]?.headers.map((header) => <TableHead key={header.id}>{flexRender(header.column.columnDef.header, header.getContext())}</TableHead>)}</TableRow></TableHeader>
                    <TableBody>{table.getRowModel().rows.map((row) => <TableRow key={row.id} onClick={() => { setSelectedId(row.original.id); setDraft(null) }} className={cn("cursor-pointer", selected?.id === row.original.id && "bg-primary/5 hover:bg-primary/10")}><>{row.getVisibleCells().map((cell) => <TableCell key={cell.id}>{flexRender(cell.column.columnDef.cell, cell.getContext())}</TableCell>)}</></TableRow>)}</TableBody>
                  </Table>
                  {!table.getRowModel().rows.length && <div className="grid h-48 place-items-center text-sm text-muted-foreground">No matching rows</div>}
                </div>
              </CardContent>
            </Card>

            <div className="space-y-5 xl:sticky xl:top-5 xl:self-start">
              {selected && (
                <Card className="shadow-none"><CardHeader className="p-4 pb-3"><CardTitle className="text-base">Verify extracted values</CardTitle><CardDescription>Edits are saved as reviewed corrections.</CardDescription></CardHeader><CardContent className="grid gap-3 p-4 pt-0">
                  {[
                    ["Subject code", "subCode"], ["Subject name", "subjectName"], ["Session type", "sessionType"], ["Lecturer", "lecturer"], ["Time", "time"], ["Room", "room"],
                  ].map(([label, key]) => <label key={key} className="grid gap-1.5 text-xs font-medium text-muted-foreground"><span>{label}</span><Input value={String(selected[key as keyof Entry])} onChange={(event) => setDraft({ ...selected, [key]: event.target.value })} /></label>)}
                  <div className="mt-2 flex gap-2"><Button className="flex-1" disabled={!draft || saveMutation.isPending} onClick={() => draft && saveMutation.mutate(draft)}>{saveMutation.isPending ? <LoaderCircle className="h-4 w-4 animate-spin" /> : <ShieldCheck className="h-4 w-4" />} Save & verify</Button>{draft && <Button variant="outline" onClick={() => setDraft(null)}>Reset</Button>}</div>
                </CardContent></Card>
              )}
            </div>
          </div>
        </>
      )}
    </main>
  )
}

function LoginScreen({ onLogin }: { onLogin: (user: TelegramUserRecord) => void }) {
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
  }, [config.data?.telegramBotUsername, isLocal])

  return (
    <main className="grid min-h-screen place-items-center px-4 py-12">
      <Card className="w-full max-w-md overflow-hidden border-primary/15 shadow-xl shadow-primary/10">
        <CardHeader className="items-center border-b bg-gradient-to-br from-white to-violet-50/80 py-8 text-center">
          <Brand />
          <CardTitle className="mt-6 text-2xl">Administrator sign in</CardTitle>
          <CardDescription className="max-w-sm leading-6">Use your Telegram account. Only approved reviewers and administrators can open this workspace.</CardDescription>
        </CardHeader>
        <CardContent className="grid min-h-36 place-items-center p-6 text-center">
          {config.isLoading ? <LoaderCircle className="h-6 w-6 animate-spin text-primary" /> : !isLocal && config.data?.telegramBotUsername ? <div ref={widgetRef} /> : !isLocal ? <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm leading-6 text-amber-900">Set <code>TELEGRAM_BOT_USERNAME</code> and <code>ADMIN_TELEGRAM_IDS</code> in the root <code>.env</code>, then restart the API.</div> : <div className="flex items-center gap-2 text-sm text-muted-foreground"><ShieldCheck className="h-4 w-4 text-emerald-600" /> Local access is restricted by the development token.</div>}
          {mutation.isError && <div className="mt-4 flex items-center gap-2 text-sm text-red-600"><AlertCircle className="h-4 w-4" /> Sign-in failed or dashboard access has not been granted.</div>}
          {isLocal && <div className="mt-6 w-full border-t pt-5"><p className="mb-3 text-xs font-medium uppercase tracking-wider text-muted-foreground">Local development</p><div className="flex gap-2"><Input type="password" value={developmentToken} onChange={(event) => setDevelopmentToken(event.target.value)} placeholder="Development access token" onKeyDown={(event) => event.key === "Enter" && developmentToken && developmentMutation.mutate(developmentToken)} /><Button disabled={!developmentToken || developmentMutation.isPending} onClick={() => developmentMutation.mutate(developmentToken)}>{developmentMutation.isPending ? <LoaderCircle className="h-4 w-4 animate-spin" /> : "Sign in"}</Button></div>{developmentMutation.isError && <p className="mt-2 text-sm text-red-600">Invalid development access token.</p>}<p className="mt-3 text-xs leading-5 text-muted-foreground">This fallback only works through localhost and is disabled in secure production mode.</p></div>}
        </CardContent>
      </Card>
    </main>
  )
}

function UsersPage({ currentUser }: { currentUser: TelegramUserRecord }) {
  const queryClient = useQueryClient()
  const users = useQuery({ queryKey: ["users"], queryFn: getUsers })
  const roleMutation = useMutation({
    mutationFn: ({ id, role }: { id: string; role: UserRole }) => updateUserRole(id, role),
    onSuccess: (updated) => queryClient.setQueryData<TelegramUserRecord[]>(["users"], (rows) => rows?.map((user) => user.id === updated.id ? updated : user)),
  })
  const rows = users.data ?? []
  const reviewers = rows.filter((user) => user.role === "reviewer").length
  const administrators = rows.filter((user) => user.role === "admin").length

  return (
    <main className="mx-auto w-full max-w-7xl px-4 pb-16 pt-10 sm:px-6 lg:px-8">
      <div className="mb-8"><Badge className="mb-4 gap-1.5"><UserCog className="h-3.5 w-3.5" /> Access control</Badge><h1 className="text-3xl font-bold tracking-tight">Telegram users</h1><p className="mt-2 text-muted-foreground">Review bot activity, selected subjects, and dashboard permissions.</p></div>
      <section className="mb-6 grid gap-4 sm:grid-cols-3">
        {[["Bot users", rows.length], ["Reviewers", reviewers], ["Administrators", administrators]].map(([label, value]) => <Card key={String(label)} className="shadow-none"><CardContent className="p-5"><p className="text-sm text-muted-foreground">{label}</p><p className="mt-1 text-2xl font-bold">{value}</p></CardContent></Card>)}
      </section>
      <Card className="overflow-hidden shadow-none">
        <CardHeader><CardTitle>User permissions</CardTitle><CardDescription>Telegram login verifies identity; this role determines dashboard access.</CardDescription></CardHeader>
        <CardContent className="p-0">
          {users.isLoading ? <div className="grid h-48 place-items-center"><LoaderCircle className="h-6 w-6 animate-spin text-primary" /></div> : (
            <div className="overflow-x-auto"><Table><TableHeader><TableRow><TableHead>User</TableHead><TableHead>Telegram ID</TableHead><TableHead>Subjects</TableHead><TableHead>Last active</TableHead><TableHead className="w-44">Role</TableHead></TableRow></TableHeader><TableBody>
              {rows.map((user) => {
                const name = [user.firstName, user.lastName].filter(Boolean).join(" ") || user.username || "Telegram user"
                return <TableRow key={user.id}><TableCell><div className="font-medium">{name}</div><div className="text-xs text-muted-foreground">{user.username ? `@${user.username}` : "No username"}</div></TableCell><TableCell className="font-mono text-xs">{user.telegramUserId}</TableCell><TableCell><div className="flex max-w-sm flex-wrap gap-1">{user.subjects.length ? user.subjects.map((subject) => <Badge key={subject.id} variant="secondary">{subject.subCode} · {subject.course}</Badge>) : <span className="text-sm text-muted-foreground">None</span>}</div></TableCell><TableCell className="text-sm text-muted-foreground">{formatDate(user.lastSeenAt)}</TableCell><TableCell><select value={user.role} disabled={user.id === currentUser.id || roleMutation.isPending} onChange={(event) => roleMutation.mutate({ id: user.id, role: event.target.value as UserRole })} className="h-9 w-full rounded-md border bg-background px-3 text-sm outline-none focus:ring-2 focus:ring-ring"><option value="user">User</option><option value="reviewer">Reviewer</option><option value="admin">Admin</option></select></TableCell></TableRow>
              })}
            </TableBody></Table></div>
          )}
        </CardContent>
      </Card>
    </main>
  )
}

export default function App() {
  const queryClient = useQueryClient()
  const me = useQuery({ queryKey: ["me"], queryFn: getCurrentUser, retry: false })
  const [documentId, setDocumentId] = useState<string | null>(() => new URLSearchParams(window.location.search).get("document"))
  const [view, setView] = useState<"dashboard" | "users">(() => new URLSearchParams(window.location.search).get("view") === "users" ? "users" : "dashboard")
  const logoutMutation = useMutation({ mutationFn: logout, onSuccess: () => { queryClient.clear(); setDocumentId(null); setView("dashboard") } })
  function open(id: string | null) {
    setDocumentId(id)
    const url = new URL(window.location.href)
    if (id) url.searchParams.set("document", id)
    else url.searchParams.delete("document")
    window.history.pushState({}, "", url)
  }
  function navigate(next: "dashboard" | "users") {
    setView(next)
    setDocumentId(null)
    const url = new URL(window.location.href)
    url.searchParams.delete("document")
    if (next === "users") url.searchParams.set("view", "users")
    else url.searchParams.delete("view")
    window.history.pushState({}, "", url)
  }
  if (me.isLoading) return <div className="grid min-h-screen place-items-center"><LoaderCircle className="h-7 w-7 animate-spin text-primary" /></div>
  if (!me.data) return <LoginScreen onLogin={(user) => queryClient.setQueryData(["me"], user)} />
  const currentUser = me.data
  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-30 border-b bg-white/85 backdrop-blur-xl"><div className="mx-auto flex min-h-16 max-w-[1800px] flex-wrap items-center justify-between gap-3 px-4 py-2 sm:px-6"><Brand /><nav className="flex items-center gap-1"><Button variant={view === "dashboard" ? "secondary" : "ghost"} onClick={() => navigate("dashboard")}><LayoutDashboard className="h-4 w-4" /> Documents</Button>{currentUser.role === "admin" && <Button variant={view === "users" ? "secondary" : "ghost"} onClick={() => navigate("users")}><Users className="h-4 w-4" /> Users</Button>}</nav><div className="flex items-center gap-2"><div className="hidden text-right sm:block"><p className="text-sm font-medium">{currentUser.firstName || currentUser.username || "Administrator"}</p><p className="text-xs capitalize text-muted-foreground">{currentUser.role}</p></div><Button variant="outline" size="icon" onClick={() => logoutMutation.mutate()} aria-label="Sign out"><LogOut className="h-4 w-4" /></Button></div></div></header>
      {documentId ? <ReviewWorkspace id={documentId} onBack={() => open(null)} canPublish={currentUser.role === "admin"} /> : view === "users" && currentUser.role === "admin" ? <UsersPage currentUser={currentUser} /> : <Dashboard onOpen={(id) => open(id)} />}
    </div>
  )
}
