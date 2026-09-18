<script setup>
import { ref, watch, computed, nextTick, onBeforeUnmount } from 'vue'
import useViewAPI from '@/core/composables/useViewAPI'
import { Button } from '@/uikit/components/ui/button'
import { ConstrainedTaskWindow } from '@/uikit/layouts'
import practiceItems from '@/user/data/practice_items.json'
import { layoutTrace } from '@/user/utils/traceLayout'
import YesNoButtons from '@/user/components/trace_judgment/YesNoButtons.vue'

const api = useViewAPI()

// the work, laid out so each computed value sits under the operator that
// produced it (flush left if a step is not a single operation, or on the
// transition step where there is no trace)
const lines = computed(() => {
  const trace = api.stepData?.trace || []
  return layoutTrace(trace)?.lines ?? trace.map((text) => ({ text, indent: 0 }))
})

// 3 practice trials (built by base-task/practice.py), then a transition screen
// ("Begin task") before the real task
const trials = api.steps.append(practiceItems.map((item) => ({ ...item })))
trials.append([{ id: 'transition' }])

// the YES / NO answer given on this trial ('yes' | 'no' | null)
const chosen = ref(null)
// after an answer we stay on the trial and show the explanation: the
// erroneous step(s) highlighted in the trace plus the feedback statement.
// The feedback never says whether the participant's own answer was right or
// wrong; it only explains what the right answer would be.
const feedbackShown = ref(false)
const feedbackBox = ref(null)

// ── read-before-answer lock (same as the main task) ─────────────────
const UNLOCK_DELAY_MS = 3000
const locked = ref(false)
const remaining = ref(0)
let lockTimer = null
let lockInterval = null

function clearLockTimers() {
  if (lockTimer) {
    clearTimeout(lockTimer)
    lockTimer = null
  }
  if (lockInterval) {
    clearInterval(lockInterval)
    lockInterval = null
  }
}

function startLock() {
  clearLockTimers()
  locked.value = true
  remaining.value = Math.ceil(UNLOCK_DELAY_MS / 1000)
  lockInterval = setInterval(() => {
    remaining.value = Math.max(0, remaining.value - 1)
    if (remaining.value <= 0) {
      clearInterval(lockInterval)
      lockInterval = null
    }
  }, 1000)
  lockTimer = setTimeout(() => {
    locked.value = false
    remaining.value = 0
  }, UNLOCK_DELAY_MS)
}

// re-arm the lock on every new trial (not on the transition screen)
watch(
  () => api.stepIndex,
  () => {
    if (api.path[0] !== 'transition') {
      chosen.value = null
      feedbackShown.value = false
      startLock()
    } else {
      clearLockTimers()
    }
  },
  { immediate: true }
)

onBeforeUnmount(clearLockTimers)

if (!api.isTimerStarted()) {
  api.startTimer()
}

// the trace is rendered from index 1 (index 0 is the expression itself), so
// displayed line i corresponds to full-trace index i + 1
function isErrorStep(displayIndex) {
  return feedbackShown.value && api.stepData.error_steps.some((e) => e.trace_index === displayIndex + 1)
}

function errorNote(displayIndex) {
  const e = api.stepData.error_steps.find((e) => e.trace_index === displayIndex + 1)
  return e ? e.note : ''
}

// A YES / NO answer (the D or F key; keyboard only since 2026-09-18) is
// recorded, then the feedback shows.
function onAnswer({ response, method }) {
  if (locked.value || feedbackShown.value) return
  chosen.value = response
  api.stepData.response = response
  api.stepData.response_method = method
  api.stepData.responded_agree = response === 'yes'
  api.stepData.correct_agree = api.stepData.statement_correct === true
  api.stepData.is_correct = api.stepData.responded_agree === api.stepData.correct_agree
  api.stepData.rt = api.elapsedTime()
  api.recordStep()
  feedbackShown.value = true
  nextTick(() => feedbackBox.value?.scrollIntoView({ behavior: 'smooth', block: 'nearest' }))
}

function next() {
  api.startTimer()
  api.goNextStep()
}

function beginTask() {
  api.saveData(true)
  api.goNextView()
}

function autofill() {
  while (api.stepIndex < api.nSteps) {
    if (api.path[0] !== 'transition') {
      api.stepData.response = api.faker.rchoice(['yes', 'no'])
      api.stepData.response_method = 'autofill'
      api.stepData.rt = api.faker.rnorm(4000, 800)
    }
    api.recordStep()
    if (api.goNextStep() === null) break
  }
}
api.setAutofill(autofill)
</script>

<template>
  <ConstrainedTaskWindow
    variant="ghost"
    :responsiveUI="api.config.responsiveUI"
    :width="api.config.windowsizerRequest.width"
    :height="api.config.windowsizerRequest.height"
  >
    <div v-if="api.path[0] !== 'transition'" class="text-left w-full h-full overflow-y-auto px-2">
      <div class="flex items-center justify-between mb-1">
        <span class="text-xs font-semibold uppercase tracking-wide text-blue-600">Practice</span>
        <span class="text-xs text-muted-foreground">{{ api.stepIndex + 1 }} of {{ practiceItems.length }}</span>
      </div>
      <p class="text-muted-foreground mb-1">Expression given to {{ api.stepData.student_name }}:</p>
      <p class="text-2xl font-bold mb-5 font-mono">{{ api.stepData.expression }}</p>

      <p class="text-muted-foreground mb-2">
        Here is the final answer {{ api.stepData.student_name }} produced, along with their work:
      </p>
      <!-- Each computed value sits under the operator that produced it; only the
           line as a whole moves (see utils/traceLayout.js). Line 0 is the
           expression itself, with no "=". An error step is highlighted amber
           with its note beside it. -->
      <div class="font-mono text-base mb-5 space-y-1">
        <div v-for="(line, i) in lines" :key="i" class="flex items-start">
          <span class="text-muted-foreground w-5 shrink-0">{{ i === 0 ? '' : '=' }}</span>
          <span
            class="rounded px-1 -mx-1 transition-colors"
            :class="i > 0 && isErrorStep(i - 1) ? 'bg-amber-200' : ''"
            :style="{ marginLeft: line.indent + 'ch' }"
          >
            {{ line.text }}
          </span>
          <span
            v-if="i > 0 && isErrorStep(i - 1)"
            class="ml-3 text-sm italic text-amber-800 font-sans whitespace-nowrap"
          >
            &larr; {{ errorNote(i - 1) }}
          </span>
        </div>
      </div>

      <div class="border border-yellow-300 bg-yellow-50 rounded-lg p-4 mb-5">
        <p class="italic text-yellow-800">{{ api.stepData.belief_statement }}</p>
      </div>

      <p class="font-semibold mb-4">
        Is this what the student believes?
        <span v-if="locked" class="ml-1 text-sm font-normal text-muted-foreground">
          (please read the work above: {{ remaining }}s)
        </span>
      </p>
      <YesNoButtons :disabled="locked || feedbackShown" :chosen="chosen" @answer="onAnswer" />

      <div v-if="feedbackShown" ref="feedbackBox" class="border border-blue-300 bg-blue-50 rounded-lg p-4 mb-6">
        <p class="text-blue-900">{{ api.stepData.feedback }}</p>
      </div>

      <div v-if="feedbackShown" class="flex justify-end mb-4">
        <Button @click="next()">
          {{ api.stepIndex === practiceItems.length - 1 ? 'Continue' : 'Next practice question' }}
          <i-fa6-solid-arrow-right />
        </Button>
      </div>
    </div>

    <div class="text-center" v-else>
      <p class="text-xl font-semibold mb-3">Practice complete!</p>
      <p class="text-lg text-muted-foreground mb-2">Now you'll move on to the real task.</p>
      <p class="text-lg text-muted-foreground mb-6">
        You will judge <strong>24 problems</strong>, one at a time, just like the ones you practiced.
        These count toward your bonus.
      </p>
      <Button variant="default" size="lg" @click="beginTask()">
        Begin task
        <i-fa6-solid-arrow-right />
      </Button>
    </div>
  </ConstrainedTaskWindow>
</template>
