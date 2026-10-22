"""Compare the same raw image pixels under AES-ECB and AES-GCM."""

import json
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def block_stats(data):
    blocks = [data[i:i + 16] for i in range(0, len(data), 16)]
    return {"blocks": len(blocks), "unique_blocks": len(set(blocks)),
            "duplicate_blocks": len(blocks) - len(set(blocks))}


def main():
    out = Path(__file__).parent / "results"
    out.mkdir(exist_ok=True)
    # The input is an original lab fixture. It contains large repeated areas.
    original = Image.new("RGB", (384, 288), "white")
    draw = ImageDraw.Draw(original)
    draw.rectangle((32, 32, 351, 255), fill=(25, 58, 90))
    draw.rectangle((48, 48, 335, 239), fill=(225, 236, 243))
    draw.ellipse((120, 64, 264, 232), fill=(18, 25, 36))
    draw.ellipse((144, 112, 240, 216), fill="white")
    draw.ellipse((150, 90, 166, 106), fill="white")
    draw.ellipse((218, 90, 234, 106), fill="white")
    draw.polygon(((180, 111), (204, 111), (192, 128)), fill=(255, 178, 48))
    draw.rectangle((136, 224, 176, 239), fill=(255, 178, 48))
    draw.rectangle((208, 224, 248, 239), fill=(255, 178, 48))
    raw = original.tobytes()
    key = AESGCM.generate_key(bit_length=256)
    padder = padding.PKCS7(128).padder()
    padded = padder.update(raw) + padder.finalize()
    enc = Cipher(algorithms.AES(key), modes.ECB()).encryptor()
    ecb = enc.update(padded) + enc.finalize()
    dec = Cipher(algorithms.AES(key), modes.ECB()).decryptor()
    decrypted = dec.update(ecb) + dec.finalize()
    unpadder = padding.PKCS7(128).unpadder()
    assert unpadder.update(decrypted) + unpadder.finalize() == raw
    nonce = os.urandom(12)
    aad = b"Session03:RGB:384x288:v1"
    aes = AESGCM(key)
    gcm = aes.encrypt(nonce, raw, aad)
    recovered = aes.decrypt(nonce, gcm, aad)
    assert recovered == raw
    changed = bytearray(gcm)
    changed[0] ^= 1
    try:
        aes.decrypt(nonce, bytes(changed), aad)
    except InvalidTag:
        tamper_rejected = True
    else:
        raise AssertionError("GCM accepted changed ciphertext.")
    views = [original, Image.frombytes("RGB", original.size, ecb[:len(raw)]),
             Image.frombytes("RGB", original.size, gcm[:-16])]
    names = ["original.png", "ecb_pixels.png", "gcm_pixels.png"]
    labels = ["Original image", "AES-ECB: repeated blocks", "AES-GCM: no visible shape"]
    board = Image.new("RGB", (384 * 3 + 48, 360), (246, 249, 252))
    board_draw = ImageDraw.Draw(board)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 18)
    except OSError:
        font = ImageFont.load_default(size=18)
    for i, (view, name, label) in enumerate(zip(views, names, labels)):
        view.save(out / name)
        board.paste(view, (12 + 396 * i, 54))
        board_draw.text((12 + 396 * i, 20), label, font=font, fill=(25, 58, 90))
    board.save(out / "ecb_gcm_comparison.png")
    Image.frombytes("RGB", original.size, recovered).save(out / "gcm_recovered.png")
    # The complete encrypted outputs include the tag, nonce, and dimensions.
    (out / "ecb_ciphertext.bin").write_bytes(ecb)
    (out / "gcm_ciphertext_and_tag.bin").write_bytes(gcm)
    metadata = {"width": 384, "height": 288, "pixel_mode": "RGB", "nonce_hex": nonce.hex(),
                "aad_ascii": aad.decode(), "tag_bytes": 16,
                "key": "Ephemeral. Used for verification, then discarded. Never exported."}
    (out / "image_metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    result = {"original": block_stats(raw), "ecb_visible_bytes": block_stats(ecb[:len(raw)]),
              "gcm_visible_bytes": block_stats(gcm[:-16]), "ecb_round_trip": True,
              "gcm_round_trip": True, "gcm_tamper_rejected": tamper_rejected,
              "raw_pixel_bytes": len(raw), "ecb_bytes_with_padding": len(ecb),
              "gcm_bytes_with_tag": len(gcm),
              "preview_note": "PNG previews display raw ciphertext as RGB pixels. Headers are not encrypted."}
    (out / "image_results.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
