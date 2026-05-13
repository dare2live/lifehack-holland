# lifehack-holland · Agent Rules

> This project is an independent questionnaire and assessment service for `lifehack`.

## Boundaries

- Workdir: `/Users/dp/Documents/M/lifehack-holland/`.
- GitHub: `https://github.com/dare2live/lifehack-holland`.
- This service owns SJT/Holland/IPIP question sources, responses, scoring, and report API.
- The main `lifehack` project calls this service by API or consumes reviewed result snapshots.
- Do not import Python modules from `lifehack` or `lifehack-datahub`.
- Do not write `/Users/dp/Documents/M/lifehack/backend/data/university.db`.
- If reading the main DB to prepare local mappings, connect with `read_only=True` and write only to this project's local `backend/data/holland.duckdb`.

## Architecture Rules

- Keep online scoring deterministic. No online LLM API in `/api/submit`, `/api/report`, or the scoring engine.
- Treat LLMs only as offline draft-generation helpers. Drafts must keep lineage and require review before release.
- Do not hardcode questionnaire text, scoring thresholds, source URLs, RIASEC mapping rules, or generation policy in service code when a config file can own them.
- Preserve lineage for every production question:
  - raw source file and source version
  - mother source and mother record id
  - transform level
  - dimensions and weights
  - review status and reviewer notes when applicable
- Preserve lineage for every option weight. One SJT item can compare multiple
  mother-template mechanisms, so item-level `mother_id` is not enough; each
  row in `sjt_weights` must carry source version, review status, and
  lineage JSON.
- Preserve lineage for every consistency rule. The rule layer is part of the model, so triggered penalties must explain source version, review status, trigger/verify fields, and penalty parameters.
- The final question bank should be small and reviewed. The thousands of O*NET/IPIP records are source material, not all user-facing questions.
- Keep the main `lifehack` contract stable: `/api/report/{submission_id}` must
  keep returning `submission_id`, `source_version`, `dimensions`,
  `holland_top3`, `mbti_type`, `cross_insight`,
  `recommended_cn_occupations`, `consistency_issues`, and `source_lineage`.

## Data Rules

- `holland.duckdb` is local runtime state and must not be committed.
- Generated candidate pools should go under ignored `backend/data/generated/`.
- Reviewed seed files under `backend/data/seed/` may be committed when they are intentionally curated and small.
- Any bridge from Chinese occupations to RIASEC must store enough lineage to explain which source row and which rule produced the label.

## Verification

- For Python changes, run:

```bash
python3 -m unittest discover -s tests -v
```

- For frontend JavaScript changes, run syntax checks when possible:

```bash
node --check frontend/js/chart.js
node --check frontend/js/survey_config.js
```
