from abc import ABC, abstractmethod

class LLMClient(ABC):
    @abstractmethod
    def generate(self, messages: list[dict]) -> str:

        raise NotImplementedError