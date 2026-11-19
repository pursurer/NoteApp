# Class 10 - Stored XSS fix (NotesApp flaw #10 closed)

**Student:** HAOJIE SONG (2023905496)

```text
STORED XSS FIX — NotesApp flaw #10 closed

  Break:  comment on note 1 =  <script>alert('XSS by Eve')</script>
          opened as alice -> raw <script>alert('XSS by Eve')</script> in her dashboard; a script in the
          comment really ran in her logged-in browser page

  Fix:    removed {% autoescape false %} in dashboard.html AND teacher.html

  Closed: same comment now shows as text -> &lt;script&gt;alert(&#39;XSS by Eve&#39;)&lt;/script&gt;, no alert

  Real use still works:  "score < 10 ... & retry" displays correctly [x]
```

The fixed cell, in both [`web/templates/dashboard.html`](../web/templates/dashboard.html) and
[`web/templates/teacher.html`](../web/templates/teacher.html):

```html
<td>{{ n.comment }}</td>
```

## How the proofs were taken

Everything ran on my own NotesApp clone, in an isolated docker project with a fresh database (seed data only).

- **Break.** As `prof.turing` I saved the lab's comment on note 1. As `alice`, `grep -o "<script>.*</script>"`
  on `/dashboard` printed `<script>alert('XSS by Eve')</script>`. In a real browser the pane could not show an
  `alert()` dialog, so I saved a second comment with the same flaw and a visible effect
  (`<script>document.title='XSS ran as '+…</script>`). Opening alice's dashboard changed the page title to
  `XSS ran as out`, so the script ran inside her logged-in page.
- **Closed.** After removing the wrapper, the same comments are escaped. `grep "<script>alert"` finds nothing
  (`safe: no live <script> in the page`) and `&lt;script&gt;alert(&#39;XSS by Eve&#39;)&lt;/script&gt;` is in the page.
  Jinja also escapes the apostrophe as `&#39;`, which is correct. The teacher's page shows the same escaped text.
  In the browser the title stays `NotesApp`, and the `<td>` holds no `<script>` element.
- **Real use.** `score < 10 on part 1 & 2, see me` is sent as `score &lt; 10 on part 1 &amp; 2, see me` and displays as typed.
- All 49 existing regression tests pass with the fixed templates.

Source: [Class 10 lab - Your words run in someone else's browser](https://kristenpire.github.io/epita-security-labs/class10/stored-xss/).
