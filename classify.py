import os
import json
import tiktoken
import argparse
import sys
import re
import csv
from pathlib import Path
from rich.console import Console
from rich.progress import Progress

def count_tokens(text: str, model: str = "gpt-4o-mini") -> int:
    encoding = tiktoken.encoding_for_model(model)
    return len(encoding.encode(text))

def construct_full_prompt(comment_text: str, bill_description: str, system_prompt: str) -> str:
    user_prompt = f"""
The bill details:
{bill_description}

Comment:
{comment_text}

Based on the above, is the commenter for or against the proposed bill?
Return either "for" or "against".
"""
    return system_prompt.strip() + "\n" + user_prompt.strip()

def main():
    console = Console()

    parser = argparse.ArgumentParser(description="Process comments to determine if they are for or against the bill.")
    parser.add_argument("directory", type=str, help="Directory containing JSON files with comments.")
    parser.add_argument("--dry-run", action="store_true", help="If provided, only calculate total tokens without calling the OpenAI API.")
    parser.add_argument("--openai-api-key", type=str, default=None, help="OpenAI API key. If not set, must be set as environment variable.")
    parser.add_argument("--output-csv", type=str, default="results.csv", help="Output CSV file to store results.")
    parser.add_argument("--model", type=str, default="gpt-4o-mini", help="Model name to use for the OpenAI API calls.")
    args = parser.parse_args()

    # Set API key
    api_key = args.openai_api_key or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        console.log("[red]Error: No OpenAI API key provided and not found in environment variables.[/red]")
        sys.exit(1)

    # Lazy import of openai since user had previous code
    from openai import OpenAI
    client = OpenAI(api_key=api_key)

    data_dir = Path(args.directory)
    if not data_dir.is_dir():
        console.log(f"[red]Error: {data_dir} is not a valid directory.[/red]")
        sys.exit(1)

    bill_description = """
    The proposed legislation includes amendments that expedite the construction of priority highway projects,
    adjust expropriation procedures for broadband and highway infrastructure, and impose additional oversight
    and restrictions regarding bicycle lanes at the municipal level. Broadly, the bill aims to streamline
    infrastructure development for highways and broadband networks, sometimes overriding municipal bylaws or
    environmental assessments, while also increasing provincial control over bicycle lane installations and removals.
    """

    system_prompt = f"""
    You are analyzing public comments related to a proposed bill. The bill aims to streamline and expedite the
    construction of priority highways, adjust expropriation procedures for broadband and highway infrastructure,
    and impose additional oversight and restrictions regarding bicycle lanes at the municipal level.

    Your job is to read each comment carefully and determine whether the commenter is generally "for"
    or "against" the bill. Consider whether the comment supports or opposes the changes described:
    e.g., supporting accelerated highway construction, expropriation changes, or more provincial control over
    bike lanes might be "for," while opposing these measures or criticizing them strongly would be "against."

    Return a single machine-readable result for each comment: either "for" or "against".
    """

    # Count total comments
    total_comments = 0
    json_files = list(data_dir.glob("*.json"))
    for json_file in json_files:
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            total_comments += len(data)

    console.log(f"[info]Found {len(json_files)} files with a total of {total_comments} comments to process.")
    console.log("[info]Starting processing of comments...")

    total_tokens = 0
    results = []

    with Progress(console=console) as progress:
        task = progress.add_task("Processing comments...", total=total_comments)
        # We'll dynamically update the task description to show last processed comment/result

        for json_file in json_files:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            for comment_id, comment_info in data.items():
                comment_text = comment_info.get("comment", "")
                full_prompt = construct_full_prompt(comment_text, bill_description, system_prompt)

                # Count tokens
                prompt_tokens = count_tokens(full_prompt, model=args.model)
                total_tokens += prompt_tokens

                if not args.dry_run:
                    response = client.chat.completions.create(
                        model=args.model,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {
                                "role": "user",
                                "content": f"The bill details:\n{bill_description}\n\nComment:\n{comment_text}\n\nBased on the above, is the commenter for or against the proposed bill? Return either 'for' or 'against'."
                            }
                        ],
                        temperature=0
                    )

                    answer = response.choices[0].message.content.strip().lower()
                    match = re.search(r"\b(for|against)\b", answer)
                    if match:
                        result = match.group(1)
                    else:
                        result = "unknown"
                        console.log(f"[yellow]Warning: Unexpected response for comment {comment_id} in {json_file.name}: {answer}[/yellow]")
                else:
                    # Dry run: no API call, just show that we would have processed
                    result = "(dry-run)"

                # Update progress bar description with last processed comment and result
                progress.update(
                    task,
                    advance=1,
                    description=f"Last: {json_file.name}/{comment_id} -> {answer}"
                )

                if not args.dry_run and result in ["for", "against"]:
                    results.append((json_file.name, comment_id, result))

    if args.dry_run:
        console.log(f"[blue]Total estimated tokens required: {total_tokens}[/blue]")
    else:
        with open(args.output_csv, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["filename", "comment_id", "stance"])
            for r in results:
                writer.writerow(r)
        console.log(f"[green]Results written to {args.output_csv}[/green]")

if __name__ == "__main__":
    main()

