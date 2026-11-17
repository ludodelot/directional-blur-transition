# Concepts

A slow-shutter whip pan is light integrated over time while the camera sweeps. This tool reproduces it directly instead of faking it with a spatial blur:

- **Virtual camera on a strip.** A and B are joined side by side and a window slides over them, so the seam never needs padding or mirroring and B arrives already in motion.
- **Shutter integration.** Each output frame averages sub-frames across the shutter window (`--shutter`, in frame-times). Sub-frame count follows the travel (about 1 per 2 px), so fast frames get hundreds of samples and slow frames few.
- **Linear light.** Averaging happens after gamma 2.2 decoding, so bright pixels streak the way they do on a sensor.
- **Speed-driven extras.** Chromatic split, bloom, overexposure and grain scale with the instantaneous speed, so they peak at the cut and vanish at rest.
- **Audio.** Pink-ish noise through a sweeping low-pass, an asymmetric envelope, a low thump on the cut, panned with the direction of travel.

## Not modelled
Rolling-shutter skew, true sensor saturation and optical-flow blur. Premiere/After Effects tricks (Transform motion blur, directional blur on an adjustment layer, Motion Tile) are covered by the virtual-camera approach. Resolve's Temporal Smear mixes neighbouring frames in time, which this tool does not do.
