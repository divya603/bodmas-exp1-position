<script setup>
// The YES / NO answer for a trial (user's design, 2026-09-16): two buttons plus
// the D (YES) and F (NO) keys. Emits 'answer' with { response: 'yes' | 'no',
// method: 'key' | 'click' }. Keys and clicks are ignored while `disabled`.
// `chosen` keeps the given answer highlighted (practice shows it next to the
// feedback). The key listener lives as long as this component is mounted.
import { onKeyDown } from '@vueuse/core'

const props = defineProps({
  disabled: { type: Boolean, default: false },
  chosen: { type: String, default: null },
})
const emit = defineEmits(['answer'])

const KEY_TO_RESPONSE = { d: 'yes', f: 'no' }

function answer(response, method) {
  if (props.disabled) return
  emit('answer', { response, method })
}

onKeyDown(
  ['d', 'D', 'f', 'F'],
  (e) => {
    if (props.disabled || e.metaKey || e.ctrlKey || e.altKey) return
    e.preventDefault()
    answer(KEY_TO_RESPONSE[e.key.toLowerCase()], 'key')
  },
  { dedupe: true }
)

function dim(response) {
  return props.disabled && props.chosen !== response ? 'opacity-40' : ''
}
</script>

<template>
  <div class="mb-6">
    <div class="flex justify-center gap-4">
      <button
        type="button"
        :disabled="disabled"
        @click="answer('yes', 'click')"
        class="w-28 py-2 rounded-lg text-base font-bold text-white bg-emerald-600 transition"
        :class="[
          dim('yes'),
          chosen === 'yes' ? 'ring-2 ring-emerald-300' : '',
          disabled ? 'cursor-not-allowed' : 'hover:bg-emerald-700',
        ]"
      >
        YES <span class="ml-1 text-xs font-semibold text-white/60">(D)</span>
      </button>
      <button
        type="button"
        :disabled="disabled"
        @click="answer('no', 'click')"
        class="w-28 py-2 rounded-lg text-base font-bold text-white bg-rose-600 transition"
        :class="[
          dim('no'),
          chosen === 'no' ? 'ring-2 ring-rose-300' : '',
          disabled ? 'cursor-not-allowed' : 'hover:bg-rose-700',
        ]"
      >
        NO <span class="ml-1 text-xs font-semibold text-white/60">(F)</span>
      </button>
    </div>
    <p class="mt-2 text-center text-sm text-muted-foreground">
      Press
      <kbd class="px-1 mx-0.5 rounded border border-gray-300 bg-white font-mono text-xs">D</kbd>
      for <strong>YES</strong> or
      <kbd class="px-1 mx-0.5 rounded border border-gray-300 bg-white font-mono text-xs">F</kbd>
      for <strong>NO</strong>
    </p>
  </div>
</template>
