# Comment Classification Tool

This project provides a command-line tool to classify comments submitted in response to the Ontario Bill 212, the **Reducing Gridlock, Saving You Time Act, 2024**, which is informally known as the "bike lane bill." The script uses the OpenAI API to evaluate comments and return a machine-readable label indicating whether each comment is "for" or "against" the proposed legislation.

## Purpose

Manually classifying these comments (i.e., determining whether each comment supports or opposes the bill) is both time-consuming and subject to human bias. This tool helps automate the classification process using a language model, thereby saving time and providing a consistent approach to analyzing public opinion.

## Methodology

1. **Contextual Prompting**:  
   Each comment is analyzed alongside a description of the bill. The model is instructed to read a given comment and determine if the commenter supports or opposes the changes outlined in Bill 212.

2. **Machine-Readable Results**:  
   The model returns "for" if the comment supports the bill and "against" if the comment opposes it. This makes it easy to tally results or conduct further quantitative analysis.

3. **Token Counting (Dry Run)**:  
   Before running a full classification, you can use the `--dry-run` option to estimate the total token usage (and therefore costs) without making API calls.

## Requirements

- Python 3.8+
- `openai` Python library (version 1.0.0+)
- `tiktoken` for token counting
- `rich` for enhanced console output
- A valid OpenAI API key

## Installation

1. **Create a virtual environment (recommended)**:
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```
   
2. **Install required packages**:
    ```bash
    pip install openai tiktoken rich
    ```

3. **Set the OpenAI API key**:
    - As an environment variable:
      ```bash
      export OPENAI_API_KEY="your-api-key-here"
      ```
    - Or use the `--openai-api-key` argument when running the script.

## Usage

**Command:**
```bash
python classify.py [directory] [options]
```

**Arguments:**
- **directory** (required): The path to a directory containing `.json` files with comments. Each file should have a structure like:
    ```json
    {
      "103658": {
        "url": "/comment/103658",
        "comment": "I believe removing bike lanes is a terrible idea..."
      },
      "103661": {
        "url": "/comment/103661",
        "comment": "This bill will help build highways faster and reduce congestion..."
      }
    }
    ```

**Optional Arguments:**
- `--dry-run`: Estimate token usage without making OpenAI API calls.
- `--openai-api-key`: Provide the API key directly. If not set, the script uses the `OPENAI_API_KEY` environment variable.
- `--output-csv`: Specify the output CSV file name. Default is `results.csv`.
- `--model`: Specify the model name. Default is `gpt-4o-mini`. Adjust this to a model you have access to, such as `gpt-4`.

**Example Run:**
```bash
python classify.py ./comment_data --openai-api-key YOUR_KEY --model gpt-4 --output-csv my_results.csv
```

A separate validation script, `validate.py`, is provided to help verify the accuracy of the model's classifications. This script allows a human reviewer to randomly sample a set of comments and provide their own "for" or "against" judgments, then compare these judgments against the model’s predictions to measure agreement.

### How It Works

1. **Random Sampling of Comments**:
   The script reads all comments from the specified directory (in `.json` files) and looks up their corresponding stances from the `results.csv` file.

2. **User Input**:
   It then randomly selects a specified number of these comments and presents them, one by one, to the user via the command line. The user is asked to classify each comment as "for" or "against."

3. **Comparison and Report**:
   Once the user has classified all the sampled comments, the script compares these user-provided classifications against the model's original predictions. It then reports a percentage agreement (i.e., how often the user and the model agreed).

4. **CSV Output**:
   The user's classifications and the agreement results are saved to a CSV file for later review.

### Usage

**Command:**
```bash
python validate.py [directory] [results_csv] [num_samples] [options]
```
