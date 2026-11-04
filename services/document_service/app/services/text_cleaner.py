
import re
import unicodedata


class TextCleaner:

    _CHAR_TRANSLATION = str.maketrans({
        "ي": "ی",
        "ى": "ی",
        "ك": "ک",
        "ۀ": "ه",
        "ة": "ه",
        "ؤ": "و",
        "إ": "ا",
        "أ": "ا",
    })

    _BIDI_CONTROLS = re.compile(
        "[\u200e\u200f\u202a-\u202e\u2066-\u2069]"
    )

    def clean(self, text: str) -> str:
        if not isinstance(text, str):
            raise TypeError("Input must be a string.")

        text = unicodedata.normalize("NFKC", text)
        text = text.translate(self._CHAR_TRANSLATION)

        # Remove Arabic tatweel.
        text = text.replace("\u0640", "")

        # Remove invisible bidirectional formatting controls.
        text = self._BIDI_CONTROLS.sub("", text)

        # Normalize line endings.
        text = text.replace("\r\n", "\n").replace("\r", "\n")

        # Normalize horizontal whitespace.
        text = re.sub(r"[ \t\f\v]+", " ", text)

        # Remove spaces around line breaks.
        text = re.sub(r" *\n *", "\n", text)

        # Limit consecutive blank lines.
        text = re.sub(r"\n{3,}", "\n\n", text)

        return text.strip()