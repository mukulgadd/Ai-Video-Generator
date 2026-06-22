"""Generate channel branding assets using FLUX.

Creates:
1. Profile picture (800x800) — Logo mark
2. YouTube banner (2560x1440) — Channel art

Usage:
    python scripts/generate_branding.py
"""

import os
import sys

sys.path.insert(0, ".")

from src.flux_image_generator import FluxImageGenerator


def main():
    os.makedirs("output/branding", exist_ok=True)
    gen = FluxImageGenerator(num_inference_steps=4)

    print("=" * 50)
    print("Generating Sanatan Rahasya branding assets")
    print("=" * 50)

    # 1. Profile picture / Logo
    print("\n[1/2] Generating profile picture (logo)...")
    logo_prompt = (
        "minimalist logo design for a Hindu mythology YouTube channel, "
        "golden Om symbol integrated with an ancient scroll or book, "
        "saffron and gold color palette on dark maroon background, "
        "clean vector style, symmetrical, sacred geometry accents, "
        "premium luxury feel, no text, centered composition, "
        "dark background, glowing golden light emanating from the Om, "
        "Indian traditional art inspired, 8k quality"
    )
    logo_images = gen.generate(
        prompt=logo_prompt,
        negative_prompt="",
        width=800,
        height=800,
        num_images=1,
    )
    logo_images[0].save("output/branding/logo_800x800.png")
    print("  Saved: output/branding/logo_800x800.png")

    # 2. YouTube channel banner
    print("\n[2/2] Generating YouTube banner...")
    banner_prompt = (
        "wide cinematic banner for Hindu mythology YouTube channel, "
        "ancient Indian temple architecture silhouette against dramatic sunset sky, "
        "saffron orange and deep gold color palette, sacred geometry patterns, "
        "mystical fog, divine light rays from above, "
        "ornate gold border frame, premium feel, "
        "dark maroon and saffron gradient, no text, no characters, "
        "panoramic landscape composition, Indian traditional art style, 8k quality"
    )
    banner_images = gen.generate(
        prompt=banner_prompt,
        negative_prompt="",
        width=2560,
        height=1440,
        num_images=1,
    )
    banner_images[0].save("output/branding/banner_2560x1440.png")
    print("  Saved: output/branding/banner_2560x1440.png")

    print("\n" + "=" * 50)
    print("Done! Assets in output/branding/")
    print("  - logo_800x800.png → Use as YouTube/Instagram profile pic")
    print("  - banner_2560x1440.png → Use as YouTube channel banner")
    print("=" * 50)


if __name__ == "__main__":
    main()
