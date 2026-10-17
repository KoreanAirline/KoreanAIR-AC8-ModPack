"""One release only: exact hashes plus an owner test or explicit test waiver."""
VERSION, BUILD = '2.3', 2026101701

def release_authorized(approval, hashes):
    if approval.get('version') != VERSION or approval.get('build') != BUILD:
        return False
    if approval.get('release_approved') is not True or approval.get('approved_binary_sha256') != hashes:
        return False
    tested = approval.get('owner_tested_current_build') is True and approval.get('no_problems_confirmed') is True
    waived = (approval.get('owner_explicitly_waived_current_build_test') is True
              and approval.get('exception_applies_to_build') == BUILD
              and approval.get('regression_review_passed') is True
              and approval.get('regression_condition') == 'No detected regression from published2.2 b2026101608; flight implementation preserved.'
              and bool(approval.get('latest_owner_authorization', '').strip()))
    return tested or waived
