// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  compatibilityDate: "2026-08-01",
  app: {
    head: {
      title: "RezervUZ — Onlayn bron qilish platformasi",
      titleTemplate: "%s — RezervUZ",
      meta: [
        { charset: "utf-8" },
        { name: "viewport", content: "width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no, viewport-fit=cover" },
        { name: "theme-color", content: "#0f172a" },
        { name: "description", content: "Klublar, PlayStation zallari va sartaroshxonalarni qulay onlayn bron qilish platformasi" },
      ],
      link: [
        { rel: "icon", type: "image/svg+xml", href: "/favicon.svg" },
        { rel: "icon", type: "image/png", sizes: "32x32", href: "/favicon-32x32.png" },
        { rel: "icon", type: "image/png", sizes: "16x16", href: "/favicon-16x16.png" },
        { rel: "apple-touch-icon", sizes: "180x180", href: "/apple-touch-icon.png" },
        { rel: "manifest", href: "/site.webmanifest" },
      ],
      script: [
        {
          id: "telegram-web-app",
          src: "https://telegram.org/js/telegram-web-app.js",
          defer: false,
        },
      ],
    },
  },
  css: [
    "@fortawesome/fontawesome-svg-core/styles.css",
    "~/assets/css/main.css",
  ],
  devtools: { enabled: true },
  modules: ["@nuxt/eslint"],
  runtimeConfig: {
    djangoApiBaseUrl: process.env.NUXT_DJANGO_API_BASE_URL || "http://127.0.0.1:8000/api/v1",
    public: {
      apiBaseUrl: process.env.NUXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000/api/v1",
    },
  },
  typescript: {
    strict: true,
    typeCheck: false,
  },
})
