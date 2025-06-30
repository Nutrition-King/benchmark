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

## 📊 Data Collection Pipeline

### Step 1: Collect Nutrition Data with CalorieKing Scraper

Before running evaluations, you need nutrition data. Use the included scraper to collect real food data:

1. **Configure API Access**:
   ```bash
   cp config.template.py config.py
   # Edit config.py and add your CalorieKing API token
   ```

2. **Run the Scraper**:
   ```bash
   python calorie_king_scraper.py
   ```

3. **Data Collection Process**:
   ```
   🔍 Fetching foods from CalorieKing API...
   📦 Found 500+ food items
   📋 Getting detailed nutrition for each item...
   💾 Saving to data/calorie_king_data.csv
   ✅ Data collection complete!
   ```

### Step 2: Verify Data Structure

The scraper creates `data/calorie_king_data.csv` with this format:
```csv
name,brand_name,classification,energy,fat,netCarbs,protein,sugar,fiber,calcium,sodium,satFat,transFat,cholesterol,potassium,iron,vitaminC
"Banana, raw, edible portion",- Average All Brands -,"Fruit, fresh",378.0,0.1,19.8,1.7,16.9,2.7,5.0,1.0,0.0,0.0,0.0,342.0,0.5,12.0
"Avocado, Hass, raw, edible portion",- Average All Brands -,"Fruit, fresh",855.0,21.2,0.6,2.0,0.6,2.8,12.0,4.0,5.1,0.0,0.0,520.0,0.0,0.0
```

### Step 3: Run LLM Evaluations

The nutrition evaluator automatically loads this CSV data:
```bash
python nutrition_evaluator.py
```

**Data Flow:**
```
calorie_king_scraper.py → data/calorie_king_data.csv → nutrition_evaluator.py → evaluation_report.md
```

### Step 4: How Evaluation Uses Scraped Data

The evaluator intelligently selects foods from your CSV for different test categories:

```python
# Automatic food selection from CSV data
banana_data = next((food for food in foods if "Banana" in food["name"]), foods[0])      # Factual accuracy
steak_data = next((food for food in foods if "Rump Steak" in food["name"]), foods[4])   # Error detection  
processed_data = next((food for food in foods if "Cookie Dough" in food["name"]), foods[3])  # Health recommendations
```

**Smart Selection Criteria:**
- 🍌 **Fruits** (banana, apple) → Factual accuracy & math calculations
- 🥩 **Proteins** (steak, chicken) → Error detection with modified data
- 🍦 **Processed foods** (ice cream, chips) → Health recommendations
- 🥑 **Diverse items** → Comprehensive nutritional testing

**Why This Works:**
- ✅ **Real variability** in nutritional profiles for robust testing
- ✅ **Automatic adaptation** to whatever foods you scrape
- ✅ **Fallback selection** if specific foods aren't found
- ✅ **No hardcoded values** - everything comes from your scraped data

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

### 📋 Data Source & Scraper Features

The evaluator loads real nutrition data from `data/calorie_king_data.csv` collected by our scraper:

| Food Item | Energy (kJ) | Fat (g) | Protein (g) | Net Carbs (g) | Fiber (g) | Sodium (mg) |
|-----------|------------|---------|-------------|---------------|-----------|-------------|
| Banana, raw | 378 | 0.1 | 1.7 | 19.8 | 2.7 | 1 |
| Avocado, Hass | 855 | 21.2 | 2.0 | 0.6 | 2.8 | 4 |
| Rump Steak, lean | 511 | 4.6 | 20.2 | 0.0 | 0.0 | 49 |
| Cookie Dough Ice Cream | 1130 | 15.0 | 4.0 | 31.0 | - | 56 |

**Scraper Features:**
- 🔄 **Automatic backups** (`calorie_king_data_partial.csv` during collection)
- ⚡ **Error recovery** (saves partial data if interrupted)
- 📊 **Progress tracking** (shows collection status)
- 🧹 **Data cleaning** (handles missing values and formatting)

**Data Benefits:**
- ✅ **Real food database** (500+ items from CalorieKing API)
- ✅ **Diverse food types** (fruits, proteins, processed foods, beverages)
- ✅ **Complete nutrition profiles** (20+ nutrients per item)
- ✅ **Edge cases included** (missing values, extreme values for testing)
- ✅ **Dynamic prompts** (evaluation tests generated from actual data)

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

### 🚀 Complete Workflow: Data Collection to Evaluation

#### Step 1: Collect Data
```bash
$ python calorie_king_scraper.py
🔍 Connecting to CalorieKing API...
📦 Found 523 food items
📋 Fetching detailed nutrition data...
[████████████████████] 100% (523/523)
💾 Saved to data/calorie_king_data.csv
✅ Data collection complete! 523 foods scraped
```

#### Step 2: Run Evaluation  
```bash
$ python nutrition_evaluator.py
Enter OpenAI API key: sk-...
Enter model name (default: gpt-4o-mini): 

Evaluating gpt-4o-mini...
✅ Loaded 523 food items from CSV
🍌 Selected Banana for factual accuracy tests
🥩 Selected Rump Steak for error detection  
🍦 Selected Cookie Dough Ice Cream for health recommendations

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
4. **Missing CSV Data**: If `data/calorie_king_data.csv` doesn't exist, run the scraper first:
   ```bash
   python calorie_king_scraper.py
   ```
5. **Scraper Access Issues**: Configure your CalorieKing API token in `config.py`
6. **Small Dataset**: For testing without full scraper, create minimal CSV with 3-4 food items

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
