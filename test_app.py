import unittest
from app import classify, select_records, format_guidance, classify_intent, four_g_information, trio_packages

class KnowledgeGuidanceTests(unittest.TestCase):
    def test_4g_intent_variants(self):
        for term in ('4G', '4 g', 'four g', 'LTE', '4G postpaid plans'):
            self.assertEqual(classify_intent(term)[0], '4g')

    def test_prepaid_postpaid_packages(self):
        from app import four_g_packages
        payload = {'collections': {'four_g': {
            'prepaid': [{'name':'Test prepaid', 'priceLkr': 100, 'quotaGb': 5, 'validityDays': 7}],
            'postpaid': [{'name':'Test postpaid', 'monthlyRentalLkr': 750, 'quotaGb': 30}]
        }}}
        plans = four_g_packages(payload)
        self.assertEqual(len(plans), 2)
        self.assertEqual({p['type'] for p in plans},{'prepaid','postpaid'})
        self.assertEqual(plans[0]['price_lkr'],100)

    def test_trio_is_not_4g_package(self):
        from app import four_g_packages
        self.assertEqual(four_g_packages({'collections':{'trio':{'packages':[{'name':'Trio Shine','pricing':{'priceWithTaxLkr':6372.47}}]}}}),[])

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

    def test_4g_search_is_not_generic(self):
        self.assertEqual(classify_intent("4G")[0], "4g")

    def test_4g_recharge_rules_are_structured(self):
        data = {"success": True, "telemetry": {"databaseName": "TEST"}, "collections": {"rules": [
            {"rule_code": "RULE_4G_RELOAD_DIRECT_CHANNELS", "rule_name": "4G recharge",
             "action_type": "DIRECT_TT", "target_group": "BSS-OPR-OCR",
             "advice_instructions": "Verify reload transaction."},
            {"rule_code": "RULE_LOS_RED", "rule_name": "Fiber LOS"}]}}
        result = four_g_information(data)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["target_group"], "BSS-OPR-OCR")

    def test_trio_prices_use_only_source_values(self):
        data = {"collections": {"trio": {"packages": [{
            "name": "Trio Shine", "pricing": {"priceWithTaxLkr": 6372.47}
        }]}}}
        self.assertEqual(trio_packages(data)[0]["total_price_lkr"], 6372.47)

if __name__ == "__main__":
    unittest.main()
