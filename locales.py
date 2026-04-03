import json
import os
import logging

class Locales:
    def __init__(self, locales_dir="locales"):
        self.locales_dir = locales_dir
        self.translations = {}
        self.load_translations()

    def load_translations(self):
        """Load JSON translation files from the locales directory."""
        for filename in os.listdir(self.locales_dir):
            if filename.endswith(".json"):
                lang_code = filename.split(".")[0]
                try:
                    with open(os.path.join(self.locales_dir, filename), "r", encoding="utf-8") as f:
                        self.translations[lang_code] = json.load(f)
                    logging.info(f"Loaded translations for language: {lang_code}")
                except Exception as e:
                    logging.error(f"Error loading translation file {filename}: {e}")

    def get(self, key, lang_code="uz", **kwargs):
        """Get translated text for a key and language code."""
        # Fallback to 'uz' if lang_code is missing or invalid
        lang_translations = self.translations.get(lang_code, self.translations.get("uz", {}))
        
        # Get the value, or the key itself as a fallback
        value = lang_translations.get(key, key)
        
        # Format if kwargs provided
        if kwargs and isinstance(value, str):
            try:
                return value.format(**kwargs)
            except KeyError as e:
                logging.warning(f"Missing key in translation format: {e} for key {key}")
        
        return value

# Global locales instance
locales = Locales()
