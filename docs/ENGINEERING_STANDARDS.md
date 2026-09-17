# Engineering Standards

## Reporting integrity

- Raw business files must remain outside version control.
- Inputs are normalized into a documented canonical schema before KPI calculation.
- Numeric fields are validated for finiteness and non-negative business values.
- Demo data must remain clearly synthetic and reproducible.

## Testing

- Pure validation and calculation logic should have deterministic unit tests.
- Regression tests should accompany fixes to parsing or KPI rules.
- Changes to report schemas should include representative fixtures without real customer data.

## Change management

- Production changes should be made through focused branches and pull requests.
- Commit messages should describe the engineering change.
- No synthetic commits, fabricated metrics, or backdated history are used to satisfy repository evaluation criteria.
