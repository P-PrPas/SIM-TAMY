"""Published measurement counts never convert skips, crashes or failures into passes."""

import pytest

from scripts.build_validation_report import counts


def test_junit_outcomes_are_counted_separately(tmp_path):
    path = tmp_path / "results.xml"
    path.write_text(
        "<testsuites><testsuite><testcase/><testcase><failure/></testcase><testcase><error/></testcase><testcase><skipped/></testcase></testsuite></testsuites>"
    )
    assert counts(path, 1) == dict(passed=1, failed=1, errors=1, skipped=1)


@pytest.mark.parametrize("exitcode", [0, 1, 2, 5])
def test_missing_results_are_not_a_pass(tmp_path, exitcode):
    assert counts(tmp_path / "missing.xml", exitcode)["errors"] == 1
