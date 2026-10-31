"""Crack an English Caesar message with letter-frequency analysis."""

import argparse
from collections import Counter
import json
from pathlib import Path


ENGLISH = dict(zip("ABCDEFGHIJKLMNOPQRSTUVWXYZ", (
    8.167, 1.492, 2.782, 4.253, 12.702, 2.228, 2.015, 6.094, 6.966,
    0.153, 0.772, 4.025, 2.406, 6.749, 7.507, 1.929, 0.095, 5.987,
    6.327, 9.056, 2.758, 0.978, 2.360, 0.150, 1.974, 0.074,
)))


def caesar(text: str, shift: int) -> str:
    result = []
    for char in text:
        if "A" <= char <= "Z":
            result.append(chr((ord(char) - 65 + shift) % 26 + 65))
        elif "a" <= char <= "z":
            result.append(chr((ord(char) - 97 + shift) % 26 + 97))
        else:
            result.append(char)
    return "".join(result)


def crack(ciphertext: str) -> list[dict]:
    counts = Counter(c for c in ciphertext.upper() if "A" <= c <= "Z")
    total = sum(counts.values())
    if not total:
        raise ValueError("The message must contain English letters.")
    ranked = []
    for shift in range(26):
        plain = caesar(ciphertext, -shift)
        observed = Counter(c for c in plain.upper() if "A" <= c <= "Z")
        score = sum((observed[c] - total * freq / 100) ** 2 / (total * freq / 100)
                    for c, freq in ENGLISH.items())
        ranked.append({"shift": shift, "chi_squared": score, "plaintext": plain})
    return sorted(ranked, key=lambda row: row["chi_squared"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ciphertext", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    ciphertext = args.ciphertext.read_text(encoding="utf-8")
    ranked = crack(ciphertext)
    counts = Counter(c for c in ciphertext.upper() if "A" <= c <= "Z")
    most_common = counts.most_common(1)[0][0]
    result = {"method": "Minimum chi-squared score across 26 letter-frequency distributions",
              "letter_count": sum(counts.values()),
              "most_common_cipher_letter": most_common,
              "single_E_estimate": (ord(most_common) - ord("E")) % 26,
              "best_shift": ranked[0]["shift"], "candidates": ranked,
              "limitation": "Short or unusual English messages can produce the wrong rank."}
    rendered = json.dumps(result, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(f"Best shift: {ranked[0]['shift']}")
    print(ranked[0]["plaintext"])


if __name__ == "__main__":
    main()
