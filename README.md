<<<<<<< HEAD
# GPT Nutrition Knowledge Evaluator

A comprehensive evaluation framework for testing GPT models on nutrition-related tasks using Calorie King food data format.

## Features

- **Multi-dimensional evaluation**: Tests factual accuracy, mathematical computation, health recommendations, and error detection
- **Automated scoring**: Uses weighted scoring across 4 criteria (Accuracy 40%, Reasoning 30%, Completeness 20%, Practical 10%)
- **Real nutrition data**: Uses actual Calorie King format nutrition data
- **Comprehensive reporting**: Generates detailed markdown reports with scores and analysis
- **Multiple difficulty levels**: From basic data reading to expert-level error detection

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

### Evaluation Categories

The system tests 4 key areas:

1. **Factual Accuracy** (Basic)
   - Reading nutrition data correctly
   - Understanding units and measurements
   - Basic nutritional calculations

2. **Mathematical Computation** (Intermediate)
   - Calorie calculations using 4-4-9-7 rule
   - Percentage calculations for macronutrients
   - Comparing calculated vs. provided values

3. **Health Recommendations** (Advanced)
   - Evaluating food suitability for health conditions
   - Understanding dietary restrictions
   - Practical nutrition advice

4. **Error Detection** (Expert)
   - Identifying impossible nutritional values
   - Spotting data inconsistencies
   - Data validation skills

### Sample Nutrition Data Format

The evaluator uses Calorie King format:
```json
{
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
```

## Output

The program generates:
- **nutrition_evaluation_report.md**: Detailed markdown report with scores and analysis
- Console output with summary statistics

### Sample Report Structure

```
# GPT Nutrition Evaluation Report

**Model:** gpt-4
**Date:** 2024-01-15 14:30:00
**Total Prompts:** 4

## Summary
- Overall Average: 85.2%
- Best Performance: 92.1%
- Worst Performance: 78.5%

## Detailed Results
...
```

## Scoring System

Each prompt is scored on 4 dimensions:

- **Accuracy (40%)**: Correctness of facts and calculations
- **Reasoning (30%)**: Quality of explanations and logical thinking
- **Completeness (20%)**: Addressing all parts of the question
- **Practical Application (10%)**: Real-world relevance

Total score is calculated as: `0.4×Accuracy + 0.3×Reasoning + 0.2×Completeness + 0.1×Practical`

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
- gpt-4
- gpt-4-turbo
- gpt-3.5-turbo
- gpt-3.5-turbo-16k

## API Costs

Approximate costs per evaluation (4 prompts):
- GPT-4: ~$0.15-0.25
- GPT-3.5-Turbo: ~$0.02-0.05

## Examples

### Running Evaluation
```bash
$ python nutrition_evaluator.py
Enter OpenAI API key: sk-...
Enter model name (default: gpt-4): gpt-4

Evaluating gpt-4...
Starting evaluation of gpt-4
Running prompt 1/4: 1A
Running prompt 2/4: 2A
Running prompt 3/4: 3A
Running prompt 4/4: 4A
Evaluation completed

Evaluation Complete!
Average Score: 87.3%
Report saved to: nutrition_evaluation_report.md
```

### Programmatic Usage
```python
from nutrition_evaluator import NutritionEvaluator

# Initialize evaluator
evaluator = NutritionEvaluator(api_key="your-key", model_name="gpt-4")

# Run evaluation
results = evaluator.run_evaluation()

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

## Contributing

To extend the evaluation framework:

1. Add new nutrition data samples in `_initialize_prompts()`
2. Create new evaluation categories
3. Enhance the scoring algorithm in `_score_response()`
4. Add new output formats (JSON, CSV, etc.)

## License

This evaluation framework is designed for research and educational purposes.
=======
# CalorieKing Data Scraper

This script fetches nutritional information from the CalorieKing API and saves it to a CSV file.

## Setup

1. Clone this repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Create your configuration file:
   ```bash
   cp config.template.py config.py
   ```
4. Edit `config.py` and replace `your_access_token_here` with your actual CalorieKing API access token

## Usage

Run the script:
```bash
python calorie_king_scraper.py
```

The script will:
- Fetch all foods from the CalorieKing database
- Get detailed nutritional information for each food
- Save the data to `calorie_king_data.csv`
- Create periodic backups in `calorie_king_data_partial.csv`
- Save data to `calorie_king_data_error.csv` if an error occurs

## Output

The CSV file will contain the following information for each food:
- Name
- Brand name
- Classification
- Nutritional values:
  - Energy
  - Fat
  - Net Carbs
  - Protein
  - Sugar
  - Fiber
  - Calcium
  - Sodium
  - Saturated Fat
  - Trans Fat
  - Polyunsaturated Fat
  - Monounsaturated Fat
  - Omega-3 Fat
  - Cholesterol
  - Alcohol
  - Potassium
  - Iron
  - Vitamin C 
>>>>>>> 1de3c1a (feat: Add CalorieKing API data scraper)
