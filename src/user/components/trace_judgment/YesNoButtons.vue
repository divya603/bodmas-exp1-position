<script setup>
// The YES / NO answer for a trial (user's design, 2026-09-16): the D (YES) and
// F (NO) keys. Since 2026-09-18, at the user's request, the keyboard is the ONLY
// way to answer: the two coloured boxes are labels showing which key does what,
// they are not clickable (no click handler, and pointer events are off). Emits
// 'answer' with { response: 'yes' | 'no', method: 'key' }. Keys are ignored
// while `disabled`. `chosen` keeps the given answer highlighted (practice shows
// it next to the feedback). The key listener lives as long as this component is
// mounted.
import { onKeyDown } from '@vueuse/core'

const props = defineProps({
  disabled: { type: Boolean, default: false },
  chosen: { type: String, default: null },
})
const emit = defineEmits(['answer'])

const KEY_TO_RESPONSE = { d: 'yes', f: 'no' }

onKeyDown(
  ['d', 'D', 'f', 'F'],
  (e) => {
    if (props.disabled || e.metaKey || e.ctrlKey || e.altKey) return
    e.preventDefault()
    emit('answer', { response: KEY_TO_RESPONSE[e.key.toLowerCase()], method: 'key' })
  },
  { dedupe: true }
)

function dim(response) {
  return props.disabled && props.chosen !== response ? 'opacity-40' : ''
}
</script>

<template>
  <div class="mb-6">
    <!-- labels, not controls: answering is keyboard-only -->
    <div class="flex justify-center gap-4 select-none pointer-events-none" aria-hidden="true">
      <div
        class="w-28 py-2 rounded-lg text-base font-bold text-white bg-emerald-600 text-center transition"
        :class="[dim('yes'), chosen === 'yes' ? 'ring-2 ring-emerald-300' : '']"
      >
        YES <span class="ml-1 text-xs font-semibold text-white/60">(D)</span>
      </div>
      <div
        class="w-28 py-2 rounded-lg text-base font-bold text-white bg-rose-600 text-center transition"
        :class="[dim('no'), chosen === 'no' ? 'ring-2 ring-rose-300' : '']"
      >
        NO <span class="ml-1 text-xs font-semibold text-white/60">(F)</span>
      </div>
    </div>
    <p class="mt-2 text-center text-sm text-muted-foreground">
      Answer with the keyboard: press
      <kbd class="px-1 mx-0.5 rounded border border-gray-300 bg-white font-mono text-xs">D</kbd>
      for <strong>YES</strong> or
      <kbd class="px-1 mx-0.5 rounded border border-gray-300 bg-white font-mono text-xs">F</kbd>
      for <strong>NO</strong>
    </p>
  </div>
</template>
