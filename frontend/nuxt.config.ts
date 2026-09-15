// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  compatibilityDate: "2026-08-01",
  app: {
    head: {
      script: [
        {
          id: "telegram-web-app",
          src: "https://telegram.org/js/telegram-web-app.js",
          defer: false,
        },
      ],
    },
  },
  css: ["~/assets/css/main.css"],
  devtools: { enabled: true },
  modules: ["@nuxt/eslint"],
  runtimeConfig: {
    djangoApiBaseUrl: "http://127.0.0.1:8000/api/v1",
    public: {
      apiBaseUrl: "http://127.0.0.1:8000/api/v1",
    },
  },
  typescript: {
    strict: true,
    typeCheck: true,
  },
})
