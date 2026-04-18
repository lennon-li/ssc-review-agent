import unittest
from agent.evaluate import mock_evaluate

class TestEvaluate(unittest.TestCase):
    def test_mock_evaluate(self):
        app_text = "Sample Applicant Text"
        rubric = {
            "criteria": [
                {"id": "crit1", "name": "Criterion 1"},
                {"id": "crit2", "name": "Criterion 2"}
            ]
        }
        instructions = "Sample Instructions"
        result = mock_evaluate(app_text, rubric, instructions)

        self.assertEqual(result["applicant_id"], "applicant_001")
        self.assertEqual(len(result["criteria"]), 2)
        self.assertEqual(result["criteria"][0]["criterion_id"], "crit1")
        
        # New reliability fields
        self.assertIn("ready_for_human_review", result)
        self.assertTrue(isinstance(result["ready_for_human_review"], bool))
        self.assertIn("needs_human_attention", result["criteria"][0])
        self.assertTrue(isinstance(result["criteria"][0]["needs_human_attention"], bool))

if __name__ == "__main__":
    unittest.main()
