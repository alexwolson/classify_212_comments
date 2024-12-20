import argparse
from rich.console import Console
from rich.progress import Progress
import sys
import json
from pathlib import Path
from transformers import RobertaTokenizerFast, TFRobertaForSequenceClassification, pipeline
import pandas as pd

def main():
    console = Console()

    parser = argparse.ArgumentParser(description="Classify emotions in comment responses to Bill 212.")
    parser.add_argument("directory", type=str, help="Directory containing JSON files with comments.")
    parser.add_argument("--output-csv", type=str, default="results.csv", help="Output CSV file to store results.")
    args = parser.parse_args()

    data_dir = Path(args.directory)
    if not data_dir.is_dir():
        console.log(f"[red]Error: {data_dir} is not a valid directory.[/red]")
        sys.exit(1)

    # Count total comments
    total_comments = 0
    json_files = list(data_dir.glob("*.json"))
    for json_file in json_files:
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            total_comments += len(data)

    console.log(f"[info]Found {len(json_files)} files with a total of {total_comments} comments to process.")

    console.log("[info]Loading emotion classification model...")

    emotion = pipeline(task="text-classification", model="SamLowe/roberta-base-go_emotions", top_k=None, truncation=True)
    
    console.log("[info]Classifying emotions in comments...")

    with Progress() as progress:
        task = progress.add_task("[cyan]Processing...", total=total_comments)

        results = []

        for json_file in json_files:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                for comment_id, comment_info in data.items():
                    comment_text = comment_info.get("comment", "")

                    # Classify emotion
                    emotions = emotion(comment_text)[0]

                    result = {
                        "comment_id": comment_id,
                    }

                    for response in emotions:
                        result[response["label"]] = response["score"]

                    results.append(result)

                    progress.update(task, advance=1)

    console.log("[info]Writing results to CSV...")
    df = pd.DataFrame(results)
    df.to_csv(args.output_csv, index=False)

if __name__ == "__main__":
    main()