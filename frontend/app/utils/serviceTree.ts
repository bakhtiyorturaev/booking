import type { ServiceTypeOption } from "~/api/serviceTypes"

export const descendantServiceIds = (services: ServiceTypeOption[], selected: string[]) => {
  const ids = new Set(selected)
  let changed = true
  while (changed) {
    changed = false
    for (const service of services) {
      if (service.parent && ids.has(service.parent) && !ids.has(service.id)) {
        ids.add(service.id)
        changed = true
      }
    }
  }
  return ids
}

export const serviceTreeOptions = <T extends ServiceTypeOption>(services: T[]) => {
  const result: (T & { depth: number; label: string })[] = []
  const seen = new Set<string>()
  const visit = (service: T, depth: number) => {
    if (seen.has(service.id)) return
    seen.add(service.id)
    result.push({ ...service, depth, label: `${"— ".repeat(depth)}${service.name}` })
    for (const child of services.filter(item => item.parent === service.id)) visit(child, depth + 1)
  }
  for (const root of services.filter(item => !item.parent || !services.some(parent => parent.id === item.parent))) visit(root, 0)
  for (const item of services) if (!seen.has(item.id)) visit(item, 0)
  return result
}

export const rootService = (services: ServiceTypeOption[], service: ServiceTypeOption | null) => {
  const seen = new Set<string>()
  while (service?.parent && !seen.has(service.id)) {
    seen.add(service.id)
    service = services.find(item => item.id === service?.parent) || service
  }
  return service
}
