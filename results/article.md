# How Many Colors Can The Human Eye See?
# The famous "10 million colors" answer is wrong.

*Or: how a rough estimate from 1943 became an unexamined fact — and what happens when you actually do the math*

---

Go to Google right now and type "how many colors can the human eye see." You'll get a confident answer: between 1 million and 10 million.

Stop. Read that again. Between 1 million and 10 million. That's not an answer — that's a shrug dressed up as a fact. A ten-to-one range would be laughed out of any other discipline. If your doctor said your cholesterol was "between 100 and 1,000," you'd find a new doctor. If an engineer said a bridge could hold "between 10 and 100 tons," no one would drive across it. But when the question is about human vision and the source is a search engine echoing eighty years of unchecked repetition, we just nod and move on.

We didn't.

The answer isn't 10 million. It isn't "between 1 million and 10 million." It's roughly **325,000** — off by a factor of 30.

Here's how that happened, and why you should care about the difference.

---

## What counts as a different color?

Before we get to the method, we need to establish what we're actually counting — because a different *number* does not mean a different *color*.

If you've ever used a color picker, you know colors can be described as numbers. RGB(99, 50, 200) is a specific purple. Change the red channel by one — RGB(98, 50, 200) — and you have a different number. But you don't have a different color. Place them side by side and no human being on earth can tell them apart. The number changed. The perception didn't.

A standard 8-bit display can address 16.7 million RGB combinations. A 10-bit display can address over a billion. Those aren't colors — they're coordinates. Most of them map to the same perceptual experience. The question isn't how many numbers a screen can produce. It's how many of those numbers *look different from each other* to a human observer. That's what we counted.

---

## How we counted

Rather than estimate, we enumerated. We packed the entire space of human-visible colors the way you'd pack a room with balls — placing each one so it doesn't overlap with anything already placed, and counting how many fit.

Each "ball" represents a neighborhood of colors too similar for the human eye to tell apart — like RGB(99, 50, 200) and RGB(98, 50, 200) living in the same neighborhood. The size of the ball depends on how strict your definition of "different" is — more on that in a moment.

The process: generate a grid of roughly 104 million candidate colors across the full range of human vision. Test each one against the physical boundary of what our visual system can perceive. Then walk through them, selecting colors that are distinguishable from everything already selected and claiming their neighborhood so nothing too similar gets counted again. When every candidate has either been selected or claimed, you stop and count.

The distance between colors was measured using CIEDE2000 — the most accurate color-difference formula standardized by the International Commission on Illumination. It accounts for the fact that your eye is better at distinguishing light colors than dark ones, that saturated colors are harder to tell apart, and that some hue regions are more sensitive than others. It's the gold standard for a reason.

We ran this at three thresholds simultaneously:

*[Visual: table showing the three tiers with plain-language definitions]*

| Threshold | What it means |
|-----------|---------------|
| **Lab detection** | The smallest difference a trained observer can detect under controlled conditions |
| **Professional match** | The threshold used in industrial color matching — "would a printer reject this?" |
| **Obvious difference** | A difference anyone would notice in everyday life |

The tiers matter as much as the totals.

---

## The bug that almost fooled us

The first four runs told us a very clean story. Too clean.

Every time we doubled the resolution of our grid, the count roughly doubled. Coarse grid: 313,000 colors. Fine grid: 1.8 million. Superfine: 4 million. Ultrafine: 8.4 million.

That should have been the first red flag. The number of colors a human can see is a physical property of the visual system — a constant. Measuring it more precisely should make your answer *converge*, not keep climbing. A result that doubles forever isn't measuring anything real. It's counting grid points.

We found the bug.

The algorithm processes the color space one thin horizontal slice at a time — like scanning a loaf of bread from bottom to top. Each slice was packed in complete isolation. Seeds placed in one slice were invisible to the next. At coarse resolution, that barely mattered — adjacent slices were far enough apart. But at fine resolution, two grid points at the same color position in neighboring slices were perceptually identical — separated by far less than any noticeable difference. Both got counted, because neither could see the other.

The algorithm was working perfectly as written. The error was architectural. Every real color was being counted dozens of times — once for each thin slice of lightness near it. More resolution meant more slices meant more phantom duplicates.

The fix: as each slice is processed, keep a buffer of recently selected colors from previous slices. Before adding a new color, check it against that buffer. If it's too close to something already counted, skip it.

After the fix, the counts converged. Runs at increasing resolution added fewer and fewer new colors, tapering from 8% gains to under 1%. A final pass of 50 million random probes across the entire space found exactly 3 additional colors.

The packing was saturated.

---

## The real numbers

*[Visual: the three final counts, large and clean — 324,669 / 52,763 / 17,751]*

At the lab-detection threshold — the smallest change a trained observer can spot in controlled conditions — the human eye can distinguish roughly **325,000 colors**. Not 10 million. The old estimate was off by 30×.

But the ratios between tiers are arguably the more important finding:

**84% of the colors your eye can technically detect are distinctions that don't matter.** For every 6 colors your visual system can resolve, only 1 represents a difference that a printer, textile manufacturer, or paint mixer would actually care about. The rest are laboratory artifacts — real, but irrelevant to anyone doing professional color work.

**And for every 18 technically distinguishable colors, only 1 is a difference you'd notice walking through the world.** Under normal conditions — not in a lab, not comparing swatches side by side — you navigate roughly **17,750 obviously different colors**.

*[Visual: ratio diagram — 18 lab-detectable colors collapsing to 3 "professional" collapsing to 1 "obvious"]*

That's still a rich palette. It's also a number a human could conceivably engage with. It fits in a spreadsheet. It does not require scientific notation.

For context: a standard 10-bit display offers 1.07 billion addressable colors. That's roughly 20,000 times more colors than there are perceptually distinguishable ones at the professional threshold. The engineering headroom isn't just generous — it's absurd.

---

## So where did "10 million" come from?

Now that you know the actual number, the history of the wrong one becomes a different kind of story.

The figure traces to researchers named Nickerson and Newhall, who published an estimate in 1943. Others refined it over the following decades — most notably Pointer and Attridge in 1998. The method was intuitive: measure how many just-noticeable steps the eye can detect along each axis of color perception — lightness, colorfulness, hue — and multiply.

If you can distinguish 200 levels of lightness, 200 levels of colorfulness, and 200 hues, that's 200 × 200 × 200 = 8 million. Push the axis counts a bit and you reach 10 million.

Clean. Simple. Wrong.

The problem is that color perception isn't a cube. The three axes aren't independent, and the shape of what humans can actually see isn't rectangular — it's an irregular, asymmetric blob that changes dramatically depending on where you are in it.

*[Visual: the shape of the human visual gamut in 3D — not a box, a lumpy blob that pinches near black and white]*

Near black, the range of distinguishable colors is tiny. Near white, same. The widest cross-section sits in the mid-lightness range. Multiplying axis counts assumes equal richness at every lightness level. Reality doesn't cooperate.

There's also the matter of how perceptual distance works. A step that registers as different in yellow-green might be invisible in blue-purple. The multiplication method assumes every step is the same size everywhere. It isn't.

The 10 million figure doesn't describe human vision. It describes a box that human vision doesn't come in.

---

## We're not the only ones who found this

In 2013, a color scientist named John Seymour ran a completely different experiment. He generated 500 million random physically realizable reflectance spectra, converted them to lab coordinates, and counted how many distinguishable colors they produced — using the same perceptual distance formula we used (CIEDE2000).

He got **346,005**. We got **324,669**. Two independent methods, different algorithms, different years, within 6.6% of each other.

That's not a coincidence. That's two measurements of the same constant.

And there's a third. In 1939 — the same year Judd and Kelly published their 10 million figure — psychologists Boring, Langfeld, and Weld estimated **300,000** discriminable colors in their textbook *Introduction to Psychology*. Three independent sources, spanning eighty-seven years: 300,000 … 346,005 … 324,669. The right answer was in the literature from the beginning. It just lost the popularity contest to a bigger, rounder number.

And once you see this, the entire eighty-year disagreement in the literature collapses into a single variable: **which distance formula you use**.

The original 1943 method didn't use a color space at all — it just multiplied axis steps. Result: 7.5 to 10 million. Starting in the late 1990s, researchers measured the volume of human color space using CIELAB, an early perceptual model, and divided it into unit cells. Every one of them got roughly **2 to 2.5 million** — Pointer and Attridge (1998), Linhares and Nascimento (2008), Flinkman (2012). Consistent, reproducible, and still too high.

The problem was CIELAB itself. It was designed to be perceptually uniform, but it isn't — it dramatically over-counts in saturated yellows and blues, where the eye is far less sensitive than the model assumes. CIEDE2000 was created specifically to fix those distortions. Every study that uses it lands in the same range: **300,000 to 350,000**.

The literature wasn't contradictory. It was a timeline. Each generation of measurement tools got closer. The 10 million estimate, the 2 million estimates, and the 325,000 answer aren't competing claims — they're the same question asked with increasingly accurate instruments.

---

## How a number goes unchecked for eighty years

If the science was improving all along, why did "10 million" survive?

Because the people refining the measurements were publishing in journals that color scientists read, and the people repeating "10 million" were writing textbooks, Wikipedia articles, and display marketing copy. The correction never reached the channels doing the repeating.

This is a pattern worth noticing. An estimate enters the literature. Textbooks cite it. Wikipedia cites the textbooks. Marketing departments cite Wikipedia. Within a generation, the estimate has been laundered into a fact — not because anyone verified it, but because the system that propagates knowledge doesn't have a built-in mechanism for going back and checking.

The original researchers weren't wrong to estimate. Their method was reasonable for 1943. What failed was the eighty years of repetition that followed — a long game of telephone in which nobody thought to hang up and dial the original number.

---

## Your trivia prize

Here is a piece of information that is true, independently corroborated, and entirely useless in any social context where you might try to deploy it.

The human eye can see approximately 325,000 colors.

Not 10 million. That number came from multiplying axis counts together without accounting for the actual shape of human vision — a shortcut that seemed reasonable in 1943 and went unchallenged for eighty years because the result was plausible enough to repeat and too esoteric for anyone to check.

Now three independent sources — spanning eighty-seven years, using completely different methods — have landed on the same answer. It's on GitHub. Every seed color is logged. The packing is saturated.

You will not win Trivial Pursuit with this. The card still says 10 million. But you'll know they're wrong, and that's worth something.

Probably.

---

*Full source and methodology at [github.com/caoimghgin/hueknew](https://github.com/caoimghgin/hueknew)*
