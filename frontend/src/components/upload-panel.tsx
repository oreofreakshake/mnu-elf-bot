import { useMutation } from "@tanstack/react-query"
import { AlertCircle, LoaderCircle, UploadCloud } from "lucide-react"
import { useRef, useState } from "react"
import { Card, CardContent } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { uploadDocument } from "@/lib/api"
import { cn } from "@/lib/utils"
import type { DocumentRecord } from "@/types"

export function UploadPanel({ onUploaded }: { onUploaded: (document: DocumentRecord) => void }) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [dragging, setDragging] = useState(false)
  const [progress, setProgress] = useState(0)
  const mutation = useMutation({ mutationFn: (file: File) => uploadDocument(file, setProgress), onSuccess: onUploaded })

  function submit(file?: File) {
    if (!file || mutation.isPending) return
    setProgress(0)
    mutation.mutate(file)
  }

  return (
    <Card className="overflow-hidden border-primary/15">
      <CardContent className="p-4">
        <input
          ref={inputRef}
          type="file"
          accept="application/pdf,.pdf"
          className="hidden"
          onChange={(event) => submit(event.target.files?.[0])}
        />
        <button
          type="button"
          disabled={mutation.isPending}
          className={cn(
            "relative flex min-h-28 w-full cursor-pointer items-center gap-4 rounded-lg border border-dashed p-4 transition-colors disabled:cursor-wait sm:px-5",
            dragging
              ? "border-primary bg-primary/5"
              : "border-primary/30 bg-blue-50/40 hover:border-primary/60 hover:bg-blue-50/70",
          )}
          onClick={() => inputRef.current?.click()}
          onDragEnter={(event) => {
            event.preventDefault()
            setDragging(true)
          }}
          onDragOver={(event) => event.preventDefault()}
          onDragLeave={() => setDragging(false)}
          onDrop={(event) => {
            event.preventDefault()
            setDragging(false)
            submit(event.dataTransfer.files[0])
          }}
        >
          <div className="grid h-11 w-11 shrink-0 place-items-center rounded-lg bg-primary text-primary-foreground">
            {mutation.isPending ? (
              <LoaderCircle className="h-5 w-5 animate-spin" />
            ) : (
              <UploadCloud className="h-5 w-5" />
            )}
          </div>
          <div className="min-w-0 flex-1 text-left">
            <h2 className="font-semibold">Upload timetable PDF</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              Drop a PDF here or choose a file. Extraction starts automatically.
            </p>
            {mutation.isPending && <Progress value={progress} className="mt-3 max-w-md" />}
            {mutation.isError && (
              <div className="mt-2 flex items-center gap-2 text-sm text-red-600">
                <AlertCircle className="h-4 w-4" />
                {mutation.error instanceof Error ? mutation.error.message : "Upload failed"}
              </div>
            )}
          </div>
          <span className="inline-flex h-10 shrink-0 items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground">
            {mutation.isPending ? `Uploading ${progress}%` : "Choose PDF"}
          </span>
        </button>
      </CardContent>
    </Card>
  )
}
