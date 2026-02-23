# engines/summarizer.py
from integrations.llm_integration import get_llm_response

class Summarizer:
    def summarize(self, turns):
        if not turns:
            return ""
        joined = "\n".join(f"You: {t['user']}\nKay: {t['kay']}" for t in turns[-6:])
        prompt = (
            "Summarize the ongoing conversation into a short memory recap "
            "that keeps emotional context and relevant facts.\n\n"
            f"{joined}\n\nRecap:"
        )
        return get_llm_response(prompt)
