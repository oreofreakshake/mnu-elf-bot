export const statusStyle = {
  queued: { label: "Queued", variant: "secondary" as const },
  processing: { label: "Processing", variant: "default" as const },
  completed: { label: "Ready", variant: "success" as const },
  failed: { label: "Failed", variant: "destructive" as const },
}
