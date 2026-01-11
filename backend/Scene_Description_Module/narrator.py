import os
import json
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Load environment variables (looks for .env file)
load_dotenv()

class NarratorBot:
    def __init__(self):
        """
        Initializes the Gemini client and sets up the strict system prompt.
        """
        # 1. Securely load API Key
        self.api_key = os.getenv("GEMINI_API_KEY")

        if not self.api_key:
            print("⚠️ Warning: GEMINI_API_KEY not found. Narrator is disabled.")
            self.model = None
            return
 
        # 3. Define the Spatial Logic (Horizontal Zones Only)
        # This acts as the "brain" for the bot so it understands the raw coordinates.
        self.system_instruction = """
        You are LUMEN, a navigation assistant for a blind user.
        
        ### SCENE GEOMETRY RULES
        The camera resolution is 1280 (width) x 720 (height).
        - LEFT ZONE: x < 450
        - CENTER ZONE (DANGER): 450 <= x <= 850
        - RIGHT ZONE: x > 850
        
        ### INSTRUCTIONS
        1. Analyze the JSON data provided.
        2. Prioritize objects in the CENTER ZONE (Immediate Path Obstruction).
        3. Group similar objects (e.g., "crowd of people", "several trucks").
        4. Objects in Left/Right zones are background context only.
        5. OUTPUT FORMAT: Natural, spoken English. Max 2 sentences. NO NUMBERS, NO IDs.
        
        ### PRIORITY ORDER (Generate in Natural Language in this order)
        1. Unique object types and their count
        2. Path Obstructions (Center Zone)
        3. Incoming Traffic
        4. General Scenery

        ### LIMIT THE OUTPUT UNDER 200 WORDS Strictly and never ever keep the sentence incomplete
        """
        
        # 4. Initialize Model (Using Flash for speed)
        self.client = genai.Client(api_key=self.api_key)

    def generate_narration(self, scene_data_dict):
        """
        Accepts a dictionary (scene data), converts to JSON string, and calls Gemini.
        Returns: String (The narration) or None.
        """

        try:
            # Convert dictionary to JSON string for the LLM
            json_str = json.dumps(scene_data_dict)
            
            # Generate content
            response = self.client.models.generate_content(
               model="gemini-1.5-flash-8b",
               contents=f"Analyze this scene data:\n{json_str}",

               config=types.GenerateContentConfig(
                   
                   system_instruction=self.system_instruction,
                   temperature=0.3,
               )
            )
            
            # Return cleaned text
            return response.text.strip()
            
        except Exception as e:
            print(f"❌ Narrator Error: {e}")
            return None