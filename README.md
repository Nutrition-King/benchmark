# LLM Nutrition Knowledge Evaluator

A comprehensive evaluation framework for testing LLM models on nutrition-related tasks using real Calorie King food data. This system uses **JSON-structured responses** and **precise numerical comparison** to provide accurate, bias-free evaluation of LLM nutritional knowledge.

**Supported APIs:**
- 🔵 **OpenAI** (GPT-4, GPT-4o, GPT-3.5-turbo)
- 🟢 **IBM WatsonX AI** (Granite, Llama, Mistral models)

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
- **🔄 Multi-API support**: Choose between OpenAI and IBM WatsonX AI
- **⚡ Easy configuration**: Environment variables or interactive setup

## Project Structure

```
benchmark/
├── src/                          # Source code directory
│   ├── calorie_king_scraper.py   # Data collection script
│   ├── nutrition_evaluator.py    # Main evaluation framework (multi-API)
│   └── config.py                 # API configuration
├── data/                         # Generated data directory
│   └── calorie_king_data.csv     # Scraped nutrition data
├── report/                       # Generated reports directory
│   ├── openai_nutrition_evaluation_report.md   # OpenAI results
│   └── watsonx_nutrition_evaluation_report.md  # WatsonX results
├── requirements.txt              # Python dependencies (includes both APIs)
├── meal_lookup.py                # Standalone meal carbohydrate lookup utility
└── README.md                     # This file
```

## Installation

1. Install required packages:
```bash
pip install -r requirements.txt
```

This will install dependencies for both OpenAI and IBM WatsonX AI APIs:
- `openai>=1.0.0` (for OpenAI models)
- `ibm-watsonx-ai>=1.1.0` (for IBM WatsonX models)
- Other utility packages

2. Set up API credentials (choose one or both):

### Option A: OpenAI Setup
```bash
export OPENAI_API_KEY="your-openai-api-key"
```

### Option B: IBM WatsonX Setup
```bash
export WATSONX_API_KEY="your-watsonx-api-key"
export WATSONX_URL="https://us-south.ml.cloud.ibm.com"
export WATSONX_PROJECT_ID="your-project-id"
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
   cd src
   python calorie_king_scraper.py
   ```

3. **Data Collection Process**:
   ```
   🔍 Fetching foods from CalorieKing API...
   📦 Found 500+ food items
   📋 Getting detailed nutrition for each item...
   💾 Saving to ../data/calorie_king_data.csv
   ✅ Data collection complete!
   ```

### Step 2: Verify Data Structure

The scraper creates `data/calorie_king_data.csv` (from the project root) with this format:
```csv
name,brand_name,classification,energy,fat,netCarbs,protein,sugar,fiber,calcium,sodium,satFat,transFat,cholesterol,potassium,iron,vitaminC
"Banana, raw, edible portion",- Average All Brands -,"Fruit, fresh",378.0,0.1,19.8,1.7,16.9,2.7,5.0,1.0,0.0,0.0,0.0,342.0,0.5,12.0
"Avocado, Hass, raw, edible portion",- Average All Brands -,"Fruit, fresh",855.0,21.2,0.6,2.0,0.6,2.8,12.0,4.0,5.1,0.0,0.0,520.0,0.0,0.0
```

### Step 3: Run LLM Evaluations

The nutrition evaluator automatically loads this CSV data:
```bash
cd src
python nutrition_evaluator.py
```

**Data Flow:**
```
src/calorie_king_scraper.py → data/calorie_king_data.csv → src/nutrition_evaluator.py → report/nutrition_evaluation_report.md
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

## 🍽️ Meal Carbohydrate Lookup

In addition to LLM evaluation, this project includes a **standalone meal lookup utility** that searches the CalorieKing database for carbohydrate information.

### Quick Lookup Examples

```bash
# Interactive mode - search for any meal
python3 meal_lookup.py

# Example searches
🔍 Enter meal name: hard boiled egg
🔍 Enter meal name: banana  
🔍 Enter meal name: chicken breast
```

### Programmatic Usage

```python
from meal_lookup import MealLookup

# Initialize lookup
lookup = MealLookup()

# Search for carbohydrate info
results = lookup.search("hard boiled egg")
for food in results:
    print(f"{food['name']}: {food['carb_info']['total_carbs_g']:.1f}g carbs")

# Quick carb value only
carbs = lookup.get_carbs_only("banana")  # Returns: 22.5

# Pretty print detailed results
lookup.print_results("chicken", max_results=3)
```

### Search Features

- **🔍 Fuzzy matching**: Finds foods even with approximate spelling
- **📊 Complete carb breakdown**: Total carbs, net carbs, fiber, sugar
- **🥗 Additional nutrients**: Energy, protein, fat, sodium  
- **⭐ Relevance scoring**: Results ranked by match quality
- **🎯 Multiple results**: Shows top matches for broader searches

### Sample Output

```
🔍 Carbohydrate information for 'banana':
================================================================================

1. Banana, raw, edible portion
   Category: Fruit, fresh
   Relevance: 90.0%

   📊 CARBOHYDRATE BREAKDOWN:
   • Total Carbohydrates: 22.5g
   • Net Carbs: 19.8g
   • Fiber: 2.7g
   • Sugar: 16.9g

   🍽️  OTHER NUTRIENTS:
   • Energy: 378 kJ
   • Protein: 1.7g
   • Fat: 0.1g
   • Sodium: 1mg
```

## Quick Start

### Method 1: Interactive Mode (Recommended)
```bash
cd src
python nutrition_evaluator.py
```

The evaluator will prompt you to:
1. **Choose API provider** (OpenAI or IBM WatsonX)
2. **Enter credentials** (or use environment variables)
3. **Select model** (or use defaults)

#### Sample Interactive Session:
```
🍎 LLM Nutrition Knowledge Evaluator
==================================================
Enable verbose API logging? (y/N): y
✅ Verbose mode enabled - will show detailed API calls and responses

Choose API provider:
1. OpenAI
2. IBM WatsonX
Enter choice (1 or 2): 2

--- IBM WatsonX Configuration ---
Enter WatsonX API key: [using environment variable]
Enter WatsonX URL (default: https://us-south.ml.cloud.ibm.com): [using default]
Enter WatsonX Project ID: [using environment variable]

Select WatsonX model:
1. ibm/granite-3-8b-instruct (default - fast, cost-effective)
2. ibm/granite-13b-instruct-v2 (larger granite model)
3. meta-llama/llama-3-3-70b-instruct (high quality)
4. mistralai/mistral-large (alternative high quality)
Enter choice (1-4, default 1): 1
Selected model: ibm/granite-3-8b-instruct

Evaluating ibm/granite-3-8b-instruct via WATSONX...
🔍 Verbose logging enabled - you'll see all API interactions below
```

### Method 2: WatsonX Quick Demo
```bash
python watsonx_demo.py
```

This uses the provided WatsonX credentials and runs a quick evaluation with the Granite model.

### Method 3: OpenAI Quick Demo  
```bash
cd src
python demo.py
```

## Usage Examples

### 🔵 OpenAI Example
```bash
# Set your OpenAI API key
export OPENAI_API_KEY="sk-..."

# Run evaluation
cd src
python nutrition_evaluator.py

# Choose option 1 (OpenAI)
# Select model: 1 (gpt-4o-mini - recommended for testing)
```

### 🟢 IBM WatsonX Example
```bash
# Set your WatsonX credentials
export WATSONX_API_KEY="your_key"
export WATSONX_URL="https://us-south.ml.cloud.ibm.com"  
export WATSONX_PROJECT_ID="your_id"

# Run evaluation
cd src
python nutrition_evaluator.py

# Choose option 2 (IBM WatsonX)
# Select model: 1 (ibm/granite-3-8b-instruct - recommended for testing)
```

### 🐍 Programmatic Usage
```python
from nutrition_evaluator import NutritionEvaluator, APIConfig, APIProvider

# OpenAI Configuration
openai_config = APIConfig(
    provider=APIProvider.OPENAI,
    openai_api_key="sk-..."
)
evaluator = NutritionEvaluator(api_config=openai_config, model_name="gpt-4o-mini")

# WatsonX Configuration  
watsonx_config = APIConfig(
    provider=APIProvider.WATSONX,
    watsonx_api_key="your-key",
    watsonx_url="https://us-south.ml.cloud.ibm.com",
    watsonx_project_id="your-project-id"
)
evaluator = NutritionEvaluator(api_config=watsonx_config, model_name="ibm/granite-3-8b-instruct")

# Enable verbose logging to see actual API calls
evaluator.enable_verbose_logging()

# Run evaluation
results = evaluator.run_evaluation()
```

### 🔍 Verbose API Logging

The evaluator includes **verbose logging** to show actual API calls and responses, proving the data comes from real APIs and isn't fabricated:

#### Interactive Mode:
```bash
cd src
python nutrition_evaluator.py
# Choose: Enable verbose API logging? (y/N): y
```

#### Programmatic Mode:
```python
# Enable during initialization
evaluator = NutritionEvaluator(api_config=config, verbose=True)

# Or enable later
evaluator.enable_verbose_logging()
```

#### Sample Verbose Output:
```
================================================================================
🔄 API CALL TO WATSONX
Model: ibm/granite-3-8b-instruct
================================================================================
📤 PROMPT SENT:
----------------------------------------
Given the following nutrition data for Banana, raw, edible portion:
{
  "energy": 378.0,
  "fat": 0.1,
  "netCarbs": 19.8,
  "protein": 1.7,
  "sugar": 16.9,
  "fiber": 2.7
}

Question: What is the total fat content and total carbohydrate content...
----------------------------------------

🟢 Making WatsonX API call...
   API Key: xxx
   URL: https://us-south.ml.cloud.ibm.com
   Project ID: xxxx
   Trying chat method first...

📥 WATSONX CHAT RESPONSE RECEIVED:
   Response structure: ['choices', 'usage', 'model']
   Token usage: {'prompt_tokens': 245, 'completion_tokens': 67, 'total_tokens': 312}
   Raw response type: <class 'dict'>
   Execution Time: 2.34s
----------------------------------------
{
  "total_fat_g": 0.1,
  "total_carbohydrates_g": 22.5,
  "carb_calculation": {
    "net_carbs": 19.8,
    "fiber": 2.7,
    "total": 22.5
  }
}
----------------------------------------
```

This verbose logging shows:
- ✅ **Real API endpoints** and credentials being used
- ✅ **Actual prompts** sent to the models  
- ✅ **Raw responses** received from APIs
- ✅ **Token usage** and timing information
- ✅ **Model identification** and response metadata

## 🎯 Evaluation Categories

The system tests LLMs across four key areas:

### 1. **Factual Accuracy** (Basic)
Tests ability to extract specific nutritional values from provided data
- Extract fat content and carbohydrate content  
- Verify calculation of total carbohydrates (net carbs + fiber)
- **Scoring**: Direct numerical comparison with 0.01g tolerance

### 2. **Mathematical Computation** (Intermediate) 
Tests nutritional calculations using the 4-4-9-7 calorie rule
- Calculate calories from macronutrients (carbs: 4 cal/g, protein: 4 cal/g, fat: 9 cal/g, alcohol: 7 cal/g)
- Compare calculated values with provided energy data
- **Scoring**: Mathematical accuracy with 0.1 calorie tolerance

### 3. **Health Recommendations** (Advanced)
Tests ability to evaluate food suitability for health conditions
- Assess suitability for Type 2 diabetes, high blood pressure, high cholesterol
- Apply evidence-based nutritional guidelines
- **Scoring**: Correct suitability rating (poor/fair/good) based on nutrient thresholds

### 4. **Error Detection** (Expert)
Tests ability to identify nutritional data inconsistencies  
- Detect impossible values (negative nutrients, saturated fat > total fat)
- Identify data integrity issues
- **Scoring**: Correct identification of data errors

## 💰 API Costs

### OpenAI Costs
Approximate costs per evaluation (4 prompts, ~1000 tokens each):
- **GPT-4o-mini**: ~$0.01-0.02 (recommended for testing)
- **GPT-4o**: ~$0.05-0.10  
- **GPT-4**: ~$0.15-0.25

### IBM WatsonX Costs
WatsonX pricing varies by model and usage. Check IBM pricing for current rates:
- **Granite models**: Generally cost-effective for testing
- **Llama models**: Higher quality, moderate cost
- **Mistral models**: Balance of performance and cost

## Model Recommendations

### 🔵 OpenAI Models
- **Testing/Development**: `gpt-4o-mini` (fast, cost-effective)
- **Production**: `gpt-4o` (best balance of speed/quality)
- **Maximum Quality**: `gpt-4` (slower but highest accuracy)

### 🟢 IBM WatsonX Models
- **Testing/Development**: `ibm/granite-3-8b-instruct` (fast, cost-effective)
- **Balanced Performance**: `ibm/granite-13b-instruct-v2` (larger granite model)
- **High Quality**: `meta-llama/llama-3-3-70b-instruct` (excellent accuracy)
- **Premium**: `meta-llama/llama-3-405b-instruct` (highest quality, slower)
- **Alternative**: `mistralai/mistral-large` (good performance)

## Troubleshooting

### Common Issues

1. **API Key Error**: Ensure your OpenAI API key is valid and has sufficient credits
2. **Rate Limiting**: The program includes 1-second delays between requests  
3. **Model Not Found**: Ensure you have access to the specified model
   - For WatsonX, use only models from the supported list shown during configuration
   - Run with verbose logging to see the exact error message
4. **Missing CSV Data**: If `data/calorie_king_data.csv` doesn't exist, run the scraper first:
   ```bash
   cd src
   python calorie_king_scraper.py
   ```
5. **Scraper Access Issues**: Configure your CalorieKing API token in `config.py`
6. **Small Dataset**: For testing without full scraper, create minimal CSV with 3-4 food items
7. **WatsonX Model Access**: Some models require special access permissions - stick to the suggested models

### Error Handling

The evaluator includes comprehensive error handling:
- API failures are logged with error messages
- Invalid responses are handled gracefully
- Execution continues even if individual prompts fail
- Model availability is checked before initialization

## 🛠️ Contributing

To extend the evaluation framework:

1. **Add new food data**: Expand `data/calorie_king_data.csv` with more diverse foods (located at project root)
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
