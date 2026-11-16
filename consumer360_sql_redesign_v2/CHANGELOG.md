# Redesign notes

This is a clean V2 SQL design, not an in-place patch. `00_create_schemas.sql` replaces the old raw staging table shape; `02_warehouse_schema.sql` drops and recreates the prior warehouse objects. Keep a backup of any existing database before running this full rebuild.

Major structural changes from the supplied V1 SQL pack:

- Raw columns are landed as text with `raw_row_id` and source-file lineage.
- Cross-file overlap uses exact row signatures and duplicate multiplicity; no invoice-level deletion.
- Same-file repeated rows are retained pending business review.
- Anonymous transactions remain in the fact via Unknown Customer key 0.
- Transaction-time country is modelled in `dim_country`.
- Non-merchandise lines remain in the fact with explicit product classification.
- Return sign logic includes both C-prefixed invoices and negative quantities.
- Customer purchase sequencing is invoice-grain so `LEAD` has a correct interpretation.
- Customer-level mart is moved to `mart_private`; aggregate marts remain in `mart`.
- Added pipeline run and data-quality result tables plus a reusable refresh procedure.

No SQL has been executed against the user's local PostgreSQL instance in this environment. Expected counts and performance targets must be measured locally.
