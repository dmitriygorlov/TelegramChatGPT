import json

from convert_dataset import convert


def test_legacy_dataset_conversion(tmp_path):
    source, target = tmp_path / "old.jsonl", tmp_path / "chat.jsonl"
    source.write_text(json.dumps({"prompt": "Q: Hello ->", "completion": " Hi###"}))
    convert(source, target)
    messages = json.loads(target.read_text())["messages"]
    assert messages == [{"role": "user", "content": "Hello"}, {"role": "assistant", "content": "Hi"}]
