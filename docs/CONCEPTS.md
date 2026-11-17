# Concepts

A slow-shutter whip pan is light integrated over time while the camera sweeps. This tool reproduces it directly instead of faking it with a spatial blur:

- **Virtual camera on a strip.** For `left/right/up/down`, A and B are joined side by side and a window slides over them, so the seam never needs padding or mirroring and B arrives already in motion.
- **Diagonals.** A and B sit on opposite corners of a 2W x 2H canvas. Each clip is mirror-tiled into the empty corners, and the two are cross-faded between 40 % and 60 % of the travel, hidden by the peak blur.
- **Shutter integration.** Each output frame averages sub-frames across the shutter window (`--shutter`, in frame-times). Sub-frame count follows the travel (about 1 per 2 px), so fast frames get hundreds of samples and slow frames few.
- **Linear light.** Averaging happens after gamma 2.2 decoding, so bright pixels streak the way they do on a sensor.
- **Speed-driven extras.** Chromatic split, bloom, over-exposure and grain scale with the instantaneous speed, so they peak at the cut and vanish at rest.

## Not modelled
Rolling-shutter skew, handheld shake, true sensor saturation and optical-flow blur. Premiere/After Effects tricks (Transform motion blur, directional blur on an adjustment layer, Motion Tile) are covered by the virtual-camera approach. Resolve's Temporal Smear mixes neighbouring frames in time, which this tool does not do.

## In camera vs. in post
Operators who shoot it for real pan in the same direction and at a similar speed in both shots, use a slow shutter, cut in the middle of each blur and match brightness at the join. A synthetic whip is the fallback when that footage does not exist.
