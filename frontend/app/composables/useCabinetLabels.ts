export const useCabinetLabels = () => {
  const { isStaff: staff } = useCabinetAccess()
  const serviceStatusLabel = (value: string) => value === "ACTIVE" ? "Faol" : "Nofaol"
  const statuses: Record<string, string> = {
    ACTIVE: "Faol", INACTIVE: "Nofaol", BLOCKED: "Bloklangan", DELETED: "O‘chirilgan", CONFIRMED: "Tasdiqlangan", CHECKED_IN: "Boshlangan", COMPLETED: "Tugallangan", CANCELLED: "Bekor qilingan", NO_SHOW: "Kelmadi", PENDING_CONFIRMATION: "Kutilmoqda", PAID: "To‘langan", FAILED: "Xatolik", REFUNDED: "Qaytarilgan",
  }
  const roles: Record<string, string> = { CUSTOMER: "Mijoz", CLIENT: "Xizmat egasi", MODERATOR: "Moderator", ADMIN: "Administrator" }
  return { serviceStatusLabel, statusLabel: (value: string) => statuses[value] || value, roleLabel: (value: string) => roles[value] || value }
}
