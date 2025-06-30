#!/usr/bin/env python3
"""
Demo script for GPT Nutrition Evaluator
Run a quick evaluation with sample data
"""

import os
from nutrition_evaluator import NutritionEvaluator

def run_demo():
    """Run a demo evaluation."""
    
    # Check for API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Demo requires OPENAI_API_KEY environment variable")
        print("Set it with: export OPENAI_API_KEY='your-key-here'")
        return
    
    print("🍎 GPT Nutrition Knowledge Evaluator - Demo")
    print("=" * 50)
    
    # Initialize evaluator with GPT-3.5-turbo for faster/cheaper demo
    print("Initializing evaluator with gpt-3.5-turbo...")
    evaluator = NutritionEvaluator(api_key=api_key, model_name="gpt-3.5-turbo")
    
    print(f"Running {len(evaluator.evaluation_prompts)} evaluation prompts...")
    print("This will take about 1-2 minutes...\n")
    
    # Run evaluation
    results = evaluator.run_evaluation()
    
    # Show quick summary
    print("\n" + "=" * 50)
    print("📊 DEMO RESULTS SUMMARY")
    print("=" * 50)
    
    total_scores = [r.total_score for r in results]
    avg_score = sum(total_scores) / len(total_scores)
    
    print(f"Model: gpt-3.5-turbo")
    print(f"Total Prompts: {len(results)}")
    print(f"Average Score: {avg_score:.1f}%")
    print(f"Best Score: {max(total_scores):.1f}%")
    print(f"Worst Score: {min(total_scores):.1f}%")
    
    print("\nDetailed breakdown by category:")
    categories = {}
    for result in results:
        if result.category not in categories:
            categories[result.category] = []
        categories[result.category].append(result.total_score)
    
    for category, scores in categories.items():
        avg_cat = sum(scores) / len(scores)
        print(f"  {category}: {avg_cat:.1f}%")
    
    # Generate full report
    report = evaluator.generate_report()
    
    with open("demo_nutrition_report.md", "w") as f:
        f.write(report)
    
    print(f"\n📄 Full report saved to: demo_nutrition_report.md")
    print("\n✅ Demo completed!")

if __name__ == "__main__":
    run_demo() 