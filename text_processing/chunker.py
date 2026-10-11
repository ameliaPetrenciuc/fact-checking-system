from typing import List, Dict
from config.settings import CHUNK_SIZE, CHUNK_OVERLAP


class TextChunker:
    def __init__(self, chunk_size: int = None, overlap: int = None):
        self.chunk_size = chunk_size or CHUNK_SIZE
        self.overlap = overlap or CHUNK_OVERLAP

        if self.overlap >= self.chunk_size and self.chunk_size > 0:
            raise ValueError(f"Overlap ({self.overlap}) must be smaller than chunk size ({self.chunk_size}).")

    def chunk_text(self, text: str) -> List[Dict[str, any]]:
        words = text.split()
        total_words = len(words)
        if total_words == 0:
            return []

        chunks = []
        start_index = 0
        chunk_number = 1

        while start_index < total_words:
            end_index = min(start_index + self.chunk_size, total_words)
            chunk_text = " ".join(words[start_index:end_index])

            chunks.append({
                "text": chunk_text,
                "chunk_number": chunk_number,
                "start_word": start_index,
                "end_word": end_index - 1,
                "word_count": end_index - start_index,
            })

            next_start_index = start_index + self.chunk_size - self.overlap
            if next_start_index <= start_index:
                if end_index == total_words:
                    break
                next_start_index = start_index + 1

            start_index = next_start_index
            chunk_number += 1

        return chunks

