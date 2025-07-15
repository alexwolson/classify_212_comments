# Strong Mayor Powers Detection Tool

This project provides a command-line tool to classify documents for the presence or absence of references to "Strong Mayor Powers" within public consultation documents. The script uses the Google Gemini API to evaluate documents and return a machine-readable label indicating whether each document contains references to Strong Mayor Powers concepts.

**🚀 Now using the new Google GenAI API with direct document upload - no more text extraction dependencies!**

## Purpose

Strong Mayor Powers refer to enhanced mayoral authorities introduced in Ontario municipalities, including authority to override certain council decisions, enhanced control over municipal planning processes, and streamlined decision-making capabilities. This tool helps identify and analyze public discourse around these governance changes by automatically detecting references to Strong Mayor Powers in public comments and consultation responses.

## Methodology

1. **Direct Document Processing**:  
   Documents are uploaded directly to the Gemini API using the new Google GenAI library. No text extraction is performed locally - Google's models handle document processing internally.

2. **Machine-Readable Results**:  
   The model returns "present" if the document contains references to Strong Mayor Powers and "absent" if no such references are found. Results use structured response schemas for reliability.

3. **Token Estimation (Dry Run)**:  
   Before running a full classification, you can use the `--dry-run` option to estimate the total token usage (and therefore costs) without making API calls.

## Requirements

- Python 3.8+
- `google-genai` Python library for Google Gemini API (new API)
- `rich` for enhanced console output
- A valid Gemini API key

**Note**: The tool no longer requires text extraction libraries (pdfplumber, python-docx, etc.) as documents are processed directly by the Gemini API.

## Installation

1. **Create a virtual environment (recommended)**:
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```
   
2. **Install required packages**:
    ```bash
    pip install google-genai rich
    ```

3. **Set the Gemini API key**:
    - As an environment variable:
      ```bash
      export GEMINI_API_KEY="your-api-key-here"
      ```
    - Or use the `--gemini-api-key` argument when running the script.

## Usage

**Command:**
```bash
python classify.py [input_directory] [options]
```

**Arguments:**
- **input_directory** (required): A directory containing document files (PDF, TXT, HTML, DOCX, RTF) with comments

**Input Format:**

**Document Directory Format**: A directory containing document files where:
  - Each document file contains the content of one comment
  - The filename (without extension) is used as the comment ID
  - Documents are processed directly by the Gemini API (no local text extraction)
  - **Supported formats:**
    - **PDF files** (`.pdf`): Processed directly by Gemini
    - **Text files** (`.txt`, `.text`): Plain text files
    - **HTML files** (`.html`, `.htm`): Processed directly with tag handling
    - **Word documents** (`.docx`): Processed directly by Gemini
    - **RTF files** (`.rtf`): Rich text format processed directly

**Optional Arguments:**
- `--dry-run`: Estimate token usage without making Google Gemini API calls.
- `--gemini-api-key`: Provide the API key directly. If not set, the script uses the `GEMINI_API_KEY` environment variable.
- `--output-csv`: Specify the output CSV file name. Default is `results.csv`.
- `--model`: Specify the model name. Default is `gemini-2.5-flash`. You can also use `gemini-2.5-pro` for potentially better accuracy.

**Large Document Handling:**
The new Gemini API can handle documents up to 1 million tokens directly. Very large documents are processed as a single unit without chunking, providing more coherent analysis.

**Example Runs:**
```bash
# Process document directory to detect Strong Mayor Powers references
python classify.py ./document_comments --gemini-api-key YOUR_KEY --model gemini-2.5-pro

# Process document directory with custom output file
python classify.py ./document_comments --gemini-api-key YOUR_KEY --output-csv strong_mayor_results.csv

# Dry run to estimate costs for document directory
python classify.py ./document_comments --dry-run
```

## Key Changes in New Version

**🚀 Major API Update**: The tool now uses the new Google GenAI API with significant improvements:

- **Direct Document Upload**: Documents are sent directly to Gemini without local text extraction
- **Simplified Dependencies**: No longer requires pdfplumber, python-docx, beautifulsoup4, striprtf
- **Better Document Processing**: Google's models handle text extraction more reliably
- **Structured Responses**: Uses enum-based response schemas for better consistency
- **Updated Model**: Now uses `gemini-2.5-flash` with 1 million token context window
- **Environment Variable**: Changed from `GOOGLE_API_KEY` to `GEMINI_API_KEY`
- **Input Simplification**: Only supports directory input (JSON input removed)

**Migration Guide**:
- Update environment variable: `GOOGLE_API_KEY` → `GEMINI_API_KEY`
- Update dependencies: Remove text extraction libraries, install `google-genai`
- Convert JSON input to directory of document files
- Update command arguments: `--google-api-key` → `--gemini-api-key`
