export type AuthScope = "customer" | "staff" | "client"
export const authScopeForPath = (path: string): AuthScope => {
  if (path.startsWith("/site/staff/") || path === "/cabinet" || path.startsWith("/cabinet/")) return "staff"
  if (path.startsWith("/site/client/")) return "client"
  return "customer"
}
export const cabinetBase = (scope: AuthScope) => scope === "client" ? "/site/client/panel" : "/site/staff/panel"
