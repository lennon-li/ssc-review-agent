import unittest
import os
from agent.loaders import load_text, load_yaml, load_markdown

class TestLoaders(unittest.TestCase):
    def test_load_text(self):
        # Assumes existence of sample_01.txt for testing
        test_file = "applications_text/sample_01.txt"
        if os.path.exists(f"ssc-review-agent/{test_file}"):
            content = load_text(f"ssc-review-agent/{test_file}")
            self.assertIn("John Doe", content)

    def test_load_yaml(self):
        test_file = "criteria/rubric.yml"
        if os.path.exists(f"ssc-review-agent/{test_file}"):
            content = load_yaml(f"ssc-review-agent/{test_file}")
            self.assertIn("criteria", content)
            self.assertEqual(len(content["criteria"]), 4)

if __name__ == "__main__":
    unittest.main()
