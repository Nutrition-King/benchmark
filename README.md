# GPT Nutrition Knowledge Evaluator

A comprehensive evaluation framework for testing GPT models on nutrition-related tasks using real Calorie King food data. This system uses **JSON-structured responses** and **precise numerical comparison** to provide accurate, bias-free evaluation of LLM nutritional knowledge.

## 🔥 Why This Approach Works

**The Problem:** Traditional LLM evaluation often suffers from style bias - a model giving a perfect answer might score only 30% due to keyword-based scoring that looks for specific phrases rather than actual correctness.

**Our Solution:** 
- ✅ **Force structured JSON responses** - eliminates style variations
- ✅ **Direct numerical comparison** - 0.1g fat is either correct or not  
- ✅ **Real food data from CSV** - no hardcoded synthetic examples
- ✅ **Few-shot prompting** - shows models exactly what format to use
- ✅ **Pure accuracy focus** - only correctness matters, not writing style

**Result:** Reliable 90-100% scores for correct answers instead of misleading 30% scores!

## ✨ Features

- **🎯 Accuracy-focused evaluation**: JSON-structured responses eliminate style bias
- **📊 Real nutrition data**: Uses actual Calorie King CSV data (no hardcoded values)
- **🧮 Precise numerical scoring**: Direct comparison of calculated values
- **📝 Few-shot prompting**: Examples ensure consistent response format
- **🔬 Multiple test categories**: Factual accuracy, mathematical computation, health recommendations, error detection
- **📈 Reliable scoring**: 90-100% scores for correct answers (not 30% due to style issues)
- **🎨 Clean JSON reports**: Formatted code blocks for easy analysis

## Installation

1. Install required packages:
```bash
pip install -r requirements.txt
```

2. Set up your OpenAI API key:
```bash
export OPENAI_API_KEY="your-api-key-here"
```

Or you'll be prompted to enter it when running the program.

## Usage

### Basic Usage

Run the evaluator with default settings:
```bash
python nutrition_evaluator.py
```

This will:
1. Prompt for your OpenAI API key (if not set as environment variable)
2. Ask for the model name to evaluate (default: gpt-4)
3. Run all evaluation prompts
4. Generate a detailed report

### 🧪 Evaluation Categories

The system tests 4 key areas using **structured JSON responses**:

#### **1A: Factual Accuracy** (Basic)
- Extract total fat and carbohydrate content from nutrition data
- Calculate total carbs (net carbs + fiber)
- JSON format ensures precise numerical comparison
```json
{
  "total_fat_g": 0.1,
  "total_carbohydrates_g": 22.5,
  "carb_calculation": {"net_carbs": 19.8, "fiber": 2.7, "total": 22.5}
}
```

#### **2A: Mathematical Computation** (Intermediate)
- Calculate calories using 4-4-9-7 rule (carbs: 4, protein: 4, fat: 9, alcohol: 7 cal/g)
- Compare calculated vs. given energy values
- Detect unit differences (kcal vs kJ)

#### **3A: Health Recommendations** (Advanced)
- Evaluate food suitability for diabetes, hypertension, high cholesterol
- Use evidence-based thresholds (e.g., >15g sugar = poor for diabetes)
- Structured assessment with specific nutritional concerns

#### **4A: Error Detection** (Expert)
- Identify nutritionally impossible values (saturated fat > total fat)
- Catch data entry errors (negative nutrients)
- Validate nutritional consistency

### 📋 Data Source

The evaluator loads real nutrition data from `data/calorie_king_data.csv`:

| Food Item | Energy (kJ) | Fat (g) | Protein (g) | Net Carbs (g) | Fiber (g) | Sodium (mg) |
|-----------|------------|---------|-------------|---------------|-----------|-------------|
| Banana, raw | 378 | 0.1 | 1.7 | 19.8 | 2.7 | 1 |
| Avocado, Hass | 855 | 21.2 | 2.0 | 0.6 | 2.8 | 4 |
| Rump Steak, lean | 511 | 4.6 | 20.2 | 0.0 | 0.0 | 49 |
| Cookie Dough Ice Cream | 1130 | 15.0 | 4.0 | 31.0 | - | 56 |

**Key Benefits:**
- ✅ **Real food data** (not synthetic examples)
- ✅ **Diverse food types** (fruits, proteins, processed foods)
- ✅ **Edge cases included** (missing values, high sodium, etc.)
- ✅ **Dynamic prompts** generated from actual data

## 📊 Output & Scoring

### Generated Reports
- **nutrition_evaluation_report.md**: Detailed markdown report with JSON comparisons
- **Console output**: Real-time progress and summary statistics

### Sample Report Structure
```markdown
# GPT Nutrition Evaluation Report

**Model:** gpt-4o-mini
**Date:** 2024-01-15 14:30:00
**Total Prompts:** 4

## Summary
- Overall Average: 92.5%
- Best Performance: 100.0%
- Worst Performance: 75.0%

### 1A: Factual Accuracy
Score: 100.0%

**Expected JSON:**
```json
{
  "total_fat_g": 0.1,
  "total_carbohydrates_g": 22.5,
  "carb_calculation": {"net_carbs": 19.8, "fiber": 2.7, "total": 22.5}
}
```

**GPT Response:**
```json
{
  "total_fat_g": 0.1,
  "total_carbohydrates_g": 22.5,
  "carb_calculation": {"net_carbs": 19.8, "fiber": 2.7, "total": 22.5}
}
```
```

### 🎯 Scoring System

**Pure Accuracy Focus:**
- ✅ **100%**: All JSON fields match expected values exactly
- ✅ **Partial credit**: Proportional scoring for partially correct responses  
- ✅ **0%**: Invalid JSON or major calculation errors
- ✅ **Floating-point tolerance**: ±0.01 for numerical comparisons

**Per-Category Scoring:**
- **1A (Factual)**: 3 points - fat value, carb value, calculation breakdown
- **2A (Math)**: 4 points - individual calorie calculations + total
- **3A (Health)**: 3 points - diabetes, hypertension, cholesterol evaluations  
- **4A (Error)**: 3 points - error count + identification of critical issues

**No style bias**: Only numerical accuracy and structural correctness matter!

## Customization

### Adding New Prompts

Modify the `_initialize_prompts()` method in `NutritionEvaluator` class:

```python
{
    "id": "5A",
    "category": "New Category",
    "difficulty": "Advanced",
    "prompt": "Your prompt text with nutrition data...",
    "expected_answer": "Expected response..."
}
```

### Adjusting Scoring

Modify the `_score_response()` method to change scoring criteria or weights.

### Testing Different Models

The evaluator works with any OpenAI model:
- **gpt-4o** / **gpt-4o-mini** (recommended)
- **gpt-4** / **gpt-4-turbo**
- **gpt-3.5-turbo**

## 💰 API Costs

Approximate costs per evaluation (4 prompts, ~1000 tokens each):
- **GPT-4o-mini**: ~$0.01-0.02 (recommended for testing)
- **GPT-4o**: ~$0.05-0.10  
- **GPT-4**: ~$0.15-0.25

## Examples

### 🚀 Running Evaluation
```bash
$ python3 nutrition_evaluator.py
Enter OpenAI API key: sk-...
Enter model name (default: gpt-4o-mini): 

Evaluating gpt-4o-mini...
✅ Loaded 10 food items from CSV
Starting evaluation of gpt-4o-mini
Running prompt 1/4: 1A - Factual Accuracy
Running prompt 2/4: 2A - Mathematical Computation  
Running prompt 3/4: 3A - Health Recommendations
Running prompt 4/4: 4A - Error Detection
Evaluation completed

🎉 Evaluation Complete!
Average Score: 94.2%
Best Performance: 100.0%
Worst Performance: 75.0%
Report saved to: nutrition_evaluation_report.md
```

### 🐍 Programmatic Usage
```python
from nutrition_evaluator import NutritionEvaluator
import json

# Initialize evaluator
evaluator = NutritionEvaluator(api_key="your-key", model_name="gpt-4o-mini")

# Run evaluation  
results = evaluator.run_evaluation()

# Access individual results
for result in results:
    print(f"Prompt {result.prompt_id}: {result.total_score:.1f}%")
    if result.total_score < 90:
        print(f"  Response: {result.gpt_response}")

# Generate report
report = evaluator.generate_report()
print(report)
```

## Troubleshooting

### Common Issues

1. **API Key Error**: Ensure your OpenAI API key is valid and has sufficient credits
2. **Rate Limiting**: The program includes 1-second delays between requests
3. **Model Not Found**: Ensure you have access to the specified model

### Error Handling

The evaluator includes comprehensive error handling:
- API failures are logged with error messages
- Invalid responses are handled gracefully
- Execution continues even if individual prompts fail

## 🛠️ Contributing

To extend the evaluation framework:

1. **Add new food data**: Expand `data/calorie_king_data.csv` with more diverse foods
2. **Create new test categories**: Add prompts in `_initialize_prompts()` with JSON schemas
3. **Enhance scoring**: Modify category-specific scoring functions (`_score_factual_accuracy()`, etc.)
4. **Support new models**: Test with different LLM APIs (Anthropic, etc.)
5. **Export formats**: Add JSON/CSV export for automated analysis

### 📋 Design Principles
- **Accuracy over style**: Focus on correctness, not writing quality
- **Structured data**: Use JSON for consistent, parseable responses  
- **Real-world data**: Base tests on actual nutrition information
- **Bias-free scoring**: Eliminate subjective evaluation criteria
- **Reproducible results**: Deterministic scoring with clear thresholds

## 📄 License

This evaluation framework is designed for research and educational purposes. Open source under MIT license.
