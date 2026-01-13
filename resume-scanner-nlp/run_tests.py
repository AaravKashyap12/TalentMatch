from tests.test_matcher import test_calculate_ats_score_keyword_and_experience, test_calculate_ats_score_short_resume_penalty

failed = 0

try:
    test_calculate_ats_score_keyword_and_experience()
    print("test_calculate_ats_score_keyword_and_experience: PASSED")
except AssertionError as e:
    print("test_calculate_ats_score_keyword_and_experience: FAILED", e)
    failed += 1

try:
    test_calculate_ats_score_short_resume_penalty()
    print("test_calculate_ats_score_short_resume_penalty: PASSED")
except AssertionError as e:
    print("test_calculate_ats_score_short_resume_penalty: FAILED", e)
    failed += 1

if failed == 0:
    print("ALL TESTS PASSED")
else:
    print(f"{failed} TEST(s) FAILED")
    raise SystemExit(1)
