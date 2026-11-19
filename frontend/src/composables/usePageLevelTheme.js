/*
 File: Pulsar/frontend/src/composables/usePageLevelTheme.js
 Description: Visual theme resolver by page navigation level
 Author: MHKolahi@gmail.com
 In collaboration with GPT4 Chat Assistant: Bahram
*/

import {
  computed,
  unref
} from 'vue'

const LEVEL_PALETTE = [
  {
    accent: '#3b82f6',
    accentStrong: '#2563eb'
  },
  {
    accent: '#10b981',
    accentStrong: '#059669'
  },
  {
    accent: '#8b5cf6',
    accentStrong: '#7c3aed'
  },
  {
    accent: '#f59e0b',
    accentStrong: '#d97706'
  },
  {
    accent: '#06b6d4',
    accentStrong: '#0891b2'
  },
  {
    accent: '#f43f5e',
    accentStrong: '#e11d48'
  }
]

function normalizeLevel(level) {
  const value = Number(
    unref(level)
  )

  if (
    !Number.isFinite(value)
  ) {
    return 0
  }

  return Math.max(
    0,
    Math.floor(value)
  )
}

function getPalette(level) {
  const index =
    level %
    LEVEL_PALETTE.length

  return LEVEL_PALETTE[index]
}

export function usePageLevelTheme(
  levelRef
) {
  const level = computed(() => {
    return normalizeLevel(
      levelRef
    )
  })

  const palette = computed(() => {
    return getPalette(
      level.value
    )
  })

  const themeStyle = computed(() => {
    const {
      accent,
      accentStrong
    } = palette.value

    return {
      '--pulsar-level':
        String(level.value),
      '--pulsar-level-accent':
        accent,
      '--pulsar-level-accent-strong':
        accentStrong,
      '--pulsar-level-accent-soft':
        `color-mix(in srgb, ${accent} 10%, transparent)`,
      '--pulsar-level-accent-faint':
        `color-mix(in srgb, ${accent} 5%, transparent)`,
      '--pulsar-level-border':
        `color-mix(in srgb, ${accent} 28%, var(--color-border, #e5e7eb))`,
      '--pulsar-level-surface':
        `color-mix(in srgb, ${accent} 4%, var(--color-panel, #ffffff))`,
      '--pulsar-level-hover':
        `color-mix(in srgb, ${accent} 8%, var(--color-panel, #ffffff))`,
      '--pulsar-level-focus':
        `color-mix(in srgb, ${accent} 22%, transparent)`,
      '--pulsar-level-shadow':
        `color-mix(in srgb, ${accent} 16%, transparent)`
    }
  })

  const surfaceStyle = computed(() => ({
    borderColor:
      'var(--pulsar-level-border)',
    backgroundColor:
      'var(--pulsar-level-surface)',
    boxShadow:
      '0 1px 3px var(--pulsar-level-shadow)'
  }))

  return {
    level,
    themeStyle,
    surfaceStyle
  }
}
