import os
import enum

import argparse
import sys
import csv
from pathlib import Path
from rich.console import Console
from rich.progress import Progress
import logging
from rich.logging import RichHandler

# ---------------------------------------------------------------------------
# Module‑level constants
# ---------------------------------------------------------------------------
MIME_TYPES: dict[str, str] = {
    '.pdf':  'application/pdf',
    '.txt':  'text/plain',
    '.text': 'text/plain',
    '.html': 'text/html',
    '.htm':  'text/html',
    '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    '.rtf':  'application/rtf',
}

console = Console()
logging.basicConfig(
    level="INFO",
    format="%(message)s",
    handlers=[RichHandler(console=console, rich_tracebacks=True)]
)
logger = logging.getLogger(__name__)

# Google GenAI imports
from google import genai
from google.genai import types

# Enum for response classification
class StrongMayorPowersClassification(enum.Enum):
    PRESENT = "present"
    ABSENT = "absent"

def count_tokens(client: genai.Client, model: str, document_part: types.Part, prompt_part: str) -> int:
    """Return the exact token count for the supplied Gemini contents."""
    info = client.models.count_tokens(
        model=model,
        contents=[document_part, prompt_part],
    )
    return info.total_tokens

def construct_document_prompt() -> str:
    """Construct the prompt for direct document analysis."""
    logger.debug("Prompt constructed.")
    return """
You are analyzing public comments submitted to the Environmental Registry of Ontario (ERO) and other public consultation platforms. Your task is to determine whether each document contains references to "Strong Mayor Powers".

**Background on Strong Mayor Powers:**
Strong Mayor Powers refer to enhanced mayoral authorities introduced in Ontario municipalities. These powers typically include:
- Authority to override certain council decisions with a simple majority vote
- Enhanced control over municipal planning and development processes  
- Greater influence over municipal budget priorities
- Streamlined decision-making capabilities for municipal governance
- Powers to hire and dismiss certain municipal staff directly

Strong Mayor Powers became relevant in Ontario as a way to expedite municipal decision-making, particularly for housing development and infrastructure projects, and were implemented in various Ontario municipalities starting in 2022.

**Your Classification Task:**
Analyze the provided document and determine if it contains any reference to Strong Mayor Powers. You must respond with exactly one of the following:

1. "present" - The document explicitly mentions Strong Mayor Powers, mayoral authorities, enhanced mayoral powers, mayor override powers, or clearly discusses the concept even if not using the exact term.
2. "absent" - The document contains no reference to Strong Mayor Powers or related mayoral authority concepts.

**Guidelines:**
- Look for direct mentions of "Strong Mayor Powers," "mayoral powers," "mayor override," or similar terminology
- Also identify indirect references that clearly discuss enhanced mayoral authorities or municipal governance changes involving mayors
- Return exactly one word: "present" or "absent"
- Do not include explanations in your response
"""

# ---------------------------------------------------------------------------
# Processing helper
# ---------------------------------------------------------------------------
def process_document(
    file_path: Path,
    client: genai.Client,
    model: str,
    dry_run: bool,
) -> tuple[str, int]:
    """
    Classify a single document.

    Returns
    -------
    result : str
        "present" / "absent" (or dry‑run note).
    tokens : int
        Exact tokens used (0 when not --dry-run).
    """
    if dry_run:
        file_bytes = file_path.read_bytes()
        mime_type = MIME_TYPES.get(file_path.suffix.lower(), 'application/octet-stream')
        document_part = types.Part.from_bytes(data=file_bytes, mime_type=mime_type)
        prompt_part = construct_document_prompt()
        tokens = count_tokens(client, model, document_part, prompt_part)
        return f"(dry-run, {tokens} tokens)", tokens

    try:
        file_bytes = file_path.read_bytes()
        mime_type = MIME_TYPES.get(file_path.suffix.lower(), 'application/octet-stream')
        document_part = types.Part.from_bytes(data=file_bytes, mime_type=mime_type)
        prompt_part = construct_document_prompt()
        response = client.models.generate_content(
            model=model,
            contents=[document_part, prompt_part],
            config={
                'response_mime_type': 'text/x.enum',
                'response_schema': StrongMayorPowersClassification,
            },
        )
        result = response.text.strip().lower()
        logger.info(f"Successfully processed {file_path.name} -> {result}")
        return result, 0
    except Exception as e:
        logger.error(f"Error processing {file_path.name}: {e}")
        return "absent", 0

def main():
    parser = argparse.ArgumentParser(description="Process documents to detect references to Strong Mayor Powers.")
    parser.add_argument("input_path", type=str, help="Directory containing document files (PDF, TXT, HTML, DOCX, RTF) with comments.")
    parser.add_argument("--dry-run", action="store_true", help="If provided, only estimate token usage without calling the Google Gemini API.")
    parser.add_argument("--gemini-api-key", type=str, default=None, help="Gemini API key. If not set, must be set as GEMINI_API_KEY environment variable.")
    parser.add_argument("--output-csv", type=str, default="results.csv", help="Output CSV file to store results.")
    parser.add_argument("--model", type=str, default="gemini-2.5-flash", help="Model name to use for the Google Gemini API calls.")
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging verbosity",
    )
    args = parser.parse_args()

    # Respect --log-level
    log_level = args.log_level.upper()
    logger.setLevel(log_level)
    for h in logger.handlers:
        h.setLevel(log_level)

    # Retrieve API key and initialize client (needed even for --dry-run to call count_tokens)
    api_key = args.gemini_api_key or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        logger.error("No Gemini API key provided and not found in environment variables.")
        logger.error("Set GEMINI_API_KEY environment variable or use --gemini-api-key option.")
        return 1

    client = genai.Client(api_key=api_key)

    input_path = Path(args.input_path)
    if not input_path.exists():
        logger.error(f"Error: {input_path} does not exist.")
        return 1
    
    if not input_path.is_dir():
        logger.error(f"Error: {input_path} must be a directory containing document files.")
        logger.error("JSON input is no longer supported. Please provide a directory of document files.")
        return 1

    # Load already processed comments if output file exists
    processed_ids = set()
    output_file = Path(args.output_csv)
    if output_file.is_file():
        logger.info("Resuming from existing output file.")
        with open(output_file, "r", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                processed_ids.add(row["Comment ID"])

    # Load documents from directory
    logger.info("Processing directory input.")
    
    # Find all supported files in the directory
    supported_files = [p for p in input_path.rglob('*') if p.is_file()]
    
    if not supported_files:
        logger.error(f"Error: No supported files found in {input_path}")
        return 1

    logger.info(f"Found {len(supported_files)} supported files.")

    # Prepare document data for processing
    documents = []
    for file_path in supported_files:
            
        # Extract comment ID from filename (remove extension)
        comment_id = file_path.stem
        documents.append({
            "comment_id": comment_id,
            "file_path": file_path
        })

    total_documents = len(documents)

    logger.info(f"Found a total of {total_documents} documents to process.")
    logger.info("Starting processing of documents...")

    total_tokens = 0

    writer = None  # type: ignore[var‑annotated]

    if not args.dry_run:
        is_new = not output_file.exists()
        with output_file.open("a", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=["Comment ID", "Strong Mayor Powers"])
            if is_new:
                writer.writeheader()

            with Progress(console=console) as progress:
                task = progress.add_task("Processing documents...", total=total_documents)
                for document in documents:
                    comment_id = document["comment_id"]
                    if comment_id in processed_ids:
                        progress.update(task, advance=1)
                        continue

                    file_path = document["file_path"]
                    result, _ = process_document(
                        file_path=file_path,
                        client=client,
                        model=args.model,
                        dry_run=False,
                    )

                    progress.update(
                        task,
                        advance=1,
                        description=f"Last: Document {comment_id} -> {result}",
                    )
                    writer.writerow({"Comment ID": comment_id, "Strong Mayor Powers": result})
    else:
        with Progress(console=console) as progress:
            task = progress.add_task("Estimating tokens...", total=total_documents)
            for document in documents:
                comment_id = document["comment_id"]
                file_path = document["file_path"]
                _, tokens = process_document(
                    file_path=file_path,
                    client=client,
                    model=args.model,
                    dry_run=True,
                )
                total_tokens += tokens
                progress.update(task, advance=1)

    if args.dry_run:
        logger.info(f"Total exact tokens required for this run: {total_tokens}")
    else:
        logger.info(f"Results written to {args.output_csv}")

    return 0

if __name__ == "__main__":
    sys.exit(main())
