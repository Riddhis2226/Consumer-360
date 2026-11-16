# Consumer-360 — Project Plan

**Goal**  
End-to-end customer analytics on the UCI Online Retail II dataset (~1.07M transaction rows). Combine:

- **Analytics** — What happened (descriptive, RFM, cohorts, product & geography performance)
- **Data Science** — What is likely to happen (CLV, churn risk, next-purchase propensity, market basket)
- **Business Intelligence** — What action to take (segment-specific plays, prioritized customer lists, dashboards)

**Current foundation (already in repo)**  
A production-minded PostgreSQL redesign lives in `consumer360_sql_redesign_v2/`:

- Raw → Staging → Warehouse (dimensions + transaction-line fact)
- Customer 360 materialized view
- RFM scoring & validation
- Cohort retention with explicit caveats
- Aggregate serving marts (`mart.*`) + restricted customer-level mart (`mart_private`)
- Data-quality logging, refresh procedure, and validation scripts
- Clear data contract and requirements traceability

Raw data is present:  
`data/raw/online_retail_II_2009-10.csv` + `data/raw/online_retail_II_2010-11.csv`

---

## Recommended Stack

| Layer              | Choice                                      | Rationale |
|--------------------|---------------------------------------------|-----------|
| Data warehouse     | PostgreSQL 14+                              | Already designed & scripted |
| Analytics / BI     | SQL marts + Power BI or Metabase / Streamlit | Fast path to stakeholder views |
| Data Science       | Python (pandas, scikit-learn, LightGBM, lifetimes / PyMC-Marketing, mlxtend) | Flexible modelling + SHAP explanations |
| Orchestration      | `run_all.sql` + simple refresh procedure; later Airflow / cron | Keep first version simple |
| Version control    | This repo                                   | Single source of truth |

Python notebooks will sit alongside the SQL warehouse and read either directly from PostgreSQL or from exported parquet/CSV snapshots of the marts.

---

## Phased Roadmap

### Phase 0 — Foundations (complete / near-complete)
- [x] Raw data landed
- [x] SQL architecture redesign (schemas, DQ, overlap handling, returns logic, Unknown Customer)
- [x] Customer 360 view, RFM, cohort, serving marts
- [ ] Local PostgreSQL build & validation against `ops.data_quality_result`
- [ ] Sign-off on product classification and Unknown Customer volume

### Phase 1 — Descriptive Analytics & BI (next)
1. Execute `sql_files/run_all.sql` on a local PostgreSQL instance.
2. Review DQ results and fix any remaining classification issues.
3. Build first dashboard (Power BI / Streamlit / Metabase) on `mart.*` tables:
   - Executive KPIs (net merchandise revenue, customers, AOV, return rate)
   - RFM segment distribution & spend
   - Cohort retention matrix
   - Top products & geography performance
4. Document key findings (“what happened”).

### Phase 2 — Predictive Data Science
1. Export or query customer features from `dw.mv_customer_360` / `mart_private.customer_segments`.
2. **CLV** — BG/NBD + Gamma-Gamma (or simpler regression baseline) with hold-out validation.
3. **Churn** — Define prediction horizon (e.g. 90-day inactivity), train LightGBM / logistic model, SHAP explanations.
4. **Market basket** — FP-Growth / association rules on merchandise invoices.
5. **Next-purchase propensity** (optional stretch).
6. Write short model cards (assumptions, metrics, limitations).

### Phase 3 — Action Layer & Packaging
1. Join predictions back to customer segments.
2. Produce prioritized action lists (e.g. “high-CLV / high-churn-risk Champions to save”).
3. Segment playbooks (what to do for Champions, At Risk, Hibernating, etc.).
4. Final interactive dashboard + one-page executive summary of recommended actions.
5. Optional: simple automated refresh pipeline.

---

## Success Criteria

- Clean, reproducible warehouse that passes the validation suite.
- At least three solid descriptive views (RFM, cohorts, product/geo).
- One validated CLV model and one churn model with hold-out metrics and SHAP.
- Dashboard or report that answers: “Which customers should we act on, and why?”
- All code and logic version-controlled and documented.

---

## Immediate Next Actions

1. Confirm PostgreSQL is available locally (or decide on a cloud Postgres).
2. Run the full SQL build (`run_all.sql`) and inspect `ops.data_quality_result`.
3. Create a lightweight Python environment (`requirements.txt` + notebooks folder) that can connect to the warehouse.
4. Draft the first dashboard skeleton on the existing marts.

---

## Folder Layout (target)

```text
Consumer-360/
├── Project_Plan.md                 ← this file
├── data/
│   └── raw/                        ← UCI CSVs (already present)
├── consumer360_sql_redesign_v2/    ← current SQL warehouse (keep as source of truth)
├── notebooks/                      ← Phase 2 Python work (to be created)
│   ├── 01_eda_and_features.ipynb
│   ├── 02_clv.ipynb
│   ├── 03_churn.ipynb
│   └── 04_market_basket.ipynb
├── dashboards/                     ← Streamlit / Power BI files (to be created)
└── docs/                           ← additional model cards, findings, playbooks
```

---

## Working Principles

- Prefer the existing SQL warehouse over re-implementing the same logic in Python.
- Keep customer-level PII/IDs in `mart_private` only.
- Document every modelling assumption and validation metric.
- Ship incremental value: working dashboard on descriptive marts before perfect models.

---

*Last updated: 2026-11-16*  
*Status: Plan finalized — ready for Phase 1 execution*
