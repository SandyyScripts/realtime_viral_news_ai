"""
Test script for viral scoring logic
Tests the viral scoring algorithm without making API calls
"""

import sys
sys.path.insert(0, '/home/user/realtime_viral_news_ai')

from app.services.viral_search_service import _calculate_viral_score, _deduplicate_by_title

def test_viral_scoring():
    """Test the viral scoring algorithm with different news items"""

    print("="*70)
    print("🧪 TESTING VIRAL SCORING ALGORITHM")
    print("="*70)

    test_cases = [
        {
            "name": "High Viral - Virat Kohli Controversy",
            "item": {
                "title": "Shock: Virat Kohli dropped from T20 squad—BCCI's ₹15cr dilemma trending on Twitter",
                "description": "BCCI faces backlash after dropping Virat from T20 squad",
                "viral_reason": "Trending #1 on Twitter India, massive outrage from fans"
            },
            "expected_range": (85, 100)
        },
        {
            "name": "Medium Viral - RBI Rate Hike",
            "item": {
                "title": "RBI hikes interest rates 0.25%—₹50L home loan EMI up ₹2,400/month",
                "description": "Reserve Bank increases repo rate affecting millions",
                "viral_reason": "Reddit discussions about impact on middle class"
            },
            "expected_range": (70, 90)
        },
        {
            "name": "Low Viral - Boring Government Meeting",
            "item": {
                "title": "Finance Minister announces new committee meeting for banking regulations",
                "description": "Government officials to meet next week to discuss policy",
                "viral_reason": ""
            },
            "expected_range": (0, 50)
        },
        {
            "name": "High Viral - Bollywood Scandal",
            "item": {
                "title": "Shocking: Shah Rukh Khan and Salman Khan viral fight at awards show",
                "description": "Bollywood's biggest stars involved in controversy",
                "viral_reason": "Viral video trending on social media"
            },
            "expected_range": (80, 100)
        },
        {
            "name": "Medium Viral - Stock Market Crash",
            "item": {
                "title": "Sensex crashes 1,000 points—investors lose ₹5 lakh crore in single day",
                "description": "Markets tumble amid global uncertainty",
                "viral_reason": "Panic selling, trending on financial forums"
            },
            "expected_range": (75, 95)
        }
    ]

    print("\nTest Results:\n")

    passed = 0
    failed = 0

    for idx, test in enumerate(test_cases, 1):
        score = _calculate_viral_score(test["item"])
        min_expected, max_expected = test["expected_range"]

        status = "✅ PASS" if min_expected <= score <= max_expected else "❌ FAIL"

        if min_expected <= score <= max_expected:
            passed += 1
        else:
            failed += 1

        print(f"{idx}. {test['name']}")
        print(f"   Score: {score}/100 (expected {min_expected}-{max_expected})")
        print(f"   Title: {test['item']['title'][:70]}...")
        print(f"   Status: {status}")
        print()

    print("="*70)
    print(f"Results: {passed} passed, {failed} failed")
    print("="*70)

    return failed == 0


def test_deduplication():
    """Test deduplication logic"""

    print("\n" + "="*70)
    print("🧪 TESTING DEDUPLICATION")
    print("="*70)

    items = [
        {"title": "Virat Kohli dropped from T20 squad after poor performance", "viral_score": 90},
        {"title": "BCCI drops Virat Kohli from T20 team citing form issues", "viral_score": 85},  # Duplicate
        {"title": "RBI hikes interest rates affecting home loans", "viral_score": 75},
        {"title": "Shah Rukh Khan new movie breaks box office records", "viral_score": 80},
        {"title": "Interest rate hike by RBI impacts borrowers nationwide", "viral_score": 70},  # Duplicate
    ]

    unique = _deduplicate_by_title(items)

    print(f"\nOriginal items: {len(items)}")
    print(f"After deduplication: {len(unique)}")
    print(f"\nUnique items:")

    for idx, item in enumerate(unique, 1):
        print(f"{idx}. [{item['viral_score']}] {item['title']}")

    expected_unique = 3  # Should keep Virat, RBI, Shah Rukh (remove duplicates)

    print(f"\n{'✅ PASS' if len(unique) == expected_unique else '❌ FAIL'}")
    print(f"Expected {expected_unique} unique items, got {len(unique)}")

    return len(unique) == expected_unique


def main():
    """Run all tests"""

    print("\n" + "🚀 VIRAL NEWS SYSTEM - UNIT TESTS" + "\n")

    test1_passed = test_viral_scoring()
    test2_passed = test_deduplication()

    print("\n" + "="*70)
    print("📊 FINAL RESULTS")
    print("="*70)
    print(f"Viral Scoring Test: {'✅ PASSED' if test1_passed else '❌ FAILED'}")
    print(f"Deduplication Test: {'✅ PASSED' if test2_passed else '❌ FAILED'}")

    if test1_passed and test2_passed:
        print("\n🎉 All tests passed! System is ready.")
        return 0
    else:
        print("\n⚠️ Some tests failed. Review implementation.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
