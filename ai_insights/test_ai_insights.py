from django.test import TestCase
from ai_insights.utils import get_insights
from pprint import pprint

class AIInsightsTestCase(TestCase):
    def test_get_insights(self):
        goal = "become a graphic designer"
        try:
            insights = get_insights(goal)
            pprint(insights)  # Pretty-print the insights
            print(insights) 
        except Exception as e:
            self.fail(f"Error: {e}")