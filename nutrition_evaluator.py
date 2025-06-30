#!/usr/bin/env python3
"""
GPT Nutrition Knowledge Evaluator
"""

import json
import time
import statistics
import csv
import os
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
    
    def __init__(self, api_key: str, model_name: str = "gpt-4o-mini"):
        self.client = OpenAI(api_key=api_key)
        self.model_name = model_name
        self.results: List[EvaluationResult] = []
        self.evaluation_prompts = self._initialize_prompts()
        
    def _load_nutrition_data(self) -> List[Dict[str, Any]]:
        """Load nutrition data from CSV file."""
        csv_path = "data/calorie_king_data.csv"
        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"Nutrition data file not found: {csv_path}")
        
        nutrition_data = []
        with open(csv_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                # Convert to nutrition format, handling empty values
                nutrients = {}
                for key, value in row.items():
                    if key in ['name', 'brand_name', 'classification']:
                        continue
                    # Handle empty values
                    if value == '' or value is None:
                        nutrients[key] = 0.0
                    else:
                        try:
                            nutrients[key] = float(value)
                        except ValueError:
                            nutrients[key] = 0.0
                
                food_item = {
                    "name": row['name'],
                    "brand": row['brand_name'],
                    "category": row['classification'],
                    "nutrients": nutrients
                }
                nutrition_data.append(food_item)
        
        return nutrition_data
    
    def _initialize_prompts(self) -> List[Dict[str, Any]]:
        """Initialize evaluation prompts with nutrition data from CSV."""
        
        # Load nutrition data from CSV
        foods = self._load_nutrition_data()
        
        # Select specific foods for different prompt types
        banana_data = next((food for food in foods if "Banana" in food["name"]), foods[0])
        steak_data = next((food for food in foods if "Rump Steak" in food["name"]), foods[4])
        processed_data = next((food for food in foods if "Cookie Dough" in food["name"]), foods[3])
        
        return [
            {
                "id": "1A",
                "category": "Factual Accuracy",
                "difficulty": "Basic",
                "prompt": f"""Given the following nutrition data for {banana_data['name']}:

{json.dumps(banana_data['nutrients'], indent=2)}

Question: What is the total fat content and total carbohydrate content of this food item?
Show your calculation for carbohydrates.

EXAMPLE of correct format:
{{
  "total_fat_g": 15.2,
  "total_carbohydrates_g": 45.8,
  "carb_calculation": {{
    "net_carbs": 42.1,
    "fiber": 3.7,
    "total": 45.8
  }}
}}

CRITICAL:
- Provide ONLY numerical values, NOT formulas
- Calculate: total_carbohydrates_g = net_carbs + fiber
- All values must be exact numbers from the data

Response format:
{{
  "total_fat_g": [NUMBER_FROM_DATA],
  "total_carbohydrates_g": [CALCULATED_NUMBER], 
  "carb_calculation": {{
    "net_carbs": [NUMBER_FROM_DATA],
    "fiber": [NUMBER_FROM_DATA],
    "total": [CALCULATED_NUMBER]
  }}
}}""",
                "expected_answer": {
                    "total_fat_g": banana_data['nutrients']['fat'],
                    "total_carbohydrates_g": banana_data['nutrients']['netCarbs'] + banana_data['nutrients']['fiber'],
                    "carb_calculation": {
                        "net_carbs": banana_data['nutrients']['netCarbs'],
                        "fiber": banana_data['nutrients']['fiber'],
                        "total": banana_data['nutrients']['netCarbs'] + banana_data['nutrients']['fiber']
                    }
                }
            },
            
            {
                "id": "2A",
                "category": "Mathematical Computation",
                "difficulty": "Intermediate", 
                "prompt": f"""Food Item: {banana_data['name']}
{json.dumps(banana_data['nutrients'], indent=2)}

Calculate total calories using the 4-4-9-7 rule:
- Carbohydrates: 4 calories per gram
- Protein: 4 calories per gram
- Fat: 9 calories per gram
- Alcohol: 7 calories per gram

Show your calculation and compare to the energy value given.

EXAMPLE of correct format:
{{
  "calculations": {{
    "carbohydrates_cal": 92.0,
    "protein_cal": 8.0,
    "fat_cal": 18.0,
    "alcohol_cal": 0.0
  }},
  "calculated_total_cal": 118.0,
  "given_energy_value": 500.0,
  "comparison": {{
    "match": false,
    "explanation": "Calculated 118 kcal vs given 500 kJ - unit difference"
  }}
}}

CRITICAL: 
- Provide ONLY calculated numerical values, NOT formulas
- All values must be numbers (e.g., 90.0), never expressions (e.g., 19.8 + 2.7)
- Calculate the math yourself before responding

Response format:
{{
  "calculations": {{
    "carbohydrates_cal": [CALCULATED_NUMBER],
    "protein_cal": [CALCULATED_NUMBER],
    "fat_cal": [CALCULATED_NUMBER],
    "alcohol_cal": [CALCULATED_NUMBER]
  }},
  "calculated_total_cal": [CALCULATED_NUMBER],
  "given_energy_value": [NUMBER_FROM_DATA],
  "comparison": {{
    "match": [true/false],
    "explanation": "[brief explanation]"
  }}
}}""",
                "expected_answer": {
                    "calculations": {
                        "carbohydrates_cal": (banana_data['nutrients']['netCarbs'] + banana_data['nutrients']['fiber']) * 4,
                        "protein_cal": banana_data['nutrients']['protein'] * 4,
                        "fat_cal": banana_data['nutrients']['fat'] * 9,
                        "alcohol_cal": banana_data['nutrients']['alcohol'] * 7
                    },
                    "calculated_total_cal": (banana_data['nutrients']['netCarbs'] + banana_data['nutrients']['fiber']) * 4 + banana_data['nutrients']['protein'] * 4 + banana_data['nutrients']['fat'] * 9 + banana_data['nutrients']['alcohol'] * 7,
                    "given_energy_value": banana_data['nutrients']['energy'],
                    "comparison": {
                        "match": False,
                        "explanation": "Energy likely in kJ not kcal"
                    }
                }
            },
            
            {
                "id": "3A",
                "category": "Health Recommendations",
                "difficulty": "Advanced",
                "prompt": f"""Food Item: {processed_data['name']}
{json.dumps(processed_data['nutrients'], indent=2)}

Evaluate this food's suitability for someone with:
1) Type 2 diabetes
2) High blood pressure
3) High cholesterol

EXAMPLE of correct format:
{{
  "evaluations": {{
    "type_2_diabetes": {{
      "suitability": "poor",
      "key_concerns": ["sugar", "carbs"],
      "specific_values": {{"sugar_g": 45.0, "carbs_g": 60.0}}
    }},
    "high_blood_pressure": {{
      "suitability": "fair", 
      "key_concerns": ["sodium"],
      "specific_values": {{"sodium_mg": 400.0}}
    }},
    "high_cholesterol": {{
      "suitability": "good",
      "key_concerns": [],
      "specific_values": {{"sat_fat_g": 2.0, "trans_fat_g": 0.0}}
    }}
  }}
}}

CRITICAL:
- suitability must be exactly "poor", "fair", or "good"
- Provide exact numbers from the nutrition data
- Use these guidelines: High sugar (>15g) = poor for diabetes, High sodium (>400mg) = poor for BP, High sat fat (>5g) = poor for cholesterol

Response format:
{{
  "evaluations": {{
    "type_2_diabetes": {{
      "suitability": "[poor/fair/good]",
      "key_concerns": ["[list_concerns]"],
      "specific_values": {{"sugar_g": [NUMBER], "carbs_g": [NUMBER]}}
    }},
    "high_blood_pressure": {{
      "suitability": "[poor/fair/good]", 
      "key_concerns": ["[list_concerns]"],
      "specific_values": {{"sodium_mg": [NUMBER]}}
    }},
    "high_cholesterol": {{
      "suitability": "[poor/fair/good]",
      "key_concerns": ["[list_concerns]"],
      "specific_values": {{"sat_fat_g": [NUMBER], "trans_fat_g": [NUMBER]}}
    }}
  }}
}}""",
                "expected_answer": {
                    "evaluations": {
                        "type_2_diabetes": {
                            "suitability": "poor",
                            "key_concerns": ["sugar", "carbs"],
                            "specific_values": {"sugar_g": processed_data['nutrients']['sugar'], "carbs_g": processed_data['nutrients']['netCarbs']}
                        },
                        "high_blood_pressure": {
                            "suitability": "poor",
                            "key_concerns": ["sodium"],
                            "specific_values": {"sodium_mg": processed_data['nutrients']['sodium']}
                        },
                        "high_cholesterol": {
                            "suitability": "poor", 
                            "key_concerns": ["satFat", "transFat"],
                            "specific_values": {"sat_fat_g": processed_data['nutrients']['satFat'], "trans_fat_g": processed_data['nutrients'].get('transFat', 0)}
                        }
                    }
                }
            },
            
            {
                "id": "4A",
                "category": "Error Detection",
                "difficulty": "Expert",
                "prompt": f"""Identify errors in this nutrition data for {steak_data['name']}:

{{
  "nutrients": {{
    "energy": {steak_data['nutrients']['energy']},
    "fat": {steak_data['nutrients']['fat']},
    "satFat": {steak_data['nutrients']['fat'] + 10.0},
    "protein": {steak_data['nutrients']['protein']},
    "sodium": -5,
    "cholesterol": {steak_data['nutrients']['cholesterol']}
  }}
}}

EXAMPLE of correct format:
{{
  "errors_found": [
    {{
      "field": "protein",
      "issue": "Protein value exceeds total weight",
      "why_problematic": "Nutritionally impossible - protein cannot be more than 100% of food"
    }},
    {{
      "field": "calcium", 
      "issue": "Negative calcium value (-10)",
      "why_problematic": "Nutrients cannot have negative values"
    }}
  ],
  "total_errors": 2
}}

CRITICAL:
- Look for: negative values, saturated fat > total fat, impossible ratios
- Count only clear nutritional impossibilities
- Provide exact field names and specific descriptions

Response format:
{{
  "errors_found": [
    {{
      "field": "[EXACT_FIELD_NAME]",
      "issue": "[SPECIFIC_DESCRIPTION]",
      "why_problematic": "[CLEAR_EXPLANATION]"
    }}
  ],
  "total_errors": [NUMBER_OF_ERRORS]
}}""",
                "expected_answer": {
                    "errors_found": [
                        {
                            "field": "satFat",
                            "issue": f"Saturated fat ({steak_data['nutrients']['fat'] + 10.0}g) > total fat ({steak_data['nutrients']['fat']}g)",
                            "why_problematic": "Saturated fat cannot exceed total fat - nutritionally impossible"
                        },
                        {
                            "field": "sodium",
                            "issue": "Negative sodium value (-5)",
                            "why_problematic": "Sodium content cannot be negative - invalid data"
                        }
                    ],
                    "total_errors": 2
                }
            }
        ]
    
    def _query_gpt(self, prompt: str) -> Tuple[str, float]:
        """Query GPT model and return response with execution time."""
        start_time = time.time()
        
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "You are a nutrition expert. CRITICAL: Respond ONLY with valid JSON. No text before or after JSON. Calculate all mathematical expressions to numerical values. Do not include formulas or expressions in JSON values."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.0,
                max_tokens=1000
            )
            
            execution_time = time.time() - start_time
            return response.choices[0].message.content.strip(), execution_time
            
        except Exception as e:
            print(f"Error querying GPT: {e}")
            return f"Error: {str(e)}", time.time() - start_time
    
    def _score_response(self, prompt_data: Dict[str, Any], gpt_response: str) -> Dict[str, float]:
        """Score a GPT response by comparing JSON output with expected JSON."""
        try:
            # Parse GPT response as JSON
            response_json = json.loads(gpt_response.strip())
            expected_json = prompt_data["expected_answer"]
            
            # Calculate accuracy based on JSON comparison
            accuracy_score = self._compare_json_accuracy(response_json, expected_json, prompt_data["id"])
            
            # For JSON responses, we focus purely on accuracy
            return {
                "accuracy": accuracy_score,
                "reasoning": accuracy_score,  # JSON structure shows reasoning
                "completeness": accuracy_score,  # JSON completeness is binary
                "practical": accuracy_score,  # Practical application shown by correct values
                "total": accuracy_score
            }
            
        except json.JSONDecodeError:
            # If response is not valid JSON, score as 0
            print(f"Warning: Invalid JSON response for prompt {prompt_data['id']}")
            return {
                "accuracy": 0.0,
                "reasoning": 0.0,
                "completeness": 0.0,
                "practical": 0.0,
                "total": 0.0
            }
    
    def _compare_json_accuracy(self, response: Dict, expected: Dict, prompt_id: str) -> float:
        """Compare JSON response with expected JSON and return accuracy percentage."""
        if prompt_id == "1A":
            return self._score_factual_accuracy(response, expected)
        elif prompt_id == "2A":
            return self._score_mathematical_computation(response, expected)
        elif prompt_id == "3A":
            return self._score_health_recommendations(response, expected)
        elif prompt_id == "4A":
            return self._score_error_detection(response, expected)
        else:
            return 0.0
    
    def _score_factual_accuracy(self, response: Dict, expected: Dict) -> float:
        """Score factual accuracy prompt (1A)."""
        score = 0.0
        total_points = 3
        
        # Check total fat (1 point) - allow small floating point differences
        if abs(response.get("total_fat_g", 0) - expected["total_fat_g"]) < 0.01:
            score += 1
        
        # Check total carbohydrates (1 point)
        if abs(response.get("total_carbohydrates_g", 0) - expected["total_carbohydrates_g"]) < 0.01:
            score += 1
        
        # Check calculation structure (1 point)
        calc = response.get("carb_calculation", {})
        exp_calc = expected["carb_calculation"]
        if (abs(calc.get("net_carbs", 0) - exp_calc["net_carbs"]) < 0.01 and
            abs(calc.get("fiber", 0) - exp_calc["fiber"]) < 0.01 and
            abs(calc.get("total", 0) - exp_calc["total"]) < 0.01):
            score += 1
        
        return (score / total_points) * 100
    
    def _score_mathematical_computation(self, response: Dict, expected: Dict) -> float:
        """Score mathematical computation prompt (2A)."""
        score = 0.0
        total_points = 4
        
        # Check individual calculations (3 points)
        calcs = response.get("calculations", {})
        exp_calcs = expected["calculations"]
        
        if abs(calcs.get("carbohydrates_cal", 0) - exp_calcs["carbohydrates_cal"]) < 0.1:
            score += 1
        if abs(calcs.get("protein_cal", 0) - exp_calcs["protein_cal"]) < 0.1:
            score += 1
        if abs(calcs.get("fat_cal", 0) - exp_calcs["fat_cal"]) < 0.1:
            score += 1
        
        # Check total calculation (1 point)
        if abs(response.get("calculated_total_cal", 0) - expected["calculated_total_cal"]) < 0.1:
            score += 1
        
        return (score / total_points) * 100
    
    def _score_health_recommendations(self, response: Dict, expected: Dict) -> float:
        """Score health recommendations prompt (3A)."""
        score = 0.0
        total_points = 3
        
        evals = response.get("evaluations", {})
        exp_evals = expected["evaluations"]
        
        # Check each health condition evaluation
        for condition in ["type_2_diabetes", "high_blood_pressure", "high_cholesterol"]:
            if (evals.get(condition, {}).get("suitability") == 
                exp_evals[condition]["suitability"]):
                score += 1
        
        return (score / total_points) * 100
    
    def _score_error_detection(self, response: Dict, expected: Dict) -> float:
        """Score error detection prompt (4A)."""
        score = 0.0
        total_points = 3
        
        # Check if correct number of errors found
        if response.get("total_errors") == expected["total_errors"]:
            score += 1
        
        # Check if major errors are identified
        errors_found = response.get("errors_found", [])
        expected_fields = {error["field"] for error in expected["errors_found"]}
        found_fields = {error.get("field") for error in errors_found}
        
        # Award points for finding each critical error
        if "satFat" in found_fields:
            score += 1
        if "sodium" in found_fields:
            score += 1
        
        return (score / total_points) * 100
    
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
            
            # Format expected answer as JSON if it's a dict
            if isinstance(result.expected_answer, dict):
                report += f"**Expected JSON:**\n```json\n{json.dumps(result.expected_answer, indent=2)}\n```\n\n"
            else:
                report += f"**Expected:** {result.expected_answer}\n\n"
            
            report += f"**GPT Response:**\n```json\n{result.gpt_response}\n```\n\n"
            report += "---\n\n"
        
        return report

def main():
    """Main function to run evaluation."""
    import os
    
    # Get API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        api_key = input("Enter OpenAI API key: ").strip()
    
    model_name = input("Enter model name (default: gpt-4o-mini): ").strip() or "gpt-4o-mini"
    
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