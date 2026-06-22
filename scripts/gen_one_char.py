"""Generate reference image for ONE character at a time.

Usage: python scripts/gen_one_char.py rama
       python scripts/gen_one_char.py sita
       etc.

This uses less memory than generating all 8 at once.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

CHARACTERS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "models", "characters"
)

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
        "wearing white dhoti with gold border, silver crown, carrying a bow and quiver, "
        "golden armlets, devoted loyal eyes, youthful energy, "
        "intricate Indian ornamental details, masterful composition, 8K quality"
    ),
    "king_dasharatha": (
        "Portrait of King Dasharatha, Indian Rajput miniature painting style, "
        "elderly dignified king with grey beard and wise tired eyes, "
        "wearing magnificent golden crown, white and gold royal robes, "
        "ornate gold necklaces and rings, regal but burdened expression, "
        "intricate Indian ornamental details, masterful composition, 8K quality"
    ),
    "ravana": (
        "Portrait of King Ravana, Indian Rajput miniature painting style, "
        "powerful demon king with dark complexion, handsome but arrogant face "
        "with sharp features, thick mustache, wearing black and gold royal armor, "
        "ruby-studded golden crown, heavy gold jewelry, fierce confident expression, "
        "muscular powerful build, intricate Indian ornamental details, masterful composition, 8K quality"
    ),
    "bharata": (
        "Portrait of Prince Bharata, Indian Rajput miniature painting style, "
        "young prince with fair skin, humble devoted expression, "
        "wearing orange dhoti with gold border, simple gold crown, "
        "carrying sandals reverently, ascetic appearance despite royalty, "
        "intricate Indian ornamental details, masterful composition, 8K quality"
    ),
    "queen_kaikeyi": (
        "Portrait of Queen Kaikeyi, Indian Rajput miniature painting style, "
        "beautiful queen wearing green silk saree with gold embroidery, "
        "emerald jewelry, elaborate hairstyle with gold pins, "
        "complex expression mixing pride and determination, fair complexion, "
        "sharp intelligent eyes, regal bearing, "
        "intricate Indian ornamental details, masterful composition, 8K quality"
    ),
}


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/gen_one_char.py <character_name>")
        print(f"Available: {', '.join(CHARACTER_PROMPTS.keys())}")
        sys.exit(1)

    char_name = sys.argv[1].lower()
    if char_name not in CHARACTER_PROMPTS:
        print(f"Unknown character: {char_name}")
        print(f"Available: {', '.join(CHARACTER_PROMPTS.keys())}")
        sys.exit(1)

    prompt = CHARACTER_PROMPTS[char_name]
    print(f"Generating reference image for: {char_name}")
    print(f"Prompt: {prompt[:80]}...")

    from src.flux_image_generator import FluxImageGenerator

    generator = FluxImageGenerator(num_inference_steps=4)
    images = generator.generate(
        prompt=prompt,
        negative_prompt="",
        width=768,
        height=1344,
        num_images=1,
    )

    # Save
    char_dir = os.path.join(CHARACTERS_DIR, char_name)
    os.makedirs(char_dir, exist_ok=True)
    ref_path = os.path.join(char_dir, "reference.png")
    images[0].save(ref_path)

    size_kb = os.path.getsize(ref_path) // 1024
    print(f"Saved: {ref_path} ({size_kb} KB)")

    # Update character.json
    char_json_path = os.path.join(char_dir, "character.json")
    if os.path.exists(char_json_path):
        with open(char_json_path, "r") as f:
            data = json.load(f)
        data["reference_images"] = [ref_path]
        with open(char_json_path, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")
        print("Updated character.json with reference path")

    print("Done!")


if __name__ == "__main__":
    main()
