# Reading `generate_handbook.py` — A Code Walkthrough for Non-Coders

This doc covers [`docs/sample-data/generate_handbook.py`](../sample-data/generate_handbook.py) —
the script that generates the fake "Orion Technologies Employee Handbook" PDF that every
golden-dataset question is written against.

This script doesn't compute a metric or drive an evaluation run, so it's a lighter, quicker read than
[`bleu-rouge-code-walkthrough.md`](bleu-rouge-code-walkthrough.md) — the walkthrough of the actual
scoring script. If you haven't read that one yet, read it first: this doc assumes you already know
`import`/`try...except`, f-strings, `csv.DictReader`, `dict.get`, list comprehensions,
`os.path.join`, and the `if __name__ == "__main__":` idiom, and won't re-explain them. Here we focus
on what's genuinely *new*: Python's class/inheritance syntax (the first object-oriented code in this
project).

## How to read this doc

The script is long (1,269 lines), but the vast majority of it is repetitive: the same handful of
methods get called with different chapter text, over and over, 14 times. So this doc is split in two:

1. **The class definition (lines 1–192)** — explained in full, since this is genuinely new syntax.
2. **The content section (lines 195–1269)** — explained as *a pattern*, with two or three concrete
   examples. Once you can read one chapter, you can read all fourteen; we won't walk through all of
   them.

---

## 1. Setup: imports and color constants (lines 1–15)

```python
from fpdf import FPDF


COMPANY = "Orion Technologies, Inc."
PRIMARY = (30, 64, 175)    # deep blue
ACCENT  = (79, 70, 229)    # indigo
LIGHT   = (241, 245, 249)  # slate-50
BLACK   = (15, 23, 42)
GREY    = (100, 116, 139)
```

`FPDF` is the central class from the `fpdf2` library (a PDF-generation library — despite the package
still being importable as `fpdf` for backwards compatibility with the older `fpdf` project it forked
from). Colors here are stored as **tuples of three numbers** — RGB (red, green, blue) values from 0 to
255 — one tuple per named color used throughout the document, so "deep blue" is defined once as
`PRIMARY` and reused everywhere instead of typing `(30, 64, 175)` by hand 40 times. Why this matters
becomes clear in the next section, where these tuples get *unpacked*.

## 2. `class HandbookPDF(FPDF):` — the first class in this project (line 18)

```python
class HandbookPDF(FPDF):
```

Every other script in this project has been built from plain functions. This line introduces a
**class** — a blueprint for creating an *object* that bundles together both data (state) and behavior
(methods) in one unit. Here, `HandbookPDF` is the blueprint for "a PDF document with Orion's specific
styling baked in."

**`(FPDF)` in parentheses is inheritance.** It means: "`HandbookPDF` starts out as a copy of everything
the `FPDF` class already knows how to do — drawing text, rectangles, lines, managing pages — and then
adds more on top, or replaces specific pieces." `FPDF` is called the **parent class** (or base class);
`HandbookPDF` is the **subclass**. Without writing a single line of PDF-rendering code, `HandbookPDF`
already inherits dozens of ready-made methods like `.cell()`, `.multi_cell()`, `.rect()`, `.line()`,
and `.add_page()` — you can see all of them used throughout this file, but none of them are *defined*
here; they come from `FPDF` for free.

## 3. `header()` and `footer()` — overriding, and what `self` means (lines 20–43)

```python
def header(self):
    if self.page_no() == 1:
        return
    self.set_fill_color(*PRIMARY)
    self.rect(0, 0, 210, 12, "F")
    self.set_font("Helvetica", "B", 8)
    self.set_text_color(255, 255, 255)
    self.set_xy(10, 3)
    self.cell(0, 6, f"{COMPANY}  |  Employee Handbook  |  Confidential", align="L")
    self.set_xy(10, 3)
    self.cell(0, 6, f"Page {self.page_no()}", align="R")
    self.ln(8)

def footer(self):
    if self.page_no() == 1:
        return
    self.set_y(-12)
    self.set_draw_color(*ACCENT)
    self.set_line_width(0.4)
    self.line(10, self.get_y(), 200, self.get_y())
    self.set_font("Helvetica", "", 7)
    self.set_text_color(*GREY)
    self.set_xy(10, self.get_y() + 2)
    self.cell(0, 5, "© 2025 Orion Technologies, Inc. -- All rights reserved. This handbook is for internal use only.")
```

**`self` is the first parameter of every method in a class, and it refers to "this specific object the
method is currently running on."** Plain-language: when you eventually create a PDF object (as this
script does near the bottom, `pdf = HandbookPDF(...)`), every method call like `pdf.header()` secretly
passes `pdf` itself in as the first argument — Python does this automatically, which is why you never
see `self` filled in at the *call* site, only at the *definition* site. Inside the method, `self` is
how the code refers back to its own current state — `self.page_no()` asks "what page number is *this*
PDF object currently on?", `self.set_xy(10, 3)` changes *this* PDF object's current drawing position.

**`header` and `footer` are special, reserved method names that `FPDF` itself calls automatically**,
once per page, every time `self.add_page()` runs. `FPDF` already ships with its own default (blank)
`header()` and `footer()` methods. By defining methods with those *exact same names* inside
`HandbookPDF`, this code **overrides** them — replacing the parent class's version with its own. This
is the payoff of inheritance: rather than manually calling "draw the page banner" after every single
`add_page()` throughout the 14 chapters below, you define it once here, and the library's own internal
page-creation logic calls it for you, automatically, every time.

Notice the guard at the top of both: `if self.page_no() == 1: return`. This is a plain early-exit —
"if this is the cover page, draw nothing and stop" — because the cover page (built separately in
`cover()`, below) has its own full-bleed design and shouldn't get the standard blue banner and
copyright footer that every other page gets.

**`self.set_fill_color(*PRIMARY)` — tuple unpacking with `*`.** `set_fill_color` (a method inherited
from `FPDF`) expects **three separate arguments** — red, green, blue — called like
`set_fill_color(30, 64, 175)`. But `PRIMARY` is stored as **one tuple** containing all three numbers:
`(30, 64, 175)`. The `*` in front of a tuple (or list) at a call site means "unpack this collection
back into separate positional arguments, one per item," rather than passing the whole tuple as a
single object.

```
$ python3.11 -c "
def f(a, b, c):
    return a + b + c

print(f(*(1, 2, 3)))
"
6
```

`f(*(1, 2, 3))` is exactly equivalent to writing `f(1, 2, 3)` by hand — the `*` just lets you keep the
three numbers bundled as one named tuple (`PRIMARY`) up at the top of the file, and still hand them to
a function that wants three separate arguments, without spelling out `set_fill_color(PRIMARY[0],
PRIMARY[1], PRIMARY[2])` everywhere. You'll see `*PRIMARY`, `*ACCENT`, `*GREY`, and `*BLACK` used this
way throughout the whole file.

## 4. The custom helper methods (lines 45–192)

Everything from line 45 (`# ── helpers ──`) to line 192 is a set of **ordinary methods** this class
adds on top of what `FPDF` provides — none of these names are special to the library the way `header`
and `footer` are; they're just this project's own shortcuts for "draw this kind of content block, in
Orion's consistent visual style, without repeating ten low-level formatting calls every time." This is
what makes the content section (Part 2, section 5 below) readable: instead of every chapter manually
setting fonts, colors, and positions, it just calls `pdf.section_heading("...")` or `pdf.bullet([...])`.

A quick tour, since the content section below assumes you recognize each of these on sight:

| Method | What it draws |
|---|---|
| `cover()` (47–93) | The full front cover page — logo block, title, address, version note |
| `toc_page(sections)` (95–103) | The table of contents, from a list of `(number, title, page)` tuples |
| `chapter_title(text)` (105–117) | A large heading with a horizontal rule underneath, e.g. "1. Welcome to Orion Technologies" |
| `section_heading(text)` (119–127) | A shaded numbered subheading, e.g. "2.3 Employment Classifications" |
| `sub_heading(text)` (129–135) | A smaller, unshaded heading one level below `section_heading` |
| `body(text)` (137–142) | A paragraph of regular body text, wrapped to the page width |
| `bullet(items, indent=14)` (144–151) | A bullet list from a list of strings |
| `table(headers, rows, col_widths=None)` (153–174) | A bordered table with a colored header row |
| `info_box(label, text)` (176–188) | A callout box with a label bar and bordered body — used for things like "Benefits Eligibility" |
| `new_chapter(title)` (190–192) | Starts a new page and immediately draws its `chapter_title` |

Two details inside `table()` (lines 153–174) are worth calling out on their own, since they're new
patterns:

```python
for h, w in zip(headers, col_widths):
    self.cell(w, 7, h, border=1, fill=True)
```

**`zip(headers, col_widths)`** pairs up two lists *position by position* — the first header with the
first column width, the second header with the second width, and so on — so the loop can draw each
column heading at exactly the width reserved for it, in one pass, instead of looping over indices and
looking both lists up by hand.

```
$ python3.11 -c "print(list(zip(['a', 'b'], [10, 20])))"
[('a', 10), ('b', 20)]
```

`zip` on its own produces pairs lazily (similar in spirit to the generator expressions from the
bleu-rouge walkthrough); wrapping it in `list(...)` here is just to print it for demonstration — the
real code uses it directly in the `for h, w in zip(...)` loop, tuple-unpacking each pair into `h`
(header text) and `w` (column width) as it goes.

```python
self.set_fill_color(241, 245, 249) if fill else self.set_fill_color(255, 255, 255)
```

This line is a **conditional expression used purely for its side effect**, which is a slightly unusual
and terser style worth flagging. Normally a conditional expression (`x if cond else y`, which you saw
in the bleu-rouge walkthrough) is used to *produce a value* that gets stored or returned. Here,
neither branch produces a value anyone keeps — both `set_fill_color(...)` calls just change the PDF's
drawing state and return nothing useful. It's really just a compact way of writing an if/else block
that happens to fit on one line. The more conventional, longer form would be:

```python
if fill:
    self.set_fill_color(241, 245, 249)
else:
    self.set_fill_color(255, 255, 255)
```

Both do exactly the same thing — alternate each table row between a light shaded background and white,
giving the classic "zebra-striped" table look (`fill = not fill` at the end of each loop iteration
flips the flag for next time).

## 5. The content section (lines 195–1269) — a pattern, not a walk

```python
# ═══════════════════════════════════════════════════════════════════════════
# CONTENT
# ═══════════════════════════════════════════════════════════════════════════

pdf = HandbookPDF(orientation="P", unit="mm", format="A4")
pdf.set_auto_page_break(auto=True, margin=18)
pdf.set_margins(10, 14, 10)
```

**This is module-level code — not inside any function.** Every other script covered in this project's
walkthroughs wraps its logic in a `main()` function and only runs it behind an `if __name__ ==
"__main__":` guard, specifically so the file's functions could be safely *imported* elsewhere without
automatically re-running the whole script. `generate_handbook.py` deliberately does not follow that
pattern anywhere below this point: `pdf = HandbookPDF(...)` and the roughly one hundred method calls
that follow it just sit directly in the file and execute top to bottom the moment the file is run.
That's a reasonable choice here because this file is a **one-shot content-generation script** — nobody
is ever going to `import generate_handbook` to reuse a function from it; its only job, ever, is "run me
and produce a PDF." The `main()` + guard pattern exists to protect against accidental side effects on
import; a script whose *entire point* is a side effect (writing a file) doesn't need that protection.

From here, `pdf` is one `HandbookPDF` object (an **instance** of the class from section 2), and every
line below calls one of its methods, building up the PDF one instruction at a time, entirely in memory
— nothing gets written to disk yet.

**One representative table example** — Section 2.3, around lines 316–327:

```python
pdf.section_heading("2.3  Employment Classifications")
pdf.table(
    ["Classification", "Hours per Week", "Benefits Eligible", "Description"],
    [
        ["Full-Time Regular",   "40+",    "Yes (full)",    "Permanent position, ongoing basis"],
        ["Part-Time Regular",   "20-39",  "Yes (pro-rata)","Permanent position, reduced hours"],
        ["Part-Time Limited",   "< 20",   "Limited",       "Ongoing, fewer than 20 hrs/week"],
        ["Fixed-Term",          "Varies", "Yes (full)",    "Time-limited project or role"],
        ["Intern / Co-op",      "Varies", "No",            "Student placement, typically 12-16 wks"],
    ],
    col_widths=[42, 32, 36, 80],
)
```

`section_heading(...)` draws the shaded "2.3 Employment Classifications" bar. `table(...)` then takes
four column headers, a list of five rows (each row itself a list of four strings, matching the header
count), and explicit millimeter widths for each of the four columns (summing to 190mm — the usable
page width after margins). Internally, `table()` runs the `zip(headers, col_widths)` loop from section
4 to draw the header row, then loops over `rows` drawing each data row with alternating shading.

**One representative bullet-list example** — the five core values, lines 269–276:

```python
pdf.sub_heading("Our Five Core Values")
pdf.bullet([
    "Craft -- We take pride in our work and hold ourselves to a high standard of quality.",
    "Transparency -- We default to openness. Information flows freely at Orion.",
    "Customer obsession -- Every decision starts with the question: does this make our customers more successful?",
    "Inclusion -- We build a workforce as diverse as the world we serve.",
    "Accountability -- We own our outcomes, celebrate our wins, and learn from our failures without blame.",
])
```

`bullet(...)` takes a plain list of strings and draws one `*`-prefixed, word-wrapped paragraph per
item, indented from the left margin — no per-item formatting calls needed; the list itself is the only
input.

**Every other chapter in the file (lines ~225–1264) follows this exact same handful of method calls —
`new_chapter`, `section_heading`, `sub_heading`, `body`, `bullet`, `table`, `info_box` — with different
text.** Chapter 3 (Code of Conduct), Chapter 6 (Benefits), Chapter 7 (Time Off), and so on are each
just more calls to the same nine methods from section 4, in different combinations. Once you can read
the two examples above, you can read all fourteen chapters; there's no new mechanism introduced after
this point.

## 6. Writing the file to disk (lines 1266–1268)

```python
output_path = "/Users/KC/Documents/rag-demo/docs/sample-data/orion-technologies-employee-handbook.pdf"
pdf.output(output_path)
print(f"Generated: {output_path}  ({pdf.page_no()} pages)")
```

Every single call before this line — `cover()`, all fourteen `new_chapter()` calls, every `body()`,
`table()`, and `bullet()` — only built up *in-memory drawing instructions* inside the `pdf` object.
Nothing touched the filesystem. `pdf.output(output_path)` is the one line in the whole script that
actually renders those instructions into real PDF bytes and writes them to disk at the given path.
`pdf.page_no()` (also used inside `header()`/`footer()` earlier) reports the final page count, purely
for the confirmation message.

---

# Python concepts you picked up in this file

| Concept | What it means | Where it appeared |
|---|---|---|
| `class Name(ParentClass):` | Defines a new class that inherits everything the parent class already does | `class HandbookPDF(FPDF):`, line 18 |
| `self` | The specific object a method is currently running on; passed automatically at the call site | Every method in `HandbookPDF` |
| Method overriding | Redefining a method with the same name as one the parent class already provides | `header()`, `footer()`, lines 20–43 |
| Tuple unpacking with `*` (`f(*some_tuple)`) | Splits a tuple back into separate positional arguments at a call site | `self.set_fill_color(*PRIMARY)` |
| `zip(list_a, list_b)` | Pairs up two lists position-by-position for a single combined loop | `table()`, line 161 |
| Conditional expression for a side effect | `x() if cond else y()` used to pick which side-effecting call runs, not to produce a value | `table()`, line 167 |
| Module-level (unwrapped) script code | Code that runs top to bottom with no enclosing function or `__main__` guard, because the file is a one-shot generator, not an importable library | `generate_handbook.py`, lines 199–1268 |

---

# What to test here

| Script | Risk | How to catch it |
|---|---|---|
| `generate_handbook.py` | Regenerating the handbook (new wording, renumbered sections, changed figures) silently desyncs every hand-matched `reference_answer` / `expected_chunk` pair in `golden-dataset.csv`, since those were written against *this exact text* | Never regenerate the handbook without immediately re-checking (or re-writing) the golden dataset rows whose `expected_chunk` cites the changed section; consider a checksum or version note tying a golden-dataset revision to a specific handbook version |
| `generate_handbook.py` | `output_path` is hardcoded to an absolute path (`/Users/KC/Documents/rag-demo/...`) rather than derived from `__file__` | Running this script from a different machine or checkout location will fail or write to the wrong place; consider using `os.path.dirname(os.path.abspath(__file__))` instead, if the script is ever run outside this exact machine |

---

# See also

- [docs/sample-data/](../sample-data/) — the generated
  `orion-technologies-employee-handbook.pdf` itself, the document every golden-dataset question is
  written against
- [bleu-rouge-code-walkthrough.md](bleu-rouge-code-walkthrough.md) — the full walkthrough of the main
  scoring script this doc assumes you've already read
