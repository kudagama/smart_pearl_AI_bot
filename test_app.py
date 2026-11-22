import unittest
from app import classify, select_records, format_guidance

class KnowledgeGuidanceTests(unittest.TestCase):
    def test_los_is_detected(self):
        self.assertEqual(classify("My LOS light is red")[0], "fiber_los")

    def test_unrelated_fiber_rule_is_not_los_guidance(self):
        self.assertEqual(select_records({"rules": [{"title": "Fiber speed complaint"}]}, "fiber_los"), [])

    def test_guidance_preserves_source_values(self):
        record = {"ruleName": "LOS Red", "troubleshootingSteps": ["Check cable"], "ttRouting": "Optical team"}
        result = format_guidance(record)
        self.assertEqual(result["steps"], ["Check cable"])
        self.assertEqual(result["routing"], ["Optical team"])

    def test_missing_sections_are_empty_not_invented(self):
        result = format_guidance({"title": "LOS signal issue"})
        self.assertEqual(result["questions"], [])
        self.assertEqual(result["routing"], [])

if __name__ == "__main__":
    unittest.main()
