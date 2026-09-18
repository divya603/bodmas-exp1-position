<script setup>
import useViewAPI from '@/core/composables/useViewAPI'
import { Button } from '@/uikit/components/ui/button'
import { ConstrainedTaskWindow } from '@/uikit/layouts'

const api = useViewAPI()

function finish() {
  api.goFirstStep()
  api.goNextView()
}
</script>

<!--
  Text approved by the user 2026-09-13; bonus reduced to one line at the user's
  request 2026-09-14. On 2026-09-16 the user had it match Experiment 2's text
  (except that nothing is skipped here): the "correct order of operations"
  paragraph removed, "Your Job" and the practice paragraph reworded, the
  6-point scale replaced by YES / NO. The numbers here mirror the task code:
  $2 = MAX_BONUS and 3 seconds = UNLOCK_DELAY_MS in TraceJudgmentView.vue,
  24 problems = the form size in utils/sampleForm.js, 3 practice questions =
  data/practice_items.json. Change them together.
-->
<template>
  <ConstrainedTaskWindow
    variant="ghost"
    :responsiveUI="api.config.responsiveUI"
    :width="api.config.windowsizerRequest.width"
    :height="api.config.windowsizerRequest.height"
  >
    <div class="w-[80%] h-[80%] overflow-y-auto">
      <h1 class="text-2xl font-bold mb-4">
        <i-material-symbols-integration-instructions class="inline-block mr-2 text-3xl" /> Instructions
      </h1>

      <p class="text-left text-lg mb-4">
        In this study you will see a math problem, the step-by-step work a student wrote while solving it, and a
        statement about what that student believes about the order of operations.
      </p>

      <p class="text-left text-lg mb-4">
        <strong>Every student in this study makes exactly one mistake</strong>, at one step of their work.
      </p>

      <p class="text-left text-lg mb-4">
        <strong>Your Job.</strong> Decide whether the statement describes what the student believes, using their work
        as evidence. Answer <strong>YES</strong> when the student's mistake is the one the statement describes and
        <strong>NO</strong> otherwise. You answer with the keyboard: press <strong>D</strong> for YES or
        <strong>F</strong> for NO. The coloured YES and NO boxes on the screen show you which key is which; they are
        not buttons and cannot be clicked.
      </p>

      <p class="text-left text-lg mb-4"><strong>Bonus.</strong> You can earn a bonus of up to $2.</p>

      <p class="text-left text-lg mb-4">
        You'll start with <strong>3 practice questions</strong>. After each one, we highlight and explain the right
        answer. Practice trials do not count towards your bonus. Then you'll judge <strong>24 problems</strong>. On
        each one, the answer keys unlock after 3 seconds, so take time to read the work.
      </p>

      <hr class="border-gray-300 my-4" />

      <div class="flex justify-end">
        <Button variant="default" @click="finish()">
          Next
          <i-fa6-solid-arrow-right />
        </Button>
      </div>
    </div>
  </ConstrainedTaskWindow>
</template>
