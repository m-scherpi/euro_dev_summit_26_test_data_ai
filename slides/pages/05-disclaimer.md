# How all of this was made

<div class="lead">

Everything you will see today <br/> — all use cases, verification checks, and also these
slides —<br/> was built with **Claude Code**, agentic, in a local repository.

</div>

<div class="steps">
<div><b>Every prompt was logged</b>, word for word, with what worked and what did not.</div>
<div><b>A lot of work went into verifying</b> the results, not just into generating them. <br/>The Agent wrote the tests to verify itself.</div>
<div><b>Everything ran locally</b> — right up to the point where something actually needed to be published.</div>
</div>

<div class="note">
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
