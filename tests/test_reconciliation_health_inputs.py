from reporting_core.reconciliation_health import summarize_reconciliation_health


def test_summary_rejects_invalid_result_type():
    try:
        summarize_reconciliation_health([object()])
    except TypeError:
        pass
    else:
        raise AssertionError("expected TypeError")
