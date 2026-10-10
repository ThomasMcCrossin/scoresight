# textocr_scoreboards

Real scoreboard and clock crops cut from Open Images photos (CC BY), with TextOCR's human transcriptions.

Built by `python -m ocr_eval.builders.textocr_scoreboards` (see its docstring); the manual review is in `ocr_eval/builders/textocr_scoreboards_review.json`. Licenses: see LICENSE and ATTRIBUTION.md.

1276 crops from 219 photos.

| Field type | Crops |
|---|---:|
| clock | 139 |
| number | 948 |
| other | 4 |
| text | 185 |

| Display technology | Crops |
|---|---:|
| broadcast | 69 |
| bulb | 60 |
| dotmatrix | 458 |
| flip | 94 |
| lcd | 74 |
| led7 | 353 |
| printed | 168 |

| Split | Crops |
|---|---:|
| dev | 268 |
| test | 1008 |

Field types come from the transcription: `clock` for M:SS, MM:SS and S.D, `number` for 1-3 digits (scores, periods, innings and other numbers are not told apart), `text` for ordinals and scoreboard words. Display technologies were assigned per photo or crop in the review.

## Selection

TextOCR words of the photos, skipped automatically:

| Reason | Words |
|---|---:|
| not a scoreboard value | 11309 |
| illegible in TextOCR | 4701 |
| over 12 per photo | 1774 |
| smaller than 12 px | 1480 |
| rotated more than 15 degrees | 336 |

Candidates dropped after cropping or in the review:

| Reason | Crops |
|---|---:|
| review: an analog clock or watch face, gauge or radio dial | 254 |
| review: a phone, computer, video game or app screen, not a scoreboard | 160 |
| review: a sign, banner, caption or other static text, not a scoreboard value | 137 |
| review: not legible (too small, blurred or dark) | 110 |
| another word box covers over 20% of it | 68 |
| review: a keypad or button label | 51 |
| review: a jersey or uniform number | 42 |
| review: unlit display segments: the transcription isn't what the display shows | 28 |
| review: an advertisement or logo | 20 |
| review: the value is cut off or covered in the crop | 13 |
| review: a device or menu label, not a scoreboard value | 7 |
| review: the transcription doesn't match the displayed value | 4 |
| review: vertical text | 2 |

Review corrections: texts corrected 0, field types set 4.
