# In a more advanced version, this module would handle conversation history,
# context management, and potentially connect to a vector database for RAG.

class Memory:
    """
    A placeholder for future memory capabilities.
    For the MVP, all state is handled via the database repositories.
    """
    def __init__(self):
        self.history = []

    def add_entry(self, entry: dict):
        self.history.append(entry)

    def get_history(self):
        return self.history
