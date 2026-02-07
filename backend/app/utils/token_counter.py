import tiktoken


class TokenCounter:
    def __init__(self, model: str = "gpt-4o"):
        try:
            self.encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            self.encoding = tiktoken.get_encoding("cl100k_base")

    def count(self, text: str) -> int:
        if not text:
            return 0
        return len(self.encoding.encode(text))

    def count_messages(self, messages: list) -> int:
        total = 0
        for msg in messages:
            total += 4  # message overhead
            for key, value in msg.items():
                if isinstance(value, str):
                    total += self.count(value)
        total += 2  # reply priming
        return total
