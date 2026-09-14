<!-- Footer after the corporate master: the copyright note bottom left, the slide
     number bottom right, both small and in the title colour. Slidev picks
     `global-bottom.vue` up automatically.

     Skipped on the cover and on the closing slide, because the master's
     `Titelfolie` and `Schlussfolie` carry neither -- the closing slide states the
     company in full instead. -->
<template>
  <footer
    v-if="$slidev.nav.currentPage > 1 && $slidev.nav.currentPage < $slidev.nav.total"
    class="ct-footer"
  >
    <span>&copy; con terra GmbH</span>
    <span>{{ $slidev.nav.currentPage }} | {{ $slidev.nav.total }}</span>
  </footer>
</template>
