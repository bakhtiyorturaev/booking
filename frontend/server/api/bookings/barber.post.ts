import type { Booking } from "~~/app/types/booking"
import { djangoRequest, proxyDjangoError, requestLanguage } from "~~/server/utils/django"

export default defineEventHandler(async (event) => {
  const body = await readBody(event)
  try {
    return await djangoRequest<Booking>(
      event,
      "/bookings/barber/",
      {
        method: "POST",
        body,
        headers: {
          "Accept-Language": requestLanguage(event),
          Authorization: getRequestHeader(event, "authorization") || "",
        },
      },
    )
  } catch (error) {
    return proxyDjangoError(event, error)
  }
})
