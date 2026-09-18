// One extra shortcut: `f` jumps to the FAQ slides and back.
//
// The FAQ slides sit behind the closing slide and are not part of the talk --
// they exist for the question round. Pressing `f` from anywhere remembers the
// current slide and jumps to the FAQ index; pressing it again returns to the
// slide it was pressed on.
//
// The FAQ slide number is looked up at runtime from a `faq: true` marker in the
// frontmatter, never hard-coded: a constant would be silently wrong the next
// time a slide is inserted anywhere before it.
//
// The marker is a custom frontmatter field rather than Slidev's own
// `routeAlias`, and that is a measured decision -- see slides/README.md. An
// alias on the `src:` block reaches every slide of the included file, so all
// five FAQ slides end up sharing one path and paging forward inside them lands
// back on the first one every time.
import { useNav } from '@slidev/client'
import type { NavOperations, ShortcutOptions } from '@slidev/types'
import { defineShortcutsSetup } from '@slidev/types'


export default defineShortcutsSetup((_nav: NavOperations, base: ShortcutOptions[]) => {
  const { slides, currentSlideNo, go } = useNav()

  // The slide the jump started from, so `f` can toggle back.
  let cameFrom: number | null = null

  function faqStart(): number | null {
    const found = slides.value.find(
      s => s.meta?.slide?.frontmatter?.faq === true,
    )
    return found ? found.no : null
  }

  return [
    ...base,
    {
      name: 'toggle_faq',
      key: 'f',
      fn: () => {
        const start = faqStart()
        if (start == null)
          return
        if (currentSlideNo.value >= start) {
          go(cameFrom ?? 1)
          cameFrom = null
        }
        else {
          cameFrom = currentSlideNo.value
          go(start)
        }
      },
    },
  ]
})
