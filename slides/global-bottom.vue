<!-- Footer on every slide but the cover, after the corporate master: the
     copyright note bottom left, the slide number bottom right, both small and in
     the title colour. Slidev picks `global-bottom.vue` up automatically. -->
<template>
  <footer v-if="$slidev.nav.currentPage > 1" class="ct-footer">
    <span>&copy; con terra GmbH</span>
    <span>{{ $slidev.nav.currentPage }} | {{ $slidev.nav.total }}</span>
  </footer>
</template>
