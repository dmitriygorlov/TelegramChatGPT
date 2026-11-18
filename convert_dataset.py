"""Convert the original prompt/completion JSONL to chat fine-tuning JSONL offline."""
import argparse
import json
from pathlib import Path


def convert(source, destination):
    rows = []
    for line in Path(source).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        prompt = row["prompt"].removesuffix(" ->").removeprefix("Q: ").strip()
        answer = row["completion"].removesuffix("###").strip()
        if not prompt or not answer:
            raise ValueError("Training examples must have a prompt and completion")
        rows.append({"messages": [{"role": "user", "content": prompt},
                                  {"role": "assistant", "content": answer}]})
    Path(destination).write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source")
    parser.add_argument("destination")
    args = parser.parse_args()
    convert(args.source, args.destination)
