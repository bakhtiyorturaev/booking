<script setup lang="ts">
import { useAuth } from "~/composables/useAuth"
import { useTheme } from "~/composables/useTheme"

const { user, logout } = useAuth()
const { mode: theme, toggle: toggleTheme } = useTheme()
const route = useRoute()

const isSidebarOpen = ref(false)

const navLinks = [
  {
    to: "/admin",
    label: "Boshqaruv paneli",
    icon: "dashboard",
    exact: true,
  },
  {
    to: "/admin/clubs",
    label: "Muassasalar (Klub & Salon)",
    icon: "clubs",
  },
  {
    to: "/admin/branches",
    label: "Filiallar & Zonalar",
    icon: "branches",
  },
  {
    to: "/admin/barbers",
    label: "Sartaroshlar",
    icon: "barbers",
  },
  {
    to: "/admin/bookings",
    label: "Bronlar",
    icon: "bookings",
  },
  {
    to: "/admin/payments",
    label: "To'lovlar",
    icon: "payments",
  },
  {
    to: "/admin/reviews",
    label: "Sharhlar",
    icon: "reviews",
  },
  {
    to: "/admin/users",
    label: "Foydalanuvchilar",
    icon: "users",
  },
]

const isActive = (item: { to: string, exact?: boolean }) => {
  if (item.exact) {
    return route.path === item.to
  }
  return route.path.startsWith(item.to)
}

const handleLogout = async () => {
  await logout()
  await navigateTo("/login")
}
</script>

<template>
  <div class="admin-layout">
    <!-- Sidebar Overlay for mobile -->
    <div
      v-if="isSidebarOpen"
      class="admin-sidebar-overlay"
      @click="isSidebarOpen = false"
    />

    <!-- Sidebar -->
    <aside class="admin-sidebar" :class="{ 'is-open': isSidebarOpen }">
      <div class="sidebar-header">
        <NuxtLink to="/admin" class="sidebar-brand">
          <div class="brand-logo-badge">⚡</div>
          <div class="brand-text">
            <span class="brand-title">Rezerv<span style="color: #6366f1;">UZ</span></span>
            <span class="brand-subtitle">Xodimlar Kabineti</span>
          </div>
        </NuxtLink>
        <button
          type="button"
          class="sidebar-close-btn"
          aria-label="Menyuni yopish"
          @click="isSidebarOpen = false"
        >
          ✕
        </button>
      </div>

      <nav class="sidebar-nav">
        <NuxtLink
          v-for="item in navLinks"
          :key="item.to"
          :to="item.to"
          class="sidebar-link"
          :class="{ 'is-active': isActive(item) }"
          @click="isSidebarOpen = false"
        >
          <span class="link-icon">
            <svg v-if="item.icon === 'dashboard'" viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/></svg>
            <svg v-else-if="item.icon === 'clubs'" viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>
            <svg v-else-if="item.icon === 'branches'" viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polygon points="16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76"/></svg>
            <svg v-else-if="item.icon === 'barbers'" viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2"><circle cx="6" cy="6" r="3"/><circle cx="6" cy="18" r="3"/><line x1="20" y1="4" x2="8.12" y2="15.88"/><line x1="14.47" y1="14.48" x2="20" y2="20"/><line x1="8.12" y1="8.12" x2="12" y2="12"/></svg>
            <svg v-else-if="item.icon === 'bookings'" viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/><path d="m9 16 2 2 4-4"/></svg>
            <svg v-else-if="item.icon === 'payments'" viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2"><rect x="1" y="4" width="22" height="16" rx="2" ry="2"/><line x1="1" y1="10" x2="23" y2="10"/></svg>
            <svg v-else-if="item.icon === 'reviews'" viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>
            <svg v-else-if="item.icon === 'users'" viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
          </span>
          <span class="link-label">{{ item.label }}</span>
        </NuxtLink>
      </nav>

      <div class="sidebar-footer">
        <NuxtLink to="/" class="back-to-site-link">
          <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>
          <span>Saytga qaytish</span>
        </NuxtLink>
      </div>
    </aside>

    <!-- Main Wrapper -->
    <div class="admin-wrapper">
      <!-- Top Header -->
      <header class="admin-topbar">
        <div class="topbar-left">
          <button
            type="button"
            class="topbar-menu-btn"
            aria-label="Menyuni ochish"
            @click="isSidebarOpen = true"
          >
            <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2"><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="18" x2="21" y2="18"/></svg>
          </button>
          <div class="topbar-badge">
            <span class="live-dot" />
            <span>Xodimlar Portali</span>
          </div>
        </div>

        <div class="topbar-right">
          <!-- Theme Toggle -->
          <button
            type="button"
            class="theme-toggle-btn"
            :title="theme === 'dark' ? 'Yorug\' rejim' : 'Qorong\'i rejim'"
            @click="toggleTheme"
          >
            <span v-if="theme === 'dark'">☀️</span>
            <span v-else>🌙</span>
          </button>

          <!-- User Badge -->
          <div class="staff-user-card">
            <div class="staff-avatar">
              {{ (user?.full_name || user?.username || "A").slice(0, 1).toUpperCase() }}
            </div>
            <div class="staff-meta">
              <span class="staff-name">{{ user?.full_name || user?.username }}</span>
              <span class="staff-role" :class="user?.role?.toLowerCase()">{{ user?.role }}</span>
            </div>
          </div>

          <!-- Logout Button -->
          <button
            type="button"
            class="logout-icon-btn"
            title="Chiqish"
            @click="handleLogout"
          >
            <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>
          </button>
        </div>
      </header>

      <!-- Main Slot Area -->
      <main class="admin-main">
        <slot />
      </main>
    </div>
  </div>
</template>

<style scoped>
.admin-layout {
  display: flex;
  min-height: 100vh;
  background: var(--page);
  color: var(--text);
  font-family: inherit;
}

.admin-sidebar {
  width: 260px;
  min-height: 100vh;
  background: var(--surface);
  border-right: 1px solid var(--panel-border);
  display: flex;
  flex-direction: column;
  position: sticky;
  top: 0;
  z-index: 100;
  transition: transform 0.25s ease;
}

.sidebar-header {
  padding: 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid var(--panel-border);
}

.sidebar-brand {
  display: flex;
  align-items: center;
  gap: 12px;
  text-decoration: none;
  color: inherit;
}

.brand-logo-badge {
  width: 38px;
  height: 38px;
  border-radius: 10px;
  background: linear-gradient(135deg, var(--accent) 0%, #0088cc 100%);
  display: grid;
  place-items: center;
  font-size: 20px;
  color: #fff;
  box-shadow: 0 4px 12px rgba(32, 199, 244, 0.3);
}

.brand-text {
  display: flex;
  flex-direction: column;
}

.brand-title {
  font-size: 16px;
  font-weight: 750;
  letter-spacing: -0.02em;
}

.brand-subtitle {
  font-size: 11px;
  color: var(--muted);
  font-weight: 500;
}

.sidebar-close-btn {
  display: none;
  background: none;
  border: none;
  color: var(--muted);
  font-size: 18px;
  cursor: pointer;
}

.sidebar-nav {
  flex: 1;
  padding: 16px 12px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.sidebar-link {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 14px;
  border-radius: 10px;
  color: var(--muted);
  text-decoration: none;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.15s ease;
}

.sidebar-link:hover {
  color: var(--text);
  background: color-mix(in srgb, var(--accent) 8%, transparent);
}

.sidebar-link.is-active {
  color: var(--accent);
  background: color-mix(in srgb, var(--accent) 14%, transparent);
  font-weight: 650;
}

.link-icon {
  display: flex;
  align-items: center;
  justify-content: center;
}

.sidebar-footer {
  padding: 16px;
  border-top: 1px solid var(--panel-border);
}

.back-to-site-link {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  border-radius: 8px;
  font-size: 13px;
  color: var(--muted);
  text-decoration: none;
  border: 1px solid var(--border);
  transition: all 0.15s ease;
}

.back-to-site-link:hover {
  color: var(--text);
  border-color: var(--accent);
}

.admin-wrapper {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.admin-topbar {
  height: 68px;
  padding: 0 24px;
  background: var(--surface);
  border-bottom: 1px solid var(--panel-border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  position: sticky;
  top: 0;
  z-index: 90;
}

.topbar-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.topbar-menu-btn {
  display: none;
  background: none;
  border: none;
  color: var(--text);
  cursor: pointer;
  padding: 4px;
}

.topbar-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 4px 10px;
  border-radius: 20px;
  background: color-mix(in srgb, var(--accent) 12%, transparent);
  color: var(--accent);
  font-size: 12px;
  font-weight: 600;
}

.live-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--accent);
  box-shadow: 0 0 8px var(--accent);
}

.topbar-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.lang-switcher {
  display: flex;
  gap: 2px;
  background: var(--control);
  padding: 3px;
  border-radius: 8px;
  border: 1px solid var(--border);
}

.lang-pill {
  padding: 4px 8px;
  border-radius: 6px;
  border: none;
  background: transparent;
  color: var(--muted);
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s ease;
}

.lang-pill.is-active {
  background: var(--accent);
  color: #fff;
}

.theme-toggle-btn {
  width: 36px;
  height: 36px;
  display: grid;
  place-items: center;
  border-radius: 8px;
  border: 1px solid var(--border);
  background: var(--control);
  cursor: pointer;
}

.staff-user-card {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 4px 10px 4px 4px;
  background: var(--control);
  border: 1px solid var(--border);
  border-radius: 24px;
}

.staff-avatar {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--accent) 0%, #0088cc 100%);
  color: #fff;
  display: grid;
  place-items: center;
  font-size: 12px;
  font-weight: 700;
}

.staff-meta {
  display: flex;
  flex-direction: column;
}

.staff-name {
  font-size: 12px;
  font-weight: 600;
}

.staff-role {
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
}

.staff-role.admin {
  color: #ef4444;
}

.staff-role.moderator {
  color: #3b82f6;
}

.logout-icon-btn {
  width: 36px;
  height: 36px;
  display: grid;
  place-items: center;
  border-radius: 8px;
  border: 1px solid var(--border);
  background: var(--control);
  color: var(--muted);
  cursor: pointer;
  transition: all 0.15s ease;
}

.logout-icon-btn:hover {
  color: #ef4444;
  border-color: #ef4444;
}

.admin-main {
  flex: 1;
  padding: 24px;
  min-width: 0;
}

@media (max-width: 900px) {
  .admin-sidebar {
    position: fixed;
    top: 0;
    bottom: 0;
    left: 0;
    transform: translateX(-100%);
    box-shadow: 12px 0 32px rgba(0, 0, 0, 0.3);
  }

  .admin-sidebar.is-open {
    transform: translateX(0);
  }

  .sidebar-close-btn {
    display: block;
  }

  .topbar-menu-btn {
    display: block;
  }

  .admin-sidebar-overlay {
    position: fixed;
    inset: 0;
    z-index: 95;
    background: rgba(0, 0, 0, 0.6);
    backdrop-filter: blur(4px);
  }

  .staff-meta {
    display: none;
  }

  .admin-main {
    padding: 16px;
  }
}

@media (max-width: 560px) {
  .admin-topbar {
    padding: 0 12px;
    min-height: 56px;
  }

  .topbar-badge span:last-child {
    display: none;
  }

  .staff-user-card {
    padding: 3px;
  }
}
</style>
