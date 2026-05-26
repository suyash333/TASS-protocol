import string
import json

class SchemaCompiler:
    def __init__(self, prefix_char="~"):
        self.prefix = prefix_char
        self.token_pool = list(string.ascii_lowercase + string.ascii_uppercase)

    def compile(self, client_json_schema: dict):
        """Generates the TASS dictionary mapping and system prompt instructions."""
        schema_keys = list(client_json_schema.keys())
        
        if len(schema_keys) > len(self.token_pool):
            raise ValueError("Schema exceeds standard single-byte token pool.")

        reverse_map = {}
        prompt_lines = ["You are an extraction engine. Output ONLY the following format. No prose."]
        format_string = " ".join([f"{self.prefix}{self.token_pool[i]}:<value>" for i in range(len(schema_keys))])
        prompt_lines.append(f"Format: {format_string}")
        prompt_lines.append("Dictionary:")

        for i, key in enumerate(schema_keys):
            short_char = self.token_pool[i]
            reverse_map[short_char] = key 
            prompt_lines.append(f"{self.prefix}{short_char} = {key}")

        return reverse_map, "\n".join(prompt_lines)

class TASSParser:
    def __init__(self, dictionary_map: dict, prefix_char="~"):
        self.dictionary = dictionary_map
        self.prefix = prefix_char

    def parse(self, raw_llm_output: str) -> dict:
        """Rehydrates the raw LLM shorthand back into standard JSON."""
        parsed_data = {}
        pairs = raw_llm_output.strip().split(" ")
        
        for pair in pairs:
            if ":" in pair and pair.startswith(self.prefix):
                key, value = pair[len(self.prefix):].split(":", 1)
                # Only map keys that exist in our dynamic dictionary
                if key in self.dictionary:
                    parsed_data[self.dictionary[key]] = value
                    
        return parsed_data
