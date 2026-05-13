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

- Rule 1 — Think Before Coding. State assumptions and tradeoffs before changing code when the risk is not obvious from local context.
- Rule 2 — Simplicity First. Keep the smallest working module boundary; do not add speculative services or abstractions.
- Rule 3 — Surgical Changes. Touch only files needed for the current objective and match existing style.
- Rule 4 — Goal-Driven Execution. Define what has to pass, implement, then verify.
- Rule 5 — Minimal Modular System. Facts, mappings, source metadata, scoring inputs, thresholds, text, URLs, and review policies belong in tables or config files. Code should load, validate, orchestrate, and compute repeatable results.
- Keep online scoring deterministic. No online LLM API in `/api/submit`, `/api/report`, or the scoring engine.
- Treat LLMs only as offline draft-generation helpers. Drafts must keep lineage and require review before release.
- Do not hardcode questionnaire text, scoring thresholds, source URLs, RIASEC mapping rules, or generation policy in service code when a config file can own them.
- Do not hardcode user-facing report interpretation text in scoring code. Keep reviewed copy and case rules in config files so the main project can explain and revise outputs without changing engine logic.
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
- Automated tests must use a temporary DuckDB path such as `HOLLAND_DB_PATH`; they must not overwrite or shrink the developer's local `backend/data/holland.duckdb`.
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
