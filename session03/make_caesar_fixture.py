"""Create a labeled practice message. The slides give no ciphertext."""

import json
from pathlib import Path

from caesar import caesar, crack


TEXT = (
    "The students use a small application to read their grades and comments. "
    "A teacher can enter a grade after each lesson. The application keeps the records in a database. "
    "The team must protect the private comments before a person can copy the database. "
    "A secret key changes the readable text into ciphertext. The same key changes the ciphertext back into readable text. "
    "Keep the key separate from the data. Use a new nonce for each message. "
    "Check the authentication tag before you use a comment. Reject a comment if the check fails. "
    "Encryption helps protect stored comments, but the application must also check who can read each record.\n"
)


def main():
    out = Path(__file__).parent / "results"
    out.mkdir(exist_ok=True)
    (out / "caesar_plaintext.txt").write_text(TEXT)
    (out / "caesar_ciphertext.txt").write_text(caesar(TEXT, 11))
    recovered = []
    for shift in range(26):
        result = crack(caesar(TEXT, shift))[0]
        assert result["shift"] == shift and result["plaintext"] == TEXT
        recovered.append(shift)
    assert caesar(caesar("Hello, Zz! 123 中文", 3), -3) == "Hello, Zz! 123 中文"
    try:
        crack("123 !")
    except ValueError:
        no_letters_rejected = True
    else:
        raise AssertionError("The empty frequency table was accepted.")
    summary = {"source": "Original practice text. No instructor ciphertext appears in the supplied slides.",
               "fixture_shift": 11, "all_fixture_shifts_recovered": recovered,
               "round_trip_case_punctuation_unicode": True,
               "no_letters_rejected": no_letters_rejected}
    (out / "caesar_verification.json").write_text(json.dumps(summary, indent=2) + "\n")
    print("The practice text was recovered for all 26 shifts.")


if __name__ == "__main__":
    main()
