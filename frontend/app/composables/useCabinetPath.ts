import { authScopeForPath, cabinetBase } from "~~/shared/authScope"
export const useCabinetPath = () => {
  const route = useRoute()
  return (suffix = "") => `${cabinetBase(authScopeForPath(route.path))}${suffix}`
}
