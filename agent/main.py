import argparse
import json
import os
import time
from .loaders import load_text, load_yaml, load_markdown
from .evaluate import get_evaluator
from .config import logger

def main():
    parser = argparse.ArgumentParser(description="SSC Review Agent - Local Evaluation")
    parser.add_argument("--input", required=True, help="Path to the input application text file.")
    parser.add_argument("--rubric", required=True, help="Path to the evaluation rubric (YAML).")
    parser.add_argument("--instructions", required=True, help="Path to the reviewer instructions (Markdown).")
    parser.add_argument("--output", required=True, help="Path to save the output evaluation (JSON).")
    parser.add_argument("--evaluator", default="mock", help="Evaluator type to use (default: mock).")

    args = parser.parse_args()

    # Step 1: Initialization
    logger.info("Initializing evaluation process.")
    print("--- [1/4] Loading configuration and inputs ---")
    
    try:
        app_text = load_text(args.input)
        rubric_data = load_yaml(args.rubric)
        instructions_text = load_markdown(args.instructions)
        logger.info(f"Loaded inputs from: {args.input}, {args.rubric}, {args.instructions}")
    except Exception as e:
        logger.error(f"Error loading files: {e}")
        print(f"FAILED: {e}")
        return

    # Step 2: Set up Evaluator
    print("--- [2/4] Setting up evaluator ---")
    try:
        evaluator = get_evaluator(args.evaluator)
        logger.info(f"Using evaluator type: {args.evaluator}")
    except Exception as e:
        logger.error(f"Error initializing evaluator: {e}")
        print(f"FAILED: {e}")
        return

    # Step 3: Run Evaluation
    print(f"--- [3/4] Evaluating applicant from {os.path.basename(args.input)} ---")
    # Simulate some progress for CLI feedback
    for i in range(1, 4):
        time.sleep(0.3)
        print(f"    Running analysis stage {i}...")
    
    start_time = time.time()
    result = evaluator.evaluate(app_text, rubric_data, instructions_text)
    end_time = time.time()
    
    logger.info(f"Evaluation completed in {end_time - start_time:.2f} seconds.")

    # Step 4: Export Result
    print(f"--- [4/4] Exporting assessment ---")
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2)

    logger.info(f"Result saved to {args.output}")
    print(f"SUCCESS: Evaluation complete. Result saved to: {args.output}")

if __name__ == "__main__":
    main()
