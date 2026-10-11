# synthetic_7seg

Rendered 7-segment LED and LCD digits (scores, clocks, periods): a synthetic control set, not a measure of real-world accuracy.

Built by `python -m ocr_eval.builders.synthetic_7seg` (deterministic). Each crop is a
display rendered by `tests/synthetic_images.seven_segment`, coloured as a lit LED (red,
amber or white segments on black) or a reflective LCD (dark segments on grey-green),
then lightly blurred and given Gaussian noise. Licensed CC0-1.0.
