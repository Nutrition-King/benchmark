#!/usr/bin/env python3
"""
GPT Nutrition Knowledge Evaluator
"""

import json
import time
import statistics
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

try:
    from openai import OpenAI
except ImportError:
    print("OpenAI package not found. Install with: pip install openai")
    exit(1)

@dataclass
class EvaluationResult:
    """Data class to store evaluation results for each prompt."""
    prompt_id: str
    category: str
    difficulty: str
    prompt_text: str
    gpt_response: str
    expected_answer: str
    accuracy_score: float
    reasoning_score: float
    completeness_score: float
    practical_score: float
    total_score: float
    execution_time: float

class NutritionEvaluator:
    """Main class for evaluating GPT models on nutrition knowledge tasks."""
    
    def __init__(self, api_key: str, model_name: str = "gpt-4"):
        self.client = OpenAI(api_key=api_key)
        self.model_name = model_name
        self.results: List[EvaluationResult] = []
        self.evaluation_prompts = self._initialize_prompts()
        
    def _initialize_prompts(self) -> List[Dict[str, Any]]:
        """Initialize evaluation prompts with nutrition data."""
        
        apple_data = {
            "nutrients": {
                "energy": 378,
                "fat": 0.1,
                "netCarbs": 19.8,
                "protein": 1.7,
                "sugar": 16.9,
                "fiber": 2.7,
                "calcium": 5,
                "sodium": 1,
                "satFat": 0,
                "transFat": 0,
                "cholesterol": 0,
                "potassium": 342,
                "iron": 0.5,
                "vitaminC": 12
            }
        }
        
        return [
            {
                "id": "1A",
                "category": "Factual Accuracy",
                "difficulty": "Basic",
                "prompt": f"""Given the following nutrition data:

{json.dumps(apple_data, indent=2)}

Question: What is the total fat content and total carbohydrate content of this food item?
Show your calculation for carbohydrates.""",
                "expected_answer": "Total fat = 0.1g, Total carbohydrates = 22.5g (netCarbs + fiber = 19.8 + 2.7)"
            },
            
            {
                "id": "2A",
                "category": "Mathematical Computation",
                "difficulty": "Intermediate", 
                "prompt": f"""Food Item:
{json.dumps(apple_data, indent=2)}

Calculate total calories using the 4-4-9-7 rule:
- Carbohydrates: 4 calories per gram
- Protein: 4 calories per gram
- Fat: 9 calories per gram
- Alcohol: 7 calories per gram

Show your calculation and compare to the energy value given.""",
                "expected_answer": "Carbs: (19.8 + 2.7) × 4 = 90 cal, Protein: 1.7 × 4 = 6.8 cal, Fat: 0.1 × 9 = 0.9 cal, Total: ~97.7 cal"
            },
            
            {
                "id": "3A",
                "category": "Health Recommendations",
                "difficulty": "Advanced",
                "prompt": """Food Item:
{
  "nutrients": {
    "energy": 285,
    "fat": 12.0,
    "satFat": 8.0,
    "transFat": 0.5,
    "cholesterol": 45,
    "sodium": 650,
    "sugar": 18.0,
    "protein": 6.0
  }
}

Evaluate this food's suitability for someone with:
1) Type 2 diabetes
2) High blood pressure
3) High cholesterol

Provide specific reasoning based on the nutritional values.""",
                "expected_answer": "1) Poor for diabetes (high sugar: 18g), 2) Poor for hypertension (high sodium: 650mg), 3) Poor for cholesterol (sat fat: 8g, trans fat: 0.5g)"
            },
            
            {
                "id": "4A",
                "category": "Error Detection",
                "difficulty": "Expert",
                "prompt": """Identify errors in this nutrition data:

{
  "nutrients": {
    "energy": 400,
    "fat": 45.0,
    "satFat": 50.0,
    "protein": 0.0,
    "sodium": -5,
    "vitaminC": 150
  }
}

What issues do you notice and why are they problematic?""",
                "expected_answer": "Errors: 1) Saturated fat (50g) > total fat (45g) - impossible, 2) Negative sodium (-5)"
            }
        ]
    
    def _query_gpt(self, prompt: str) -> Tuple[str, float]:
        """Query GPT model and return response with execution time."""
        start_time = time.time()
        
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "You are a nutrition expert. Provide detailed, accurate responses with clear reasoning."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=800
            )
            
            execution_time = time.time() - start_time
            return response.choices[0].message.content.strip(), execution_time
            
        except Exception as e:
            print(f"Error querying GPT: {e}")
            return f"Error: {str(e)}", time.time() - start_time
    
    def _score_response(self, prompt_data: Dict[str, Any], gpt_response: str) -> Dict[str, float]:
        """Score a GPT response based on evaluation criteria."""
        response_lower = gpt_response.lower()
        
        # Simple keyword-based scoring
        accuracy_score = 0.0
        reasoning_score = 0.0
        completeness_score = 0.0
        practical_score = 0.0
        
        # Check for numerical accuracy
        if any(num in response_lower for num in ["0.1", "22.5", "19.8", "2.7"]):
            accuracy_score += 25
        if any(calc in response_lower for calc in ["×", "*", "=", "calculate"]):
            accuracy_score += 25
        
        # Check for reasoning
        if any(word in response_lower for word in ["because", "due to", "since", "therefore"]):
            reasoning_score += 30
        if any(word in response_lower for word in ["explain", "reason", "shows"]):
            reasoning_score += 20
        
        # Check completeness
        if len(response_lower.split()) > 20:
            completeness_score += 20
        if any(unit in response_lower for unit in ["gram", "mg", "calorie", "%"]):
            completeness_score += 20
        
        # Check practical application
        if any(term in response_lower for term in ["health", "diet", "nutrition", "recommend"]):
            practical_score += 15
        
        # Cap scores at 100
        accuracy_score = min(accuracy_score, 100)
        reasoning_score = min(reasoning_score, 100)
        completeness_score = min(completeness_score, 100)
        practical_score = min(practical_score, 100)
        
        # Calculate weighted total
        total_score = (
            accuracy_score * 0.4 + 
            reasoning_score * 0.3 + 
            completeness_score * 0.2 + 
            practical_score * 0.1
        )
        
        return {
            "accuracy": accuracy_score,
            "reasoning": reasoning_score,
            "completeness": completeness_score,
            "practical": practical_score,
            "total": total_score
        }
    
    def run_evaluation(self) -> List[EvaluationResult]:
        """Run the full evaluation suite."""
        print(f"Starting evaluation of {self.model_name}")
        
        for i, prompt_data in enumerate(self.evaluation_prompts, 1):
            print(f"Running prompt {i}/{len(self.evaluation_prompts)}: {prompt_data['id']}")
            
            # Query GPT
            gpt_response, execution_time = self._query_gpt(prompt_data["prompt"])
            
            # Score the response
            scores = self._score_response(prompt_data, gpt_response)
            
            # Create result
            result = EvaluationResult(
                prompt_id=prompt_data["id"],
                category=prompt_data["category"],
                difficulty=prompt_data["difficulty"],
                prompt_text=prompt_data["prompt"],
                gpt_response=gpt_response,
                expected_answer=prompt_data["expected_answer"],
                accuracy_score=scores["accuracy"],
                reasoning_score=scores["reasoning"],
                completeness_score=scores["completeness"],
                practical_score=scores["practical"],
                total_score=scores["total"],
                execution_time=execution_time
            )
            
            self.results.append(result)
            time.sleep(1)  # Rate limiting
        
        print("Evaluation completed")
        return self.results
    
    def generate_report(self) -> str:
        """Generate evaluation report."""
        if not self.results:
            return "No results available"
        
        total_scores = [r.total_score for r in self.results]
        avg_total = statistics.mean(total_scores)
        
        report = f"""
# GPT Nutrition Evaluation Report

**Model:** {self.model_name}
**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Total Prompts:** {len(self.results)}

## Summary
- Overall Average: {avg_total:.1f}%
- Best Performance: {max(total_scores):.1f}%
- Worst Performance: {min(total_scores):.1f}%

## Detailed Results

"""
        
        for result in self.results:
            report += f"### {result.prompt_id}: {result.category}\n"
            report += f"Score: {result.total_score:.1f}%\n"
            report += f"Time: {result.execution_time:.2f}s\n\n"
            report += f"**Expected:** {result.expected_answer}\n\n"
            report += f"**Response:** {result.gpt_response[:200]}...\n\n"
            report += "---\n\n"
        
        return report

def main():
    """Main function to run evaluation."""
    import os
    
    # Get API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        api_key = input("Enter OpenAI API key: ").strip()
    
    model_name = input("Enter model name (default: gpt-4): ").strip() or "gpt-4"
    
    # Run evaluation
    evaluator = NutritionEvaluator(api_key=api_key, model_name=model_name)
    
    print(f"\nEvaluating {model_name}...")
    results = evaluator.run_evaluation()
    
    # Generate report
    report = evaluator.generate_report()
    
    # Save report
    with open("nutrition_evaluation_report.md", "w") as f:
        f.write(report)
    
    # Show summary
    total_scores = [r.total_score for r in results]
    print(f"\nEvaluation Complete!")
    print(f"Average Score: {statistics.mean(total_scores):.1f}%")
    print(f"Report saved to: nutrition_evaluation_report.md")

if __name__ == "__main__":
    main() 