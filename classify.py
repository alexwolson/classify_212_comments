import os
import re
from collections import Counter
import enum

import argparse
import sys
import csv
from pathlib import Path
from rich.console import Console
from rich.progress import Progress

# Google GenAI imports
from google import genai
from google.genai import types

# Enum for response classification
class StrongMayorPowersClassification(enum.Enum):
    PRESENT = "present"
    ABSENT = "absent"

def get_file_mime_type(file_path: Path) -> str:
    """Get MIME type for supported file formats."""
    file_extension = file_path.suffix.lower()
    
    mime_types = {
        '.pdf': 'application/pdf',
        '.txt': 'text/plain',
        '.text': 'text/plain',
        '.html': 'text/html',
        '.htm': 'text/html',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.rtf': 'application/rtf'
    }
    
    return mime_types.get(file_extension, 'application/octet-stream')

def is_supported_file(file_path: Path) -> bool:
    """Check if file format is supported."""
    supported_extensions = {'.pdf', '.txt', '.text', '.html', '.htm', '.docx', '.rtf'}
    return file_path.suffix.lower() in supported_extensions

def count_tokens_estimate(file_path: Path) -> int:
    """Estimate tokens for a file for dry runs."""
    # Simple estimation based on file size
    # Gemini models typically have ~3-4 characters per token
    file_size = file_path.stat().st_size
    return file_size // 3

def get_supported_extensions():
    """Return a list of supported file extensions."""
    return ['.pdf', '.txt', '.text', '.html', '.htm', '.docx', '.rtf']

def construct_document_prompt() -> str:
    """Construct the prompt for direct document analysis."""
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

def main():
    console = Console()

    parser = argparse.ArgumentParser(description="Process documents to detect references to Strong Mayor Powers.")
    parser.add_argument("input_path", type=str, help="Directory containing document files (PDF, TXT, HTML, DOCX, RTF) with comments.")
    parser.add_argument("--dry-run", action="store_true", help="If provided, only estimate token usage without calling the Google Gemini API.")
    parser.add_argument("--gemini-api-key", type=str, default=None, help="Gemini API key. If not set, must be set as GEMINI_API_KEY environment variable.")
    parser.add_argument("--output-csv", type=str, default="results.csv", help="Output CSV file to store results.")
    parser.add_argument("--model", type=str, default="gemini-2.5-flash", help="Model name to use for the Google Gemini API calls.")
    args = parser.parse_args()

    # Set API key and initialize client only if not doing a dry run
    if not args.dry_run:
        api_key = args.gemini_api_key or os.environ.get("GEMINI_API_KEY")
        if not api_key:
            console.log("[red]Error: No Gemini API key provided and not found in environment variables.[/red]")
            console.log("[red]Set GEMINI_API_KEY environment variable or use --gemini-api-key option.[/red]")
            sys.exit(1)

        # Initialize Google GenAI client
        client = genai.Client(api_key=api_key)

    input_path = Path(args.input_path)
    if not input_path.exists():
        console.log(f"[red]Error: {input_path} does not exist.[/red]")
        sys.exit(1)
    
    if not input_path.is_dir():
        console.log(f"[red]Error: {input_path} must be a directory containing document files.[/red]")
        console.log("[red]JSON input is no longer supported. Please provide a directory of document files.[/red]")
        sys.exit(1)

    # Load already processed comments if output file exists
    processed_ids = set()
    output_file = Path(args.output_csv)
    if output_file.is_file():
        console.log("[info]Resuming from existing output file.")
        with open(output_file, "r", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                processed_ids.add(row["Comment ID"])

    # Load documents from directory
    console.log("[info]Processing directory input.")
    supported_extensions = get_supported_extensions()
    
    # Find all supported files in the directory
    supported_files = []
    for ext in supported_extensions:
        supported_files.extend(input_path.glob(f"*{ext}"))
    
    if not supported_files:
        console.log(f"[red]Error: No supported files found in {input_path}[/red]")
        console.log(f"[red]Supported file types: {', '.join(supported_extensions)}[/red]")
        sys.exit(1)
    
    console.log(f"[info]Found {len(supported_files)} supported files: {', '.join(supported_extensions)}[/info]")
    
    # Prepare document data for processing
    documents = []
    for file_path in supported_files:
        if not is_supported_file(file_path):
            console.log(f"[yellow]Skipping unsupported file: {file_path.name}[/yellow]")
            continue
            
        # Extract comment ID from filename (remove extension)
        comment_id = file_path.stem
        documents.append({
            "comment_id": comment_id,
            "file_path": file_path
        })

    total_documents = len(documents)

    console.log(f"[info]Found a total of {total_documents} documents to process.")
    console.log("[info]Starting processing of documents...")

    total_tokens = 0

    with open(output_file, "a", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        if not output_file.is_file() or output_file.stat().st_size == 0:
            writer.writerow(["Comment ID", "Strong Mayor Powers"])

        with Progress(console=console) as progress:
            task = progress.add_task("Processing documents...", total=total_documents)

            for document in documents:
                comment_id = document["comment_id"]
                if comment_id in processed_ids:
                    progress.update(task, advance=1)
                    continue

                file_path = document["file_path"]

                # Estimate tokens for dry run
                if args.dry_run:
                    estimated_tokens = count_tokens_estimate(file_path)
                    total_tokens += estimated_tokens
                    result = "(dry-run)"
                else:
                    # Process document with new API
                    try:
                        # Read file as bytes
                        file_bytes = file_path.read_bytes()
                        mime_type = get_file_mime_type(file_path)
                        
                        # Create document part
                        document_part = types.Part.from_bytes(
                            data=file_bytes,
                            mime_type=mime_type
                        )
                        
                        # Create prompt part
                        prompt_part = construct_document_prompt()
                        
                        # Make API call with structured response
                        response = client.models.generate_content(
                            model=args.model,
                            contents=[document_part, prompt_part],
                            config={
                                'response_mime_type': 'text/x.enum',
                                'response_schema': StrongMayorPowersClassification,
                            }
                        )

                        # Parse response
                        answer = response.text.strip().lower()
                        if answer in ["present", "absent"]:
                            result = answer
                        else:
                            # Fallback parsing for unexpected responses
                            match = re.search(r"\b(present|absent)\b", answer)
                            if match:
                                result = match.group(1)
                            else:
                                result = "absent"
                                console.log(f"[yellow]Warning: Unexpected response for document {comment_id}: {answer}[/yellow]")
                        
                        console.log(f"[green]Successfully processed {file_path.name} -> {result}[/green]")
                        
                    except Exception as e:
                        console.log(f"[red]Error processing {file_path.name}: {e}[/red]")
                        result = "absent"  # Default to absent on error

                # Update progress bar
                progress.update(
                    task,
                    advance=1,
                    description=f"Last: Document {comment_id} -> {result}"
                )

                if not args.dry_run:
                    writer.writerow([comment_id, result])

    if args.dry_run:
        console.log(f"[blue]Total estimated tokens required: {total_tokens}[/blue]")
    else:
        console.log(f"[green]Results written to {args.output_csv}[/green]")

if __name__ == "__main__":
    main()
