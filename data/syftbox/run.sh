from syftbox.lib import Client
from collections import Counter
import json


def main() -> None:
    client = Client.load()

    # Adjust this if the owner uses a different layout
    dataset_root = client.my_datasite / "semi-public" / "team-project" / "data"
    patterns_path = dataset_root / "patterns.json"

    with patterns_path.open("r", encoding="utf-8") as f:
        patterns = json.load(f)

    protoss_patterns = {
        pid: entry
        for pid, entry in patterns.items()
        if (entry.get("race") or "").lower() == "protoss"
    }

    breakdown = Counter(
        (entry.get("strategy_type") or "unknown")
        for entry in protoss_patterns.values()
    )

    examples = []
    for pid, entry in list(protoss_patterns.items())[:10]:
        sig = entry.get("signature", {}) or {}
        opening_seq = sig.get("opening_sequence", []) or []
        units = [step.get("unit") for step in opening_seq]

        examples.append(
            {
                "pattern_id": pid,
                "strategy_type": entry.get("strategy_type"),
                "sample_count": entry.get("sample_count"),
                "confidence": entry.get("confidence"),
                "opening_units": units,
            }
        )

    result = {
        "protoss_count": len(protoss_patterns),
        "strategy_breakdown": dict(breakdown),
        "examples": examples,
    }

    output_path = client.my_datasite / "public" / "protoss_summary.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    print(f"[App] Summary written to: {output_path}")


if __name__ == "__main__":
    main()
