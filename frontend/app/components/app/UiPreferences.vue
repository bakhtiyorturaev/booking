<script setup lang="ts">
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome"
import { faCheck, faMoon, faSun } from "@fortawesome/free-solid-svg-icons"
import { supportedLocales, type Locale } from "~/types/translation"

const { locale, setLocale, t } = useTranslations()
const { mode, toggle } = useTheme()

const isLangMenuOpen = ref(false)
const dropdownRef = ref<HTMLElement | null>(null)

interface LanguageOption {
  code: Locale
  name: string
  shortLabel: string
  flag: string
}

const languages: LanguageOption[] = [
  {
    code: "uz",
    name: "O‘zbekcha",
    shortLabel: "UZ",
    flag: "/flags/uz.svg",
  },
  {
    code: "ru",
    name: "Русский",
    shortLabel: "RU",
    flag: "/flags/ru.svg",
  },
  {
    code: "en",
    name: "English",
    shortLabel: "EN",
    flag: "/flags/en.svg",
  },
]

const currentLanguage = computed<LanguageOption>(() => {
  const found = languages.find(l => l.code === locale.value)
  return found ?? languages[0]!
})

const selectLanguage = async (code: Locale) => {
  isLangMenuOpen.value = false
  await setLocale(code)
}

const toggleLangMenu = () => {
  isLangMenuOpen.value = !isLangMenuOpen.value
}

const handleClickOutside = (event: MouseEvent) => {
  if (dropdownRef.value && !dropdownRef.value.contains(event.target as Node)) {
    isLangMenuOpen.value = false
  }
}

onMounted(() => {
  document.addEventListener("click", handleClickOutside)
})

onUnmounted(() => {
  document.removeEventListener("click", handleClickOutside)
})
</script>

<template>
  <div class="ui-preferences">
    <!-- Language Custom Dropdown with Only Flag on Trigger -->
    <div ref="dropdownRef" class="custom-locale-dropdown">
      <button
        type="button"
        class="locale-trigger-btn"
        :class="{ active: isLangMenuOpen }"
        :aria-expanded="isLangMenuOpen"
        :aria-label="t('common.language')"
        :title="currentLanguage.name"
        @click="toggleLangMenu"
      >
        <img :src="currentLanguage.flag" :alt="currentLanguage.name" class="flag-icon-round trigger-flag">
      </button>

      <Transition name="dropdown-fade">
        <div v-if="isLangMenuOpen" class="locale-menu-popover">
          <button
            v-for="lang in languages"
            :key="lang.code"
            type="button"
            class="locale-option-item"
            :class="{ selected: lang.code === locale }"
            @click="selectLanguage(lang.code)"
          >
            <img :src="lang.flag" :alt="lang.name" class="flag-icon-round">
            <span class="lang-option-name">{{ lang.name }}</span>
            <FontAwesomeIcon v-if="lang.code === locale" :icon="faCheck" class="selected-check-icon" />
          </button>
        </div>
      </Transition>
    </div>

    <!-- Dark/Light Theme Toggle Button -->
    <button
      class="theme-toggle"
      type="button"
      :aria-label="mode === 'dark' ? t('theme.light') : t('theme.dark')"
      @click="toggle"
    >
      <FontAwesomeIcon :icon="mode === 'dark' ? faMoon : faSun" />
    </button>
  </div>
</template>

<style scoped>
.ui-preferences {
  display: flex;
  align-items: center;
  gap: 10px;
}

.custom-locale-dropdown {
  position: relative;
}

.locale-trigger-btn {
  display: grid;
  place-items: center;
  width: 36px;
  height: 36px;
  padding: 0;
  border-radius: 50%;
  border: 1px solid var(--border);
  background: var(--control);
  cursor: pointer;
  transition: border-color 160ms ease, background 160ms ease, transform 0.15s ease, box-shadow 0.15s ease;
  user-select: none;
}

.locale-trigger-btn:hover,
.locale-trigger-btn.active {
  border-color: var(--accent);
  background: color-mix(in srgb, var(--accent) 12%, transparent);
  transform: scale(1.05);
}

.flag-icon-round {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  object-fit: cover;
  flex-shrink: 0;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.25);
  border: 1px solid rgba(255, 255, 255, 0.15);
}

.trigger-flag {
  width: 24px;
  height: 24px;
}

.locale-menu-popover {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  min-width: 165px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 6px;
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.35);
  backdrop-filter: blur(12px);
  z-index: 1000;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.locale-option-item {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 8px 12px;
  border-radius: 10px;
  border: none;
  background: transparent;
  color: var(--text);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  text-align: left;
  transition: background 0.15s ease, color 0.15s ease;
}

.locale-option-item:hover {
  background: color-mix(in srgb, var(--accent) 12%, transparent);
  color: var(--accent);
}

.locale-option-item.selected {
  background: color-mix(in srgb, var(--accent) 18%, transparent);
  color: var(--accent);
  font-weight: 750;
}

.lang-option-name {
  flex: 1;
}

.selected-check-icon {
  font-size: 11px;
  color: var(--accent);
}

.theme-toggle {
  display: grid;
  place-items: center;
  width: 36px;
  height: 36px;
  padding: 0;
  border: 1px solid var(--border);
  border-radius: 50%;
  background: var(--control);
  color: var(--accent);
  font-size: 15px;
  cursor: pointer;
  transition: border-color 160ms ease, background 160ms ease, color 160ms ease, transform 0.15s ease;
}

.theme-toggle:hover {
  border-color: var(--accent);
  transform: scale(1.05);
}

/* Animations */
.dropdown-fade-enter-active,
.dropdown-fade-leave-active {
  transition: opacity 0.15s ease, transform 0.15s ease;
}

.dropdown-fade-enter-from,
.dropdown-fade-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}
</style>
