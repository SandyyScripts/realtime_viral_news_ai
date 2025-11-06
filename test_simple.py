"""
Simple test to validate viral scoring logic without dependencies
"""

import re

def calculate_viral_score(item: dict) -> int:
    """Calculate viral potential score (0-100)"""
    score = 50  # Base score

    title = (item.get('title', '') + ' ' + item.get('description', '')).lower()
    viral_reason = item.get('viral_reason', '').lower()

    # Controversy indicators (+20)
    controversy_words = ['shocking', 'controversial', 'scandal', 'outrage', 'viral', 'trending',
                         'angry', 'protest', 'backlash', 'slammed', 'criticized', 'drama']
    if any(word in title or word in viral_reason for word in controversy_words):
        score += 20

    # Emotion triggers (+15)
    emotion_words = ['shock', 'anger', 'fury', 'rage', 'amazing', 'incredible', 'stunning',
                     'unbelievable', 'insane', 'wild', 'crazy']
    if any(word in title for word in emotion_words):
        score += 15

    # Numbers/data points (+10)
    if re.search(r'₹|crore|lakh|\d+%|\d+cr|\d+L', title):
        score += 10

    # Social proof (+15)
    social_words = ['twitter', 'reddit', 'viral', 'trending', 'social media', 'reactions', 'netizens']
    if any(word in title or word in viral_reason for word in social_words):
        score += 15

    # Celebrity/Cricket/Politics (+10)
    high_engagement = ['virat', 'dhoni', 'rohit', 'modi', 'rahul gandhi', 'shah rukh',
                       'salman', 'rbi', 'bcci', 'ipl', 'bollywood']
    if any(name in title for name in high_engagement):
        score += 10

    # Negative for boring words (-20)
    boring_words = ['meeting', 'conference', 'statement', 'announces', 'inaugurates']
    if any(word in title for word in boring_words):
        score -= 20

    # Has viral reason (+10)
    if item.get('viral_reason') and len(item['viral_reason']) > 10:
        score += 10

    return max(0, min(100, score))


def main():
    print("\n" + "="*70)
    print("🧪 TESTING VIRAL SCORING ALGORITHM")
    print("="*70)

    tests = [
        {
            "name": "HIGH VIRAL - Virat Kohli Controversy",
            "item": {
                "title": "Shock: Virat Kohli dropped from T20 squad—BCCI's ₹15cr dilemma trending on Twitter",
                "description": "Massive outrage",
                "viral_reason": "Trending #1 on Twitter"
            },
            "expected_min": 85
        },
        {
            "name": "MEDIUM VIRAL - RBI Rate Hike",
            "item": {
                "title": "RBI hikes rates 0.25%—₹50L home loan EMI up ₹2,400/month",
                "description": "Impacts millions",
                "viral_reason": "Reddit discussions"
            },
            "expected_min": 70
        },
        {
            "name": "LOW VIRAL - Boring Meeting",
            "item": {
                "title": "Finance Minister announces committee meeting for regulations",
                "description": "Officials to meet",
                "viral_reason": ""
            },
            "expected_max": 50
        }
    ]

    print("\nTest Results:\n")
    passed = 0
    total = len(tests)

    for idx, test in enumerate(tests, 1):
        score = calculate_viral_score(test["item"])

        if "expected_min" in test:
            success = score >= test["expected_min"]
            expected = f">= {test['expected_min']}"
        else:
            success = score <= test["expected_max"]
            expected = f"<= {test['expected_max']}"

        status = "✅ PASS" if success else "❌ FAIL"
        if success:
            passed += 1

        print(f"{idx}. {test['name']}")
        print(f"   Score: {score}/100 (expected {expected})")
        print(f"   Title: {test['item']['title'][:65]}...")
        print(f"   {status}\n")

    print("="*70)
    print(f"Results: {passed}/{total} tests passed")
    print("="*70)

    if passed == total:
        print("\n🎉 All tests passed! Viral scoring logic is working correctly.\n")
        return 0
    else:
        print(f"\n⚠️ {total - passed} test(s) failed.\n")
        return 1


if __name__ == "__main__":
    exit(main())
