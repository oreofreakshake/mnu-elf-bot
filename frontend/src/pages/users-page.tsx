import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { LoaderCircle, UserCog } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { getUsers, updateUserRole } from "@/lib/api"
import { formatDate } from "@/lib/utils"
import type { TelegramUserRecord, UserRole } from "@/types"

export function UsersPage({ currentUser }: { currentUser: TelegramUserRecord }) {
  const queryClient = useQueryClient()
  const users = useQuery({ queryKey: ["users"], queryFn: getUsers })
  const roleMutation = useMutation({
    mutationFn: ({ id, role }: { id: string; role: UserRole }) => updateUserRole(id, role),
    onSuccess: (updated) =>
      queryClient.setQueryData<TelegramUserRecord[]>(["users"], (rows) =>
        rows?.map((user) => (user.id === updated.id ? updated : user)),
      ),
  })
  const rows = users.data ?? []
  const reviewers = rows.filter((user) => user.role === "reviewer").length
  const administrators = rows.filter((user) => user.role === "admin").length

  return (
    <main className="mx-auto w-full max-w-6xl px-4 pb-16 pt-10 sm:px-6">
      <div className="mb-8">
        <Badge className="mb-4 gap-1.5">
          <UserCog className="h-3.5 w-3.5" /> Access control
        </Badge>
        <h1 className="text-3xl font-bold tracking-tight">Telegram users</h1>
        <p className="mt-2 text-muted-foreground">Review bot activity and manage dashboard permissions.</p>
      </div>
      <section className="mb-6 grid gap-4 sm:grid-cols-3">
        {[
          ["Bot users", rows.length],
          ["Reviewers", reviewers],
          ["Administrators", administrators],
        ].map(([label, value]) => (
          <Card key={String(label)}>
            <CardContent className="p-5">
              <p className="text-sm text-muted-foreground">{label}</p>
              <p className="mt-1 text-2xl font-bold">{value}</p>
            </CardContent>
          </Card>
        ))}
      </section>
      <Card className="overflow-hidden">
        <CardHeader>
          <CardTitle>User permissions</CardTitle>
          <CardDescription>Telegram login verifies identity; this role determines dashboard access.</CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          {users.isLoading ? (
            <div className="grid h-48 place-items-center">
              <LoaderCircle className="h-6 w-6 animate-spin text-primary" />
            </div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>User</TableHead>
                    <TableHead>Telegram ID</TableHead>
                    <TableHead>Last active</TableHead>
                    <TableHead className="w-44">Role</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {rows.map((user) => {
                    const name =
                      [user.firstName, user.lastName].filter(Boolean).join(" ") || user.username || "Telegram user"
                    return (
                      <TableRow key={user.id}>
                        <TableCell>
                          <div className="font-medium">{name}</div>
                          <div className="text-xs text-muted-foreground">
                            {user.username ? `@${user.username}` : "No username"}
                          </div>
                        </TableCell>
                        <TableCell className="font-mono text-xs">{user.telegramUserId}</TableCell>
                        <TableCell className="text-sm text-muted-foreground">{formatDate(user.lastSeenAt)}</TableCell>
                        <TableCell>
                          <select
                            value={user.role}
                            disabled={user.id === currentUser.id || roleMutation.isPending}
                            onChange={(event) =>
                              roleMutation.mutate({ id: user.id, role: event.target.value as UserRole })
                            }
                            className="h-9 w-full rounded-md border bg-background px-3 text-sm text-black outline-none focus:ring-2 focus:ring-ring"
                          >
                            <option value="user">User</option>
                            <option value="reviewer">Reviewer</option>
                            <option value="admin">Admin</option>
                          </select>
                        </TableCell>
                      </TableRow>
                    )
                  })}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>
    </main>
  )
}
