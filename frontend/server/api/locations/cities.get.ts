import { djangoRequest, proxyDjangoError } from "~~/server/utils/django"
export default defineEventHandler(async (event): Promise<unknown> => {
  try { return await djangoRequest<unknown>(event, "/locations/cities/", { query: getQuery(event) }) }
  catch (error) { return proxyDjangoError(event, error) }
})
