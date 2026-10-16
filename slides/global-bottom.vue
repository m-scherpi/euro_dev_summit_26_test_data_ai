<!-- Footer after the corporate master: the copyright note bottom left, the slide
     number bottom right, both small and in the title colour. Slidev picks
     `global-bottom.vue` up automatically.

     Skipped on the cover and on the closing slide, because the master's
     `Titelfolie` and `Schlussfolie` carry neither -- the closing slide states the
     company in full instead.

     This used to read `currentPage > 1 && currentPage < total`, which is the same
     thing only while the closing slide is the last one. Adding the FAQ slides
     behind it put a footer on the closing slide and took it off the last FAQ
     slide -- a green build, and nothing to see until the PNGs were exported. The
     condition now names the two slides instead of their positions.

     The count on the right is the count of *talk* slides: the FAQ slides sit
     behind the closing slide and are not part of the 15-minute slot, so counting
     them would tell the audience the talk is five slides longer than it is.

     The same goes for the bonus slide between the closing slide and the FAQ, so
     the total is anchored on the closing slide (found by its class, like
     `isClose`) rather than on the FAQ marker: anchoring it on the FAQ would have
     counted the bonus slide into the talk. Everything behind the close that is
     not FAQ is labelled `Bonus`. -->
<template>
  <footer v-if="showFooter" class="ct-footer">
    <span>&copy; con terra GmbH</span>
    <span v-if="isFaq">FAQ</span>
    <span v-else-if="isBonus">Bonus</span>
    <span v-else>{{ page }} | {{ talkTotal }}</span>
  </footer>
</template>

<script setup lang="ts">
import { useNav } from '@slidev/client'
import { computed } from 'vue'

const { slides, currentSlideNo, currentFrontmatter } = useNav()

// The first slide marked `faq: true`; the same marker `setup/shortcuts.ts` uses
// to find the jump target. Never a hard-coded number.
const faqStart = computed(() => {
  const found = slides.value.find(s => s.meta?.slide?.frontmatter?.faq === true)
  return found ? found.no : slides.value.length + 1
})

const page = computed(() => currentSlideNo.value)
// The closing slide, found by its class -- never by position.
const closeNo = computed(() => {
  const found = slides.value.find(s => String(s.meta?.slide?.frontmatter?.class ?? '').includes('close-slide'))
  return found ? found.no : faqStart.value - 1
})

const isFaq = computed(() => page.value >= faqStart.value)
const isBonus = computed(() => page.value > closeNo.value && !isFaq.value)
const talkTotal = computed(() => closeNo.value)
const isClose = computed(() => String(currentFrontmatter.value?.class ?? '').includes('close-slide'))
const showFooter = computed(() => page.value > 1 && !isClose.value)
</script>
