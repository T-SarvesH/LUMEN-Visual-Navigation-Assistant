import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

class NarratorBot:
    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY")
        
        # Internal system instructions - kept out of public attributes
        self._system_instruction = """
        You are LUMEN, a navigation assistant for the blind.
        Task: Refine skeletal spatial data into natural, supportive speech.
        
        RULES:
        1. Return ONLY the final narration. 
        2. NO preambles (e.g., "Here is the description...").
        3. NO post-scripts or technical IDs.
        4. Keep it TELEGRAPHIC and brief.
        5. Prioritize 'directly ahead' above all else.
        """
        
        if self.api_key:
            self.client = Groq(api_key=self.api_key)
        else:
            self.client = None
            print("Warning: GROQ_API_KEY missing. Fallback mode enabled.")

    def _pluralize(self, word, count):
        if count == 1: return f"a {word}"
        if word == "person": return f"{count} people"
        if word.endswith(('s', 'sh', 'ch', 'x', 'z')): return f"{count} {word}es"
        return f"{count} {word}s"

    def generate_rule_based_nl(self, scene_data):
        """Layer 1: Deterministic spatial mapping."""
        if not scene_data or not scene_data.get("scenery"):
            return "Path is clear."

        priority_map = [
            ("Immediate Forward", "directly ahead"), ("Left", "on your left"),
            ("Right", "on your right"), ("Far Forward", "in the distance ahead"),
            ("Far Left", "far to your left"), ("Far Right", "far to your right")
        ]

        results = []
        scenery = scene_data["scenery"]
        for zone_key, zone_label in priority_map:
            items = [self._pluralize(obj, zones[zone_key]) 
                     for obj, zones in scenery.items() if zones.get(zone_key, 0) > 0]
            if items:
                results.append(f"{', '.join(items)} {zone_label}")

        return ". ".join(results[:3]) + "."

    def generate_narration(self, scene_data_dict):
        """Main entry point: Rules -> Groq Compound -> Clean Log Output."""
        skeletal_text = self.generate_rule_based_nl(scene_data_dict)
        
        if self.client:
            try:
                # Direct constraint in the user message to prevent preambles
                prompt = (f"Refine this into a natural narration. Respond ONLY with the "
                         f"final sentence, no other text: {skeletal_text}")
                
                response = self.client.chat.completions.create(
                    model="groq/compound",
                    messages=[
                        {"role": "system", "content": self._system_instruction},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.1, # Low temperature for strict adherence
                    max_tokens=100,
                )
                # Extract and clean result
                final_narration = response.choices[0].message.content.strip()
                return final_narration if final_narration else skeletal_text
            except Exception as e:
                # Error log is sanitized to not include full prompt history
                print(f"Inference Error: {e}")
                return skeletal_text
        
        return skeletal_text