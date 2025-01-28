import os
import json
import re

import tiktoken
import argparse
import sys
import csv
from pathlib import Path
from rich.console import Console
from rich.progress import Progress

def count_tokens(text: str, model: str = "gpt-4o-mini") -> int:
    encoding = tiktoken.encoding_for_model(model)
    return len(encoding.encode(text))

def construct_full_prompt(comment_text: str, system_prompt: str) -> str:
    user_prompt = f"""
Comment:
{comment_text}

Based on the above comment and its context, determine the overall stance of the commenter regarding the described issue. Your response must always be one of the following:

1. "for" - The comment clearly supports the legislation or its goals.
2. "against" - The comment clearly opposes the legislation or its goals.
3. "unclear" - Use only if the comment provides no clear indication of support or opposition, or discusses unrelated topics.

Return exactly one word: "for", "against", or "unclear". Do not include any additional explanation or text in your response.
"""
    return system_prompt.strip() + "\n" + user_prompt.strip()

def main():
    console = Console()

    parser = argparse.ArgumentParser(description="Process comments to determine attitudes.")
    parser.add_argument("input_file", type=str, help="File containing JSON data with comments associated with multiple ERO numbers.")
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

    input_file = Path(args.input_file)
    if not input_file.is_file():
        console.log(f"[red]Error: {input_file} is not a valid file.[/red]")
        sys.exit(1)

    system_prompt = """
You are analyzing public comments submitted to the Environmental Registry of Ontario (ERO). The ERO is a platform where public feedback is collected on proposed Ontario legislation as part of the consultation process. Each comment corresponds to a specific ERO number, which identifies the related legislation.

Your task is to determine the **overall stance** of the commenter based on the content provided. The stance must always be exactly one of the following three options:

1. "for" - The comment explicitly supports the legislation or its goals.
2. "against" - The comment explicitly opposes the legislation or its goals.
3. "unclear" - Use this only if the comment provides no clear indication of support or opposition, or discusses unrelated topics.

**Guidelines**:
- Always return a single word: "for," "against," or "unclear." Do not include explanations or additional text in your response.
- Remain impartial and base your classification solely on the content of the comment. Do not infer intent beyond what is explicitly stated.
- If a comment is vague, incomplete, or references unrelated topics, mark it as "unclear."
- When a comment addresses multiple aspects of the legislation, base your decision on the dominant sentiment. If no dominant sentiment is apparent, choose "unclear."
- Consider spelling errors, informal language, or grammatical issues as part of normal analysis and do not discount these comments unless they are incomprehensible.

Examples:
- Comment: "I fully agree with these changes to reduce traffic delays." → **for**
- Comment: "This legislation will harm small businesses." → **against**
- Comment: "I don't understand this proposal." → **unclear**
"""

    # Load already processed comments if output file exists
    processed_ids = set()
    output_file = Path(args.output_csv)
    if output_file.is_file():
        console.log("[info]Resuming from existing output file.")
        with open(output_file, "r", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                processed_ids.add(row["Comment ID"])

    # Load comments
    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    total_comments = len(data)

    console.log(f"[info]Found a total of {total_comments} comments to process.")
    console.log("[info]Starting processing of comments...")

    total_tokens = 0

    with open(output_file, "a", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        if not output_file.is_file() or output_file.stat().st_size == 0:
            writer.writerow(["Comment ID", "Stance"])

        with Progress(console=console) as progress:
            task = progress.add_task("Processing comments...", total=total_comments)

            for entry in data:
                comment_id = entry["comment_id"]
                if comment_id in processed_ids:
                    progress.update(task, advance=1)
                    continue

                comment_text = entry.get("comment", "")

                full_prompt = construct_full_prompt(comment_text, system_prompt)

                # Count tokens
                prompt_tokens = count_tokens(full_prompt, model=args.model)
                total_tokens += prompt_tokens

                if not args.dry_run:
                    response = client.chat.completions.create(
                        model=args.model,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": full_prompt}
                        ],
                        temperature=0
                    )

                    answer = response.choices[0].message.content.strip().lower()
                    match = re.search(r"\b(for|against|unclear)\b", answer)
                    if match:
                        result = match.group(1)
                    else:
                        result = "unclear"
                        console.log(f"[yellow]Warning: Unexpected response for comment {comment_id}: {answer}[/yellow]")
                else:
                    result = "(dry-run)"

                # Update progress bar
                progress.update(
                    task,
                    advance=1,
                    description=f"Last: Comment ID {comment_id} -> {result}"
                )

                if not args.dry_run:
                    writer.writerow([comment_id, result])

    if args.dry_run:
        console.log(f"[blue]Total estimated tokens required: {total_tokens}[/blue]")
    else:
        console.log(f"[green]Results written to {args.output_csv}[\green]")

if __name__ == "__main__":
    main()
