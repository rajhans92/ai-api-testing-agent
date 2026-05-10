from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

PROMPT_DIR = BASE_DIR / "prompts"


def loadPrompt(
    file_name: str,
    **kwargs
):

    template = (
        PROMPT_DIR / file_name
    ).read_text()

    return template.format(**kwargs)