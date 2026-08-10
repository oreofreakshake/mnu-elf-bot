import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import {
  createColumnHelper,
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  useReactTable,
} from "@tanstack/react-table"
import {
  AlertCircle,
  ArrowLeft,
  CheckCircle2,
  LoaderCircle,
  RefreshCcw,
  Search,
  Send,
  ShieldCheck,
  X,
} from "lucide-react"
import { useMemo, useState } from "react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Progress } from "@/components/ui/progress"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { activateDocument, getDocument, getEntries, getIssues, retryDocument, updateEntry } from "@/lib/api"
import { statusStyle } from "@/lib/document-status"
import { cn, formatBytes, formatDate } from "@/lib/utils"
import type { Entry } from "@/types"

const columnHelper = createColumnHelper<Entry>()

export function ReviewPage({ id, onBack, canPublish }: { id: string; onBack: () => void; canPublish: boolean }) {
  const queryClient = useQueryClient()
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [filter, setFilter] = useState("")
  const [issuesOnly, setIssuesOnly] = useState(false)
  const [draft, setDraft] = useState<Entry | null>(null)
  const document = useQuery({
    queryKey: ["document", id],
    queryFn: () => getDocument(id),
    refetchInterval: (query) => (["queued", "processing"].includes(query.state.data?.status ?? "") ? 1200 : false),
  })
  const entries = useQuery({
    queryKey: ["entries", id],
    queryFn: () => getEntries(id),
    enabled: document.data?.status === "completed",
  })
  const issues = useQuery({
    queryKey: ["issues", id],
    queryFn: () => getIssues(id),
    enabled: document.data?.status === "completed",
  })
  const openIssueEntryIds = useMemo(
    () =>
      new Set((issues.data ?? []).flatMap((item) => (item.status === "open" && item.entryId ? [item.entryId] : []))),
    [issues.data],
  )
  const shownEntries = useMemo(
    () =>
      issuesOnly
        ? (entries.data ?? []).filter((entry) => openIssueEntryIds.has(entry.id) || !entry.valid)
        : (entries.data ?? []),
    [entries.data, issuesOnly, openIssueEntryIds],
  )
  const selected = draft ?? shownEntries.find((entry) => entry.id === selectedId) ?? shownEntries[0] ?? null

  const saveMutation = useMutation({
    mutationFn: updateEntry,
    onSuccess: (saved) => {
      queryClient.setQueryData<Entry[]>(["entries", id], (current) =>
        current?.map((entry) => (entry.id === saved.id ? saved : entry)),
      )
      void queryClient.invalidateQueries({ queryKey: ["issues", id] })
      setDraft(null)
    },
  })
  const retryMutation = useMutation({
    mutationFn: () => retryDocument(id),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["document", id] }),
  })
  const activateMutation = useMutation({
    mutationFn: () => activateDocument(id),
    onSuccess: (published) => {
      queryClient.setQueryData(["document", id], published)
      void queryClient.invalidateQueries({ queryKey: ["documents"] })
    },
  })

  const columns = useMemo(
    () => [
      columnHelper.accessor("subCode", {
        header: "Code",
        cell: (info) => <span className="font-semibold text-foreground">{info.getValue()}</span>,
      }),
      columnHelper.accessor("subjectName", {
        header: "Subject",
        cell: (info) => <span className="block max-w-64 truncate">{info.getValue()}</span>,
      }),
      columnHelper.accessor("sessionType", {
        header: "Type",
        cell: (info) => <Badge variant="secondary">{info.getValue()}</Badge>,
      }),
      columnHelper.accessor("lecturer", {
        header: "Lecturer",
        cell: (info) => <span className="block max-w-48 truncate">{info.getValue()}</span>,
      }),
      columnHelper.accessor("time", { header: "Time" }),
      columnHelper.accessor("sourcePage", { header: "Page", cell: (info) => `p. ${info.getValue()}` }),
      columnHelper.display({
        id: "status",
        header: "Check",
        cell: ({ row }) =>
          openIssueEntryIds.has(row.original.id) || !row.original.valid ? (
            <Badge variant="warning">Review</Badge>
          ) : row.original.reviewed ? (
            <Badge variant="success">Verified</Badge>
          ) : (
            <CheckCircle2 className="h-4 w-4 text-emerald-600" />
          ),
      }),
    ],
    [openIssueEntryIds],
  )

  const table = useReactTable({
    data: shownEntries,
    columns,
    state: { globalFilter: filter },
    onGlobalFilterChange: setFilter,
    getCoreRowModel: getCoreRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
  })

  if (document.isLoading || !document.data)
    return (
      <div className="grid min-h-screen place-items-center">
        <LoaderCircle className="h-7 w-7 animate-spin text-primary" />
      </div>
    )
  const doc = document.data
  const progress = doc.pageCount ? (doc.pagesProcessed / doc.pageCount) * 100 : doc.status === "completed" ? 100 : 4
  const openIssues = (issues.data ?? []).filter((item) => item.status === "open").length
  const selectedIsVerified = Boolean(selected?.reviewed && !draft)

  return (
    <main className="mx-auto w-full max-w-[1800px] px-4 pb-10 pt-6 sm:px-6">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
        <div className="flex min-w-0 items-center gap-3">
          <Button variant="outline" size="icon" onClick={onBack} aria-label="Back to dashboard">
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div className="min-w-0">
            <h1 className="truncate text-xl font-bold tracking-tight">{doc.filename}</h1>
            <p className="mt-1 text-sm text-muted-foreground">
              {formatBytes(doc.sizeBytes)} · uploaded {formatDate(doc.createdAt)}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {!doc.isActive && <Badge variant={statusStyle[doc.status].variant}>{statusStyle[doc.status].label}</Badge>}
          {doc.status === "completed" &&
            (doc.isActive ? (
              <Badge className="h-10 gap-1.5 px-4">
                <Send className="h-3.5 w-3.5" /> Live in Telegram bot
              </Badge>
            ) : canPublish ? (
              <Button
                variant="outline"
                disabled={openIssues > 0 || activateMutation.isPending}
                onClick={() => activateMutation.mutate()}
                title={openIssues ? "Resolve all review flags before publishing" : "Publish this timetable to the bot"}
              >
                {activateMutation.isPending ? (
                  <LoaderCircle className="h-4 w-4 animate-spin" />
                ) : (
                  <Send className="h-4 w-4" />
                )}{" "}
                Publish to Telegram
              </Button>
            ) : null)}
        </div>
      </div>

      {doc.status !== "completed" ? (
        <Card className="mx-auto mt-20 max-w-2xl overflow-hidden">
          <CardHeader className="items-center text-center">
            <div className="mb-3 grid h-14 w-14 place-items-center rounded-2xl bg-primary/10 text-primary">
              {doc.status === "failed" ? <X className="h-7 w-7" /> : <LoaderCircle className="h-7 w-7 animate-spin" />}
            </div>
            <CardTitle>{doc.status === "failed" ? "Processing stopped" : "Reading your timetable"}</CardTitle>
            <CardDescription>{doc.error ?? doc.stage}</CardDescription>
          </CardHeader>
          <CardContent>
            <Progress value={progress} className="h-2.5" />
            <div className="mt-3 flex justify-between text-xs text-muted-foreground">
              <span>{doc.pagesProcessed} pages processed</span>
              <span>{doc.pageCount || "—"} total pages</span>
            </div>
            {doc.status === "failed" && (
              <Button className="mt-6 w-full" onClick={() => retryMutation.mutate()} disabled={retryMutation.isPending}>
                <RefreshCcw className="h-4 w-4" /> Retry extraction
              </Button>
            )}
          </CardContent>
        </Card>
      ) : (
        <>
          <section className="mb-5 grid gap-3 sm:grid-cols-4">
            {[
              ["Pages", doc.pageCount],
              ["Rows", doc.recordsExtracted],
              ["Review flags", openIssues],
              ["Confidence", openIssues ? "Needs review" : "Validated"],
            ].map(([label, value]) => (
              <Card key={String(label)}>
                <CardContent className="p-4">
                  <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">{String(label)}</p>
                  <p className="mt-1 text-xl font-bold">{String(value)}</p>
                </CardContent>
              </Card>
            ))}
          </section>

          <div className="grid gap-5 xl:grid-cols-[minmax(0,1.45fr)_minmax(360px,.55fr)]">
            <Card className="min-w-0">
              <CardHeader className="border-b p-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <CardTitle>Extracted schedule</CardTitle>
                    <CardDescription className="mt-1">
                      Select a row to inspect or correct its extracted values.
                    </CardDescription>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="relative">
                      <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                      <Input
                        value={filter}
                        onChange={(event) => setFilter(event.target.value)}
                        placeholder="Search rows…"
                        className="w-56 pl-9"
                      />
                    </div>
                    <Button variant={issuesOnly ? "default" : "outline"} onClick={() => setIssuesOnly(!issuesOnly)}>
                      <AlertCircle className="h-4 w-4" /> Flags
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="p-0">
                <div className="max-h-[720px] overflow-auto">
                  <Table>
                    <TableHeader className="sticky top-0 z-10 bg-card">
                      <TableRow>
                        {table.getHeaderGroups()[0]?.headers.map((header) => (
                          <TableHead key={header.id}>
                            {flexRender(header.column.columnDef.header, header.getContext())}
                          </TableHead>
                        ))}
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {table.getRowModel().rows.map((row) => (
                        <TableRow
                          key={row.id}
                          onClick={() => {
                            setSelectedId(row.original.id)
                            setDraft(null)
                          }}
                          className={cn(
                            "cursor-pointer",
                            selected?.id === row.original.id && "bg-primary/5 hover:bg-primary/10",
                          )}
                        >
                          {row.getVisibleCells().map((cell) => (
                            <TableCell key={cell.id}>
                              {flexRender(cell.column.columnDef.cell, cell.getContext())}
                            </TableCell>
                          ))}
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                  {!table.getRowModel().rows.length && (
                    <div className="grid h-48 place-items-center text-sm text-muted-foreground">No matching rows</div>
                  )}
                </div>
              </CardContent>
            </Card>

            <div className="space-y-5 xl:sticky xl:top-5 xl:self-start">
              {selected && (
                <Card>
                  <CardHeader className="p-4 pb-3">
                    <CardTitle className="text-base">Verify extracted values</CardTitle>
                    <CardDescription>
                      {doc.isActive
                        ? "This timetable is live. Verified edits are available to the bot immediately."
                        : "Confirm the row as extracted, or edit it before publishing this timetable."}
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="grid gap-3 p-4 pt-0">
                    {[
                      ["Subject code", "subCode"],
                      ["Subject name", "subjectName"],
                      ["Session type", "sessionType"],
                      ["Lecturer", "lecturer"],
                      ["Time", "time"],
                      ["Room", "room"],
                    ].map(([label, key]) => (
                      <label
                        key={key}
                        htmlFor={`${selected.id}-${key}`}
                        className="grid gap-1.5 text-xs font-medium text-muted-foreground"
                      >
                        <span>{label}</span>
                        <Input
                          id={`${selected.id}-${key}`}
                          value={String(selected[key as keyof Entry])}
                          onChange={(event) => setDraft({ ...selected, [key]: event.target.value })}
                        />
                      </label>
                    ))}
                    <div className="mt-2 flex gap-2">
                      <Button
                        className="flex-1"
                        variant={selectedIsVerified ? "secondary" : "default"}
                        disabled={saveMutation.isPending || selectedIsVerified}
                        onClick={() => saveMutation.mutate(selected)}
                      >
                        {saveMutation.isPending ? (
                          <LoaderCircle className="h-4 w-4 animate-spin" />
                        ) : selectedIsVerified ? (
                          <CheckCircle2 className="h-4 w-4" />
                        ) : (
                          <ShieldCheck className="h-4 w-4" />
                        )}
                        {draft ? "Save & verify" : selected.reviewed ? "Verified" : "Verify row"}
                      </Button>
                      {draft && (
                        <Button variant="outline" onClick={() => setDraft(null)}>
                          Reset
                        </Button>
                      )}
                    </div>
                  </CardContent>
                </Card>
              )}
            </div>
          </div>
        </>
      )}
    </main>
  )
}
