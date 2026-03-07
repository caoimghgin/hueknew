# The Blue Tail: Why Darkness Is Blue

## Finding

Below L* 5, the human visual gamut collapses to a narrow spike in the blue-red quadrant. Green (negative a*) does not appear at all until L* 6-7. The full "mollusk shell" shape of the gamut only opens up around L* 11.

In practical terms: near black, the only colors humans can distinguish are shades of blue.

## Data (Obvious tier, DE2000 = 5.0)

| L* | Seeds | a* range | Green seeds (a* < -5) | Notes |
|----|-------|----------|-----------------------|-------|
| 0  | 18    | 0 to 86  | 0                     | No greens. All seeds red-blue. |
| 1  | 15    | 8 to 105 | 0                     | Still no greens. |
| 2  | 15    | 19 to 121| 0                     | Pure tail. |
| 3  | 15    | 24 to 126| 0                     | Pure tail. |
| 4  | 16    | 33 to 110| 0                     | Pure tail. |
| 5  | 24    | -1 to 120| 0                     | First hint of a* approaching 0. |
| 6  | 36    | -8 to 127| 1                     | **First green seed.** Transition begins. |
| 7  | 26    | -21 to 126| 5                    | Green side opening up. |
| 9  | 45    | -34 to 125| 7                    | Shell widening. |
| 11 | 62    | -46 to 123| 12                   | Full shell shape emerging. |
| 15 | 67    | -66 to 127| 13                   | Wide gamut. |
| 19 | 100   | -82 to 123| 40                   | Full mollusk. |

## Why This Happens

The human eye's luminous efficiency function V(lambda) peaks at ~555nm (yellow-green). This means:

- **Reds and greens** have high luminous efficiency. Even small amounts of red or green light produce measurable brightness. By the time lightness drops to L* 5, these wavelengths have already gone achromatic -- indistinguishable from black.

- **Blues (~450nm)** have extremely low luminous efficiency. Blue photons contribute almost nothing to perceived brightness. This means blue light can be present at significant intensity while still producing very low L* values -- dark, but visibly chromatic.

Blue is the last color standing as you approach darkness.

## Cultural Connection

This physical reality may explain a well-documented pattern in historical linguistics. Across unrelated cultures, blue was consistently the last basic color term to emerge in language. Homer described the sea as "wine-dark." Many ancient languages had no word for blue, treating it as a shade of black or dark.

Berlin and Kay (1969) documented a near-universal sequence of color term evolution:

    black/white -> red -> yellow/green -> blue

The gamut data provides a physical basis for this. At low luminance levels -- firelight, twilight, dim interiors -- blue is the only hue that persists as a distinct chromatic experience. Everything else has already faded to black. If your daily experience of dark colors is overwhelmingly "black" and "slightly blue-black," there is little practical reason to name blue as a separate category. Blue only becomes an obvious, nameable experience at higher lightness -- open sky, certain minerals, rare flowers.

The bottom of the 3D gamut model is, in effect, a visual proof of why ancient cultures lumped blue with darkness.

## Visible in the Viewer

Launch the 3D viewer (`python3 launch/gamut-model.py`) and orbit to view the gamut from below. The narrow blue spike at the base is immediately visible -- the "tail" of the mollusk shape. Switch between Obvious and JND tiers to see the effect at different perceptual thresholds.
