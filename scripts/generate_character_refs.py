"""Generate canonical reference images for key characters using FLUX.

Creates one high-quality reference image per character in the Indian
traditional art style. These images are used by IP-Adapter to maintain
character consistency across all 315 videos.

Run once — takes ~15-20 min on Apple Silicon (MPS).
"""
import json
import os
import sys
import torch
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

CHARACTERS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "models", "characters"
)

# Detailed prompts for each character — designed for consistent appearance
CHARACTER_PROMPTS = {
    "rama": (
        "Portrait of Bhagwan Rama, Indian Rajput miniature painting style, "
        "young divine prince with blue-tinted skin, large lotus-shaped eyes, "
        "serene compassionate expression, wearing ornate golden mukut crown "
        "with peacock feather, golden earrings and necklaces, yellow silk dhoti "
        "with gold border, muscular build, holding divine bow Kodanda, "
        "sacred tilak on forehead, divine aura, rich jewel tones, "
        "intricate Indian ornamental details, masterful composition, 8K quality"
    ),
    "sita": (
        "Portrait of Mata Sita, Indian Rajput miniature painting style, "
        "beautiful divine woman with fair golden skin, large doe eyes, "
        "gentle graceful expression full of devotion, wearing red and gold "
        "silk saree with intricate zari work, ornate gold maang tikka, "
        "heavy gold necklaces and bangles, jasmine flowers in hair, "
        "sindoor in hair parting, sacred beauty, serene divine radiance, "
        "intricate Indian ornamental details, masterful composition, 8K quality"
    ),
    "hanuman": (
        "Portrait of Lord Hanuman, Indian Rajput miniature painting style, "
        "powerful vanara warrior with golden-orange fur, muscular divine body, "
        "fierce yet devotional expression, wearing golden armor on chest, "
        "red dhoti, golden crown, long curling tail, holding golden mace (gada), "
        "flying posture with one hand raised in blessing, glowing with divine energy, "
        "devoted loyal eyes, intricate Indian ornamental details, masterful composition, 8K quality"
    ),
    "lakshmana": (
        "Portrait of Prince Lakshmana, Indian Rajput miniature painting style, "
        "young handsome prince with fair skin, alert protective expression, "
        "slightly shorter than Rama, wearing white dhoti with gold border, "
        "silver crown, carrying a bow and quiver, golden armlets, "
        "devoted loyal eyes, always ready for battle, youthful energy, "
        "intricate Indian ornamental details, masterful composition, 8K quality"
    ),
    "king_dasharatha": (
        "Portrait of King Dasharatha, Indian Rajput miniature painting style, "
        "elderly dignified king with grey beard and wise tired eyes, "
        "wearing magnificent golden crown, white and gold royal robes, "
        "ornate gold necklaces and rings, seated on golden throne, "
        "regal but burdened expression, loving father, powerful ruler, "
        "intricate Indian ornamental details, masterful composition, 8K quality"
    ),
    "ravana": (
        "Portrait of King Ravana, Indian Rajput miniature painting style, "
        "powerful demon king with dark complexion, ten heads shown as shadow silhouettes, "
        "main face handsome but arrogant with sharp features, thick mustache, "
        "wearing black and gold royal armor, ruby-studded golden crown, "
        "heavy gold jewelry, fierce confident expression, muscular powerful build, "
        "Lanka palace in background, intricate Indian ornamental details, masterful composition, 8K quality"
    ),
    "bharata": (
        "Portrait of Prince Bharata, Indian Rajput miniature painting style, "
        "young prince with fair skin, humble devoted expression, "
        "wearing orange dhoti with gold border, simple gold crown, "
        "carrying Rama's sandals reverently, ascetic appearance despite royalty, "
        "matted hair showing his vow, tears of devotion in eyes, "
        "intricate Indian ornamental details, masterful composition, 8K quality"
    ),
    "queen_kaikeyi": (
        "Portrait of Queen Kaikeyi, Indian Rajput miniature painting style, "
        "beautiful queen wearing green silk saree with gold embroidery, "
        "emerald jewelry, elaborate hairstyle with gold pins, "
        "complex expression mixing pride and determination, fair complexion, "
        "sharp intelligent eyes, regal bearing, seated in anger chamber, "
        "intricate Indian ornamental details, masterful composition, 8K quality"
    ),
}


def generate_reference_image(char_name: str, prompt: str) -> str:
    """Generate a reference image for a character using FLUX.

    Returns the path to the saved image.
    """
    from src.flux_image_generator import FluxImageGenerator

    generator = FluxImageGenerator(num_inference_steps=4)

    print(f"  Generating reference for {char_name}...")
    images = generator.generate(
        prompt=prompt,
        negative_prompt="",
        width=1080,
        height=1920,
        num_images=1,
    )

    # Save reference image
    char_dir = os.path.join(CHARACTERS_DIR, char_name)
    os.makedirs(char_dir, exist_ok=True)
    ref_path = os.path.join(char_dir, "reference.png")
    images[0].save(ref_path)

    size_kb = os.path.getsize(ref_path) // 1024
    print(f"    Saved: {ref_path} ({size_kb} KB)")

    # Update character.json with reference path
    char_json_path = os.path.join(char_dir, "character.json")
    if os.path.exists(char_json_path):
        with open(char_json_path, "r") as f:
            char_data = json.load(f)
        char_data["reference_images"] = [ref_path]
        with open(char_json_path, "w") as f:
            json.dump(char_data, f, indent=2, ensure_ascii=False)
            f.write("\n")
        print(f"    Updated character.json")

    return ref_path


def main():
    print(f"Generating reference images for {len(CHARACTER_PROMPTS)} characters...")
    print(f"Output: {CHARACTERS_DIR}/*/reference.png\n")

    for char_name, prompt in CHARACTER_PROMPTS.items():
        generate_reference_image(char_name, prompt)
        print()

    print(f"Done! {len(CHARACTER_PROMPTS)} reference images generated.")
    print("These will be used by IP-Adapter for character consistency.")


if __name__ == "__main__":
    main()
