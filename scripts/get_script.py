"""Quick script to call Gemini and show the generated episode script."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from src.gemini_llm_client import GeminiLLMClient
from src.script_engine import ScriptEngine, SYSTEM_PROMPT
from src.story_manager import StoryManager
from src.episode_script import pretty_print, parse


sm = StoryManager(db_path="ramayan_db")
segment = sm._load_segment(1, 1)  # Bala Kanda, segment 1

client = GeminiLLMClient()
engine = ScriptEngine(llm_client=client, model="gemini-2.5-flash", characters_dir="models/characters")
registry = engine._get_character_registry()
prompt = engine._build_user_prompt(segment, registry, episode_number=1)

messages = [
    {"role": "system", "content": SYSTEM_PROMPT},
    {"role": "user", "content": prompt},
]

print("Calling Gemini 2.5 Flash...")
response = client.chat_completions_create(
    model="gemini-2.5-flash", messages=messages, temperature=0.7
)

# Clean up response
cleaned = response.strip()
if cleaned.startswith("```"):
    lines = cleaned.split("\n")
    if lines[-1].strip() == "```":
        lines = lines[1:-1]
    else:
        lines = lines[1:]
    cleaned = "\n".join(lines)

print("\n" + "=" * 60)
print("GENERATED SCRIPT:")
print("=" * 60)
print(cleaned)
