#!/usr/bin/env python3
"""
LLM Nutrition Knowledge Evaluator
Supports both OpenAI and IBM WatsonX AI APIs
"""

import json
import time
import statistics
import csv
import os
from typing import Dict, List, Any, Optional, Tuple, Literal
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import difflib

# OpenAI import (optional)
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

# IBM WatsonX import (optional)
try:
    from ibm_watsonx_ai.foundation_models import ModelInference
    from ibm_watsonx_ai import Credentials
    WATSONX_AVAILABLE = True
except ImportError:
    WATSONX_AVAILABLE = False

class APIProvider(Enum):
    """Enum for supported API providers."""
    OPENAI = "openai"
    WATSONX = "watsonx"

@dataclass
class EvaluationResult:
    """Data class to store evaluation results for each prompt."""
    prompt_id: str
    category: str
    difficulty: str
    prompt_text: str
    llm_response: str
    expected_answer: str
    accuracy_score: float
    reasoning_score: float
    completeness_score: float
    practical_score: float
    total_score: float
    execution_time: float

@dataclass
class APIConfig:
    """Configuration for different API providers."""
    provider: APIProvider
    # OpenAI config
    openai_api_key: Optional[str] = None
    # WatsonX config
    watsonx_api_key: Optional[str] = None
    watsonx_url: Optional[str] = None
    watsonx_project_id: Optional[str] = None

class NutritionEvaluator:
    """Main class for evaluating LLM models on nutrition knowledge tasks."""
    
    def __init__(self, api_config: APIConfig, model_name: str = None, verbose: bool = False):
        self.api_config = api_config
        self.model_name = model_name or self._get_default_model(api_config.provider)
        self.results: List[EvaluationResult] = []
        self.evaluation_prompts = self._initialize_prompts()
        self.verbose = verbose
        
        # Load nutrition data for meal lookups
        self.nutrition_data = self._load_nutrition_data()
        
        # Initialize the appropriate client
        if api_config.provider == APIProvider.OPENAI:
            if not OPENAI_AVAILABLE:
                raise ImportError("OpenAI package not found. Install with: pip install openai")
            if not api_config.openai_api_key:
                raise ValueError("OpenAI API key is required")
            self.client = OpenAI(api_key=api_config.openai_api_key)
        
        elif api_config.provider == APIProvider.WATSONX:
            if not WATSONX_AVAILABLE:
                raise ImportError("IBM WatsonX package not found. Install with: pip install ibm-watsonx-ai")
            if not all([api_config.watsonx_api_key, api_config.watsonx_url, api_config.watsonx_project_id]):
                raise ValueError("WatsonX API key, URL, and project ID are all required")
            
            credentials = Credentials(
                api_key=api_config.watsonx_api_key,
                url=api_config.watsonx_url
            )
            self.client = ModelInference(
                model_id=self.model_name,
                credentials=credentials,
                project_id=api_config.watsonx_project_id
            )
        
        else:
            raise ValueError(f"Unsupported API provider: {api_config.provider}")
    
    def _get_default_model(self, provider: APIProvider) -> str:
        """Get default model for the specified provider."""
        if provider == APIProvider.OPENAI:
            return "gpt-4o-mini"
        elif provider == APIProvider.WATSONX:
            return "ibm/granite-3-8b-instruct"  # Confirmed available model
        else:
            raise ValueError(f"No default model for provider: {provider}")
    
    def _load_nutrition_data(self) -> List[Dict[str, Any]]:
        """Load nutrition data from CSV file."""
        csv_path = "../data/calorie_king_data.csv"
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
    
    def _query_llm(self, prompt: str) -> Tuple[str, float]:
        """Query LLM model and return response with execution time."""
        start_time = time.time()
        
        if self.verbose:
            print(f"\n{'='*80}")
            print(f"🔄 API CALL TO {self.api_config.provider.value.upper()}")
            print(f"Model: {self.model_name}")
            print(f"{'='*80}")
            print(f"📤 PROMPT SENT:")
            print(f"{'-'*40}")
            print(prompt[:500] + "..." if len(prompt) > 500 else prompt)
            print(f"{'-'*40}")
        
        try:
            if self.api_config.provider == APIProvider.OPENAI:
                if self.verbose:
                    print(f"🔵 Making OpenAI API call...")
                    print(f"   API Key: {self.api_config.openai_api_key[:8]}...{self.api_config.openai_api_key[-4:]}")
                
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
                content = response.choices[0].message.content.strip()
                
                if self.verbose:
                    print(f"📥 OPENAI RESPONSE RECEIVED:")
                    print(f"   Response ID: {response.id}")
                    print(f"   Model Used: {response.model}")
                    print(f"   Tokens Used: {response.usage.total_tokens} (prompt: {response.usage.prompt_tokens}, completion: {response.usage.completion_tokens})")
                    print(f"   Execution Time: {execution_time:.2f}s")
                    print(f"{'-'*40}")
                    print(content)
                    print(f"{'-'*40}")
                
                return content, execution_time
            
            elif self.api_config.provider == APIProvider.WATSONX:
                if self.verbose:
                    print(f"🟢 Making WatsonX API call...")
                    print(f"   API Key: {self.api_config.watsonx_api_key[:8]}...{self.api_config.watsonx_api_key[-4:]}")
                    print(f"   URL: {self.api_config.watsonx_url}")
                    print(f"   Project ID: {self.api_config.watsonx_project_id}")
                
                # For WatsonX, use the chat method for conversational models
                messages = [
                    {"role": "system", "content": "You are a nutrition expert. CRITICAL: Respond ONLY with valid JSON. No text before or after JSON. Calculate all mathematical expressions to numerical values. Do not include formulas or expressions in JSON values."},
                    {"role": "user", "content": prompt}
                ]
                
                # Some WatsonX models may not support chat format, fallback to generate_text
                try:
                    if self.verbose:
                        print(f"   Trying chat method first...")
                    
                    response = self.client.chat(messages=messages)
                    content = response['choices'][0]['message']['content']
                    
                    if self.verbose:
                        print(f"📥 WATSONX CHAT RESPONSE RECEIVED:")
                        print(f"   Response structure: {list(response.keys())}")
                        if 'usage' in response:
                            print(f"   Token usage: {response.get('usage', 'N/A')}")
                        print(f"   Raw response type: {type(response)}")
                        
                except (KeyError, AttributeError, TypeError) as e:
                    if self.verbose:
                        print(f"   Chat method failed ({e}), falling back to generate_text...")
                    
                    # Fallback to generate_text for non-chat models
                    full_prompt = f"You are a nutrition expert. CRITICAL: Respond ONLY with valid JSON. No text before or after JSON. Calculate all mathematical expressions to numerical values. Do not include formulas or expressions in JSON values.\n\nUser: {prompt}\n\nAssistant:"
                    response = self.client.generate_text(prompt=full_prompt)
                    content = response
                    
                    if self.verbose:
                        print(f"📥 WATSONX GENERATE_TEXT RESPONSE RECEIVED:")
                        print(f"   Response type: {type(response)}")
                
                execution_time = time.time() - start_time
                
                if self.verbose:
                    print(f"   Execution Time: {execution_time:.2f}s")
                    print(f"{'-'*40}")
                    print(content)
                    print(f"{'-'*40}")
                
                return content.strip(), execution_time
            
            else:
                raise ValueError(f"Unsupported API provider: {self.api_config.provider}")
                
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            execution_time = time.time() - start_time
            
            if self.verbose:
                print(f"❌ API CALL FAILED:")
                print(f"   Error: {error_msg}")
                print(f"   Execution Time: {execution_time:.2f}s")
                print(f"{'='*80}")
            
            print(f"Error querying LLM: {e}")
            return error_msg, execution_time
    
    def _score_response(self, prompt_data: Dict[str, Any], llm_response: str) -> Dict[str, float]:
        """Score an LLM response by comparing JSON output with expected JSON."""
        try:
            # Parse LLM response as JSON
            response_json = json.loads(llm_response.strip())
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
            
            # Query LLM
            llm_response, execution_time = self._query_llm(prompt_data["prompt"])
            
            # Score the response
            scores = self._score_response(prompt_data, llm_response)
            
            # Create result
            result = EvaluationResult(
                prompt_id=prompt_data["id"],
                category=prompt_data["category"],
                difficulty=prompt_data["difficulty"],
                prompt_text=prompt_data["prompt"],
                llm_response=llm_response,
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
        
        provider_name = self.api_config.provider.value.upper()
        
        report = f"""
# {provider_name} Nutrition Evaluation Report

**Provider:** {provider_name}
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
            
            report += f"**LLM Response:**\n```json\n{result.llm_response}\n```\n\n"
            report += "---\n\n"
        
        return report

    def lookup_meal_carbs(self, meal_name: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """
        Look up carbohydrate information for a specific meal from the CalorieKing database.
        
        Args:
            meal_name (str): Name of the meal/food to search for (e.g., "hard boiled egg")
            max_results (int): Maximum number of results to return (default: 5)
            
        Returns:
            List[Dict]: List of matching foods with carbohydrate information, sorted by relevance
            
        Example:
            >>> evaluator = NutritionEvaluator(api_config)
            >>> results = evaluator.lookup_meal_carbs("hard boiled egg")
            >>> for food in results:
            ...     print(f"{food['name']}: {food['carb_info']['total_carbs_g']}g carbs")
        """
        if not hasattr(self, 'nutrition_data'):
            self.nutrition_data = self._load_nutrition_data()
        
        meal_name_lower = meal_name.lower()
        matches = []
        
        # Search through all food items
        for food in self.nutrition_data:
            food_name_lower = food['name'].lower()
            
            # Calculate similarity score using different methods
            scores = []
            
            # 1. Direct substring match (highest priority)
            if meal_name_lower in food_name_lower:
                scores.append(0.9)
            elif any(word in food_name_lower for word in meal_name_lower.split()):
                scores.append(0.7)
            
            # 2. Fuzzy string matching
            similarity = difflib.SequenceMatcher(None, meal_name_lower, food_name_lower).ratio()
            scores.append(similarity)
            
            # 3. Word-by-word matching
            meal_words = set(meal_name_lower.split())
            food_words = set(food_name_lower.split())
            word_overlap = len(meal_words.intersection(food_words)) / len(meal_words.union(food_words)) if meal_words.union(food_words) else 0
            scores.append(word_overlap)
            
            # Take the best score
            best_score = max(scores) if scores else 0
            
            # Only include if there's some relevance
            if best_score > 0.3:
                # Calculate carbohydrate information
                net_carbs = food['nutrients'].get('netCarbs', 0.0)
                fiber = food['nutrients'].get('fiber', 0.0)
                total_carbs = net_carbs + fiber if net_carbs and fiber else net_carbs
                sugar = food['nutrients'].get('sugar', 0.0)
                
                match_info = {
                    'name': food['name'],
                    'brand': food['brand'],
                    'category': food['category'],
                    'relevance_score': best_score,
                    'carb_info': {
                        'net_carbs_g': net_carbs,
                        'fiber_g': fiber,
                        'total_carbs_g': total_carbs,
                        'sugar_g': sugar
                    },
                    'other_nutrients': {
                        'energy_kj': food['nutrients'].get('energy', 0.0),
                        'protein_g': food['nutrients'].get('protein', 0.0),
                        'fat_g': food['nutrients'].get('fat', 0.0),
                        'sodium_mg': food['nutrients'].get('sodium', 0.0)
                    }
                }
                matches.append(match_info)
        
        # Sort by relevance score (highest first)
        matches.sort(key=lambda x: x['relevance_score'], reverse=True)
        
        # Return top results
        return matches[:max_results]
    
    def print_meal_carb_info(self, meal_name: str, max_results: int = 5) -> None:
        """
        Print formatted carbohydrate information for a meal search.
        
        Args:
            meal_name (str): Name of the meal/food to search for
            max_results (int): Maximum number of results to display
        """
        results = self.lookup_meal_carbs(meal_name, max_results)
        
        if not results:
            print(f"❌ No matches found for '{meal_name}'")
            print("Try a more general term or check the spelling.")
            return
        
        print(f"🔍 Carbohydrate information for '{meal_name}':")
        print("=" * 80)
        
        for i, food in enumerate(results, 1):
            carbs = food['carb_info']
            other = food['other_nutrients']
            
            print(f"\n{i}. {food['name']}")
            if food['brand'] and food['brand'] != "- Average All Brands -":
                print(f"   Brand: {food['brand']}")
            print(f"   Category: {food['category']}")
            print(f"   Relevance: {food['relevance_score']:.1%}")
            
            print(f"\n   📊 CARBOHYDRATE BREAKDOWN:")
            print(f"   • Total Carbohydrates: {carbs['total_carbs_g']:.1f}g")
            print(f"   • Net Carbs: {carbs['net_carbs_g']:.1f}g")
            print(f"   • Fiber: {carbs['fiber_g']:.1f}g") 
            print(f"   • Sugar: {carbs['sugar_g']:.1f}g")
            
            print(f"\n   🍽️  OTHER NUTRIENTS:")
            print(f"   • Energy: {other['energy_kj']:.0f} kJ")
            print(f"   • Protein: {other['protein_g']:.1f}g")
            print(f"   • Fat: {other['fat_g']:.1f}g")
            print(f"   • Sodium: {other['sodium_mg']:.0f}mg")
            
            if i < len(results):
                print("\n" + "-" * 40)
        
        print(f"\n✅ Found {len(results)} match(es) for '{meal_name}'")
    
    def enable_verbose_logging(self):
        """Enable verbose API logging to see actual API calls and responses."""
        self.verbose = True
        print("✅ Verbose logging enabled - API calls and responses will be shown")
    
    def disable_verbose_logging(self):
        """Disable verbose API logging."""
        self.verbose = False
        print("ℹ️ Verbose logging disabled")

def main():
    """Main function to run evaluation."""
    import os
    
    print("🍎 LLM Nutrition Knowledge Evaluator")
    print("=" * 50)
    
    # Ask for verbose mode
    verbose_choice = input("Enable verbose API logging? (y/N): ").strip().lower()
    verbose = verbose_choice in ['y', 'yes', 'true', '1']
    
    if verbose:
        print("✅ Verbose mode enabled - will show detailed API calls and responses")
    
    # Choose API provider
    print("\nChoose API provider:")
    print("1. OpenAI")
    print("2. IBM WatsonX")
    
    while True:
        choice = input("Enter choice (1 or 2): ").strip()
        if choice == "1":
            provider = APIProvider.OPENAI
            break
        elif choice == "2":
            provider = APIProvider.WATSONX
            break
        else:
            print("Invalid choice. Please enter 1 or 2.")
    
    # Configure API based on choice
    if provider == APIProvider.OPENAI:
        print("\n--- OpenAI Configuration ---")
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            api_key = input("Enter OpenAI API key: ").strip()
        
        # Show OpenAI model options
        print("\nSelect OpenAI model:")
        print("1. gpt-4o-mini (default - fast, cost-effective)")
        print("2. gpt-4o (balanced performance)")
        print("3. gpt-4 (highest quality)")
        print("4. gpt-3.5-turbo (budget option)")
        
        model_choice = input("Enter choice (1-4, default 1): ").strip()
        model_options = {
            "1": "gpt-4o-mini",
            "2": "gpt-4o", 
            "3": "gpt-4",
            "4": "gpt-3.5-turbo"
        }
        model_name = model_options.get(model_choice, "gpt-4o-mini")
        
        print(f"Selected model: {model_name}")
        
        api_config = APIConfig(
            provider=APIProvider.OPENAI,
            openai_api_key=api_key
        )
    
    elif provider == APIProvider.WATSONX:
        print("\n--- IBM WatsonX Configuration ---")
        
        # Try to get from environment variables first
        watsonx_api_key = os.getenv("WATSONX_API_KEY")
        watsonx_url = os.getenv("WATSONX_URL") 
        watsonx_project_id = os.getenv("WATSONX_PROJECT_ID")
        
        # Prompt for missing values
        if not watsonx_api_key:
            watsonx_api_key = input("Enter WatsonX API key: ").strip()
        if not watsonx_url:
            watsonx_url = input("Enter WatsonX URL (default: https://us-south.ml.cloud.ibm.com): ").strip() or "https://us-south.ml.cloud.ibm.com"
        if not watsonx_project_id:
            watsonx_project_id = input("Enter WatsonX Project ID: ").strip()
        
        # Show WatsonX model options
        print("\nSelect WatsonX model:")
        print("1. ibm/granite-3-8b-instruct (default - fast, cost-effective)")
        print("2. ibm/granite-13b-instruct-v2 (larger granite model)")
        print("3. meta-llama/llama-3-3-70b-instruct (high quality)")
        print("4. mistralai/mistral-large (alternative high quality)")
        
        model_choice = input("Enter choice (1-4, default 1): ").strip()
        model_options = {
            "1": "ibm/granite-3-8b-instruct",
            "2": "ibm/granite-13b-instruct-v2",
            "3": "meta-llama/llama-3-3-70b-instruct", 
            "4": "mistralai/mistral-large"
        }
        model_name = model_options.get(model_choice, "ibm/granite-3-8b-instruct")
        
        print(f"Selected model: {model_name}")
        
        api_config = APIConfig(
            provider=APIProvider.WATSONX,
            watsonx_api_key=watsonx_api_key,
            watsonx_url=watsonx_url,
            watsonx_project_id=watsonx_project_id
        )
    
    # Initialize evaluator
    try:
        evaluator = NutritionEvaluator(api_config=api_config, model_name=model_name, verbose=verbose)
    except Exception as e:
        print(f"Error initializing evaluator: {e}")
        return
    
    print(f"\nEvaluating {evaluator.model_name} via {provider.value.upper()}...")
    if verbose:
        print("🔍 Verbose logging enabled - you'll see all API interactions below")
    
    results = evaluator.run_evaluation()
    
    # Generate report
    report = evaluator.generate_report()
    
    # Save report
    report_path = f"../report/{provider.value}_nutrition_evaluation_report.md"
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w") as f:
        f.write(report)
    
    # Show summary
    total_scores = [r.total_score for r in results]
    print(f"\n{'='*60}")
    print(f"🎉 Evaluation Complete!")
    print(f"Provider: {provider.value.upper()}")
    print(f"Model: {evaluator.model_name}")
    print(f"Average Score: {statistics.mean(total_scores):.1f}%")
    print(f"Report saved to: {report_path}")
    if verbose:
        print(f"✅ All API calls and responses were logged above for verification")

if __name__ == "__main__":
    main() 