# Strong Mayor Powers Detection Tool

This project provides a command-line tool to classify comments for the presence or absence of references to "Strong Mayor Powers" within public consultation documents. The script uses the OpenAI API to evaluate comments and return a machine-readable label indicating whether each comment contains references to Strong Mayor Powers concepts.

## Purpose

Strong Mayor Powers refer to enhanced mayoral authorities introduced in Ontario municipalities, including authority to override certain council decisions, enhanced control over municipal planning processes, and streamlined decision-making capabilities. This tool helps identify and analyze public discourse around these governance changes by automatically detecting references to Strong Mayor Powers in public comments and consultation responses.

## Methodology

1. **Contextual Analysis**:  
   Each comment is analyzed to detect explicit or implicit references to Strong Mayor Powers, enhanced mayoral authorities, mayor override powers, or related municipal governance concepts.

2. **Machine-Readable Results**:  
   The model returns "present" if the comment contains references to Strong Mayor Powers and "absent" if no such references are found. This makes it easy to tally results or conduct further quantitative analysis on public opinion regarding mayoral governance changes.

3. **Token Counting (Dry Run)**:  
   Before running a full classification, you can use the `--dry-run` option to estimate the total token usage (and therefore costs) without making API calls.

## Requirements

- Python 3.8+
- `openai` Python library (version 1.0.0+)
- `tiktoken` for token counting
- `rich` for enhanced console output
- `pdfplumber` for PDF text extraction
- `python-docx` for Word document (.docx) text extraction 
- `beautifulsoup4` for HTML text extraction
- `striprtf` for RTF text extraction
- A valid OpenAI API key

## Installation

1. **Create a virtual environment (recommended)**:
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```
   
2. **Install required packages**:
    ```bash
    pip install openai tiktoken rich pdfplumber python-docx beautifulsoup4 striprtf
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
python classify.py [input_path] [options]
```

**Arguments:**
- **input_path** (required): Either:
  - A JSON file containing comments in the format described below, OR
  - A directory containing document files (PDF, TXT, HTML, DOCX, RTF) with comments

**Input Formats:**

1. **JSON File Format**: Each file should have a structure like:
    ```json
    [
      {
        "comment_id": "103658",
        "comment": "I believe removing bike lanes is a terrible idea..."
      },
      {
        "comment_id": "103661", 
        "comment": "This bill will help build highways faster and reduce congestion..."
      }
    ]
    ```

2. **Document Directory Format**: A directory containing document files where:
   - Each document file contains the text of one comment
   - The filename (without extension) is used as the comment ID
   - Text is automatically extracted from the document
   - **Supported formats:**
     - **PDF files** (`.pdf`): Text extracted using pdfplumber
     - **Text files** (`.txt`, `.text`): Plain text files
     - **HTML files** (`.html`, `.htm`): Text extracted with HTML tags removed
     - **Word documents** (`.docx`): Text extracted from paragraphs and tables
     - **RTF files** (`.rtf`): Rich text format with formatting removed

**Optional Arguments:**
- `--dry-run`: Estimate token usage without making OpenAI API calls.
- `--openai-api-key`: Provide the API key directly. If not set, the script uses the `OPENAI_API_KEY` environment variable.
- `--output-csv`: Specify the output CSV file name. Default is `results.csv`.
- `--model`: Specify the model name. Default is `gpt-4o-mini`. Adjust this to a model you have access to, such as `gpt-4`.
- `--max-tokens`: Maximum tokens per request for chunking large PDFs. Default is 120,000 tokens.

**Large Document Handling:**
When processing document files that contain more text than the model's context window can handle, the script automatically:
1. Chunks the text into smaller pieces that fit within the token limit
2. Processes each chunk separately to get individual classifications
3. Uses majority voting to determine the final stance for the entire comment

**Example Runs:**
```bash
# Process JSON file to detect Strong Mayor Powers references
python classify.py comments.json --openai-api-key YOUR_KEY --model gpt-4

# Process document directory (supports PDF, TXT, HTML, DOCX, RTF)
python classify.py ./document_comments --openai-api-key YOUR_KEY --output-csv strong_mayor_results.csv

# Dry run to estimate costs for document directory
python classify.py ./document_comments --dry-run
```

A separate validation script, `validate.py`, is provided to help verify the accuracy of the model's classifications. This script allows a human reviewer to randomly sample a set of comments and provide their own "for" or "against" judgments, then compare these judgments against the model’s predictions to measure agreement.

### How It Works

1. **Random Sampling of Comments**:
   The script reads all comments from the specified directory (in `.json` files) and looks up their corresponding Strong Mayor Powers classifications from the `results.csv` file.

2. **User Input**:
   It then randomly selects a specified number of these comments and presents them, one by one, to the user via the command line. The user is asked to classify each comment as "present" or "absent" for Strong Mayor Powers references.

3. **Comparison and Report**:
   Once the user has classified all the sampled comments, the script compares these user-provided classifications against the model's original predictions. It then reports a percentage agreement (i.e., how often the user and the model agreed).

4. **CSV Output**:
   The user's classifications and the agreement results are saved to a CSV file for later review.

### Usage

**Command:**
```bash
python validate.py [directory] [results_csv] [num_samples] [options]
```
