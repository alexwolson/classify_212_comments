import argparse
import csv
import json
import os
import random
import sys
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description="Validate the classification results.")
    parser.add_argument("directory", type=str, help="Directory containing JSON files with comments.")
    parser.add_argument("results_csv", type=str, help="CSV file with model results.")
    parser.add_argument("num_samples", type=int, help="Number of random samples to validate.")
    parser.add_argument("--output-csv", type=str, default="validation_results.csv", help="Where to store the validation responses.")
    args = parser.parse_args()

    data_dir = Path(args.directory)
    if not data_dir.is_dir():
        print(f"Error: {data_dir} is not a valid directory.")
        sys.exit(1)

    # Load the model results
    # results.csv should have: filename,comment_id,stance
    model_results = {}
    with open(args.results_csv, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # key by filename and comment_id
            key = (row["filename"], row["comment_id"])
            model_results[key] = row["stance"]

    # Load all comments from the directory
    comments = []
    for json_file in data_dir.glob("*.json"):
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            for comment_id, comment_info in data.items():
                comment_text = comment_info.get("comment", "")
                key = (json_file.name, comment_id)
                if key in model_results:
                    comments.append((json_file.name, comment_id, comment_text, model_results[key]))

    if len(comments) == 0:
        print("No comments found or no matching results in the given directory and results CSV.")
        sys.exit(1)

    # If the requested number of samples is more than available comments, cap it
    num_samples = min(args.num_samples, len(comments))

    # Randomly sample the comments
    random.shuffle(comments)
    sampled_comments = comments[:num_samples]

    # Collect user responses
    user_responses = []

    print(f"Presenting {num_samples} random comments for validation.")
    print("Please type 'for' or 'against' when prompted. Press Ctrl+C to quit.\n")

    for (filename, comment_id, comment_text, model_stance) in sampled_comments:
        print("Comment:\n" + comment_text.strip() + "\n")
        user_input = None
        while user_input not in ["for", "against"]:
            user_input = input("Your classification (for/against): ").strip().lower()
            if user_input not in ["for", "against"]:
                print("Please type 'for' or 'against'.")

        # Store the response
        user_responses.append((filename, comment_id, model_stance, user_input))

        print("-" * 60)

    # Calculate agreement
    total = len(user_responses)
    agree_count = sum(1 for r in user_responses if r[2] == r[3])
    agreement_percentage = (agree_count / total) * 100 if total > 0 else 0

    print(f"\nValidation complete. Agreement with model: {agreement_percentage:.2f}%")

    # Write results to a CSV
    with open(args.output_csv, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["filename", "comment_id", "model_stance", "user_stance", "agrees"])
        for (filename, comment_id, model_stance, user_stance) in user_responses:
            agrees = (model_stance == user_stance)
            writer.writerow([filename, comment_id, model_stance, user_stance, agrees])

    print(f"User responses and validation results have been saved to {args.output_csv}")

if __name__ == "__main__":
    main()

