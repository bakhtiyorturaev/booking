export const useCabinetLabels = () => {
  const statuses: Record<string, string> = {
    ACTIVE: "Faol", BLOCKED: "Bloklangan", DELETED: "O‘chirilgan", PENDING: "Kutilmoqda", INACTIVE: "Faol emas", CONFIRMED: "Tasdiqlangan", CHECKED_IN: "Boshlangan", COMPLETED: "Tugallangan", CANCELLED: "Bekor qilingan", NO_SHOW: "Kelmadi", PENDING_CONFIRMATION: "Kutilmoqda", PAID: "To‘langan", FAILED: "Xatolik", REFUNDED: "Qaytarilgan",
  }
  const roles: Record<string, string> = { CUSTOMER: "Mijoz", CLIENT: "Muassasa egasi", MODERATOR: "Moderator", ADMIN: "Administrator" }
  return { statusLabel: (value: string) => statuses[value] || value, roleLabel: (value: string) => roles[value] || value }
}
