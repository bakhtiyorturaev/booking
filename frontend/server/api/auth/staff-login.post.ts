import { proxyDjangoError } from "~~/server/utils/django"
import { completePublicAuth } from "~~/server/utils/publicAuth"

// Xodimlar (admin/moderator) uchun parolli login. Django /auth/staff-login/ ga uzatadi
// va qaytgan JWT tokenlarni httpOnly cookie'ga yozadi (Telegram login bilan bir xil oqim).
export default defineEventHandler(async (event) => {
  try {
    return await completePublicAuth(event, "/auth/staff-login/", await readBody(event))
  } catch (error) {
    return proxyDjangoError(event, error)
  }
})
