"""Authorize only this conditional bug-fix release, tied to exact verified binaries."""
VERSION, BUILD = '2.3', 2026101901
REGRESSION_CONDITION = 'Only the reproduced S repress edge is corrected from published2.3 b2026101701; feature regression and settings preservation pass.'


def release_authorized(approval, hashes):
    if approval.get('version') != VERSION or approval.get('build') != BUILD:
        return False
    if approval.get('release_approved') is not True or approval.get('approved_binary_sha256') != hashes:
        return False
    tested = approval.get('owner_tested_current_build') is True and approval.get('no_problems_confirmed') is True
    conditional = (approval.get('owner_authorized_conditional_bugfix_release') is True
                   and approval.get('authorization_mode') == 'conditional_fix_and_reupload'
                   and approval.get('exception_applies_to_build') == BUILD
                   and approval.get('reproduced_input_edge_confirmed') is True
                   and approval.get('regression_review_passed') is True
                   and approval.get('regression_condition') == REGRESSION_CONDITION
                   and bool(approval.get('latest_owner_authorization', '').strip()))
    return tested or conditional
