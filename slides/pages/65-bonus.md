<div class="kicker">Beyond geospatial data</div>

# Bonus: Test systems, not just test data

<div class="note">
Test infrastructure we created with Agentic AI as well
</div>

<div class="lead">

**Goal:** infrastructure components with little effort, for temporary tests.<br/>
**Lifetime:** throwaway — built for just one or two tests. Mostly Docker images.

</div>

<div class="bonus-grid">

<div><b>GeoServer</b><br/>
WFS with stored queries, plus a curl test suite</div>

<div><b>SAML 2</b><br/>
Keycloak / SimpleSAMLphp as external IdP, fake test users</div>


<div><b>SMTP server</b><br/>
a mail endpoint for tests</div>

<div><b>LDAP</b><br/>
in Docker, with fake test users</div>

</div>

<div class="note">
Same way of working, other targets — these are not part of this repository.
</div>

<!--
Not part of the 15-minute slot: this sits behind the closing slide, in front of
the FAQ. Show it only if there is time, or if a question goes in this direction.

One sentence: "The same approach works one level up -- not the data in a system,
but the system itself, for a test that needs it once." The point is the
lifetime: nobody maintains these, they are built for one test and thrown away,
which is exactly what makes generating them cheap enough to be worth it.

Say the last line out loud if someone looks for these in the repository: they
are other projects, not committed here.
-->
