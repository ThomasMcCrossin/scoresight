# commons_scoreboards

Real scoreboard fields (scores, clocks, shot clocks, periods, fouls ...) cut from Wikimedia Commons photos of physical scoreboards, labelled field by field.

Built by `python -m ocr_eval.builders.commons_scoreboards --cache DIR --frames` (see its docstring) from `ocr_eval/builders/commons_scoreboards_labels.json`, which re-checks every photo's license with the Commons API. Licenses: see LICENSE and ATTRIBUTION.md; crops of CC BY-SA photos are CC BY-SA.

1044 crops from 186 photos. `frames.jsonl` lists every photo with its rendition URL, license and all its labelled fields (boxes in the pixels of the 1280 px rendition), for whole-frame experiments; `frames/` has the photos downscaled.

Labels: model-assisted-unverified 1044. The boxes and texts were drawn and transcribed with a model's help (Claude), looking at every field zoomed in; fields that weren't clearly legible were left out. Check them with `python -m ocr_eval review commons_scoreboards` and apply the exported decisions with the builder's `--apply-review`.

| Field type | Crops |
|---|---:|
| clock | 156 |
| number | 359 |
| other | 8 |
| period | 78 |
| score | 309 |
| text | 134 |

| Role | Crops |
|---|---:|
| away_fouls | 13 |
| away_name | 66 |
| away_score | 147 |
| away_timeouts | 35 |
| ball_on | 21 |
| batter_runs | 23 |
| clock | 139 |
| down | 22 |
| home_fouls | 12 |
| home_name | 63 |
| home_score | 149 |
| home_timeouts | 35 |
| other | 122 |
| overs | 13 |
| penalty_player | 5 |
| penalty_time | 17 |
| period | 80 |
| runs | 13 |
| score | 15 |
| shot_clock | 19 |
| target | 2 |
| to_go | 23 |
| wickets | 10 |

| Display technology | Crops |
|---|---:|
| broadcast | 216 |
| bulb | 54 |
| dotmatrix | 304 |
| flip | 51 |
| led7 | 411 |
| printed | 8 |

| Sport | Photos |
|---|---:|
| 3x3 basketball | 1 |
| american football | 36 |
| association football | 34 |
| australian rules football | 1 |
| ball hockey | 4 |
| basketball | 39 |
| canadian football | 1 |
| cricket | 13 |
| ice hockey | 42 |
| table tennis | 6 |
| tennis | 1 |
| volleyball | 3 |
| wheelchair basketball | 5 |

| License | Crops |
|---|---:|
| CC-BY-2.0 | 146 |
| CC-BY-2.5 | 10 |
| CC-BY-3.0 | 25 |
| CC-BY-4.0 | 43 |
| CC-BY-SA-2.0 | 189 |
| CC-BY-SA-3.0 | 250 |
| CC-BY-SA-4.0 | 308 |
| CC0-1.0 | 46 |
| PDM-1.0 | 27 |

| Split | Crops |
|---|---:|
| dev | 142 |
| test | 902 |

Field types: `score` for scores (read like ScoreSight's Home Score box, 0-199), `clock` for game clocks and shot clocks showing tenths (`M:SS`, `MM:SS`, `S.D`), `period` for periods, quarters and innings (ScoreSight's Period box accepts 1-4), `number` for other numbers (shot clocks in whole seconds, fouls, timeouts, downs, cricket totals ...), `text` for team names and words, `other` for values with other characters (cricket overs such as `12.4`).

## Photos looked at and not used

| Reason | Photos |
|---|---:|
| fields too small or far away | 22 |
| display off | 7 |
| digits ambiguous | 5 |
| fields cut off or covered | 5 |
| blurred | 4 |
| strongly angled | 3 |
| image unusable | 1 |
| near-duplicate of another photo | 1 |
| no scoreboard field | 1 |
