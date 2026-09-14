# How all of this was made

<div class="lead">

Everything you will see — the five use cases, the checks, and these slides —
was built with **Claude Code**, an agent working in a local repository.

</div>

<div class="steps">
<div><b>Every prompt is logged</b>, word for word, with what worked and what did not.</div>
<div><b>The work went into verifying</b> the results, not into generating them.</div>
<div><b>Everything ran locally</b> — right up to the moment something was published.</div>
</div>

<div class="pt-6 text-sm opacity-80">
These slides are part of it: written as Markdown with <b>Slidev</b>, in the same
repository, built and deployed by CI.
</div>

<!--
40s. Say this once, plainly, so nobody has to wonder later how the code and the
data came about. The prompt log is the reason this talk can show the failures as
well as the results: they are all written down, including the iterations that
went nowhere. And say the honest ratio out loud — generating was fast, checking
was the work.
-->
