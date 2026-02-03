"""
Text chunking utility for RAG.

Splits documents into overlapping chunks for better retrieval.
"""

import re
from typing import List, Dict, Any, Optional


class TextChunker:
    """
    Splits text into overlapping chunks for embedding.

    Uses sentence-aware splitting to avoid breaking mid-sentence.
    """

    def __init__(
        self,
        chunk_size: int = 1000,
        overlap_percent: float = 0.18,
        min_chunk_size: int = 200,
    ):
        """
        Initialize chunker.

        Args:
            chunk_size: Target chunk size in characters (700-1300 recommended)
            overlap_percent: Overlap between chunks (0.15-0.22 recommended)
            min_chunk_size: Minimum chunk size (smaller chunks are merged)
        """
        self.chunk_size = chunk_size
        self.overlap_size = int(chunk_size * overlap_percent)
        self.min_chunk_size = min_chunk_size

    def chunk_text(
        self,
        text: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Split text into overlapping chunks.

        Args:
            text: The text to chunk
            metadata: Optional metadata to include with each chunk

        Returns:
            List of chunk dicts with 'text', 'chunk_index', 'total_chunks',
            and any provided metadata
        """
        if not text or not text.strip():
            return []

        # Clean and normalize text
        text = self._clean_text(text)

        # If text is small enough, return as single chunk
        if len(text) <= self.chunk_size:
            return [self._create_chunk(text, 0, 1, metadata)]

        # Split into sentences
        sentences = self._split_sentences(text)

        # Build chunks from sentences
        chunks = self._build_chunks(sentences)

        # Create chunk records
        total_chunks = len(chunks)
        return [
            self._create_chunk(chunk_text, idx, total_chunks, metadata)
            for idx, chunk_text in enumerate(chunks)
        ]

    def _clean_text(self, text: str) -> str:
        """Clean and normalize text."""
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove excessive punctuation
        text = re.sub(r'\.{3,}', '...', text)
        return text.strip()

    def _split_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences.

        Handles common edge cases like abbreviations, decimals, etc.
        """
        # Split on sentence boundaries
        # This regex handles: periods, exclamation, question marks
        # But avoids splitting on: Mr., Dr., etc., numbers like 3.14
        sentence_endings = r'(?<=[.!?])\s+(?=[A-Z])'

        # First, split on clear paragraph breaks
        paragraphs = re.split(r'\n\s*\n', text)

        sentences = []
        for para in paragraphs:
            # Split paragraph into sentences
            para_sentences = re.split(sentence_endings, para)
            sentences.extend([s.strip() for s in para_sentences if s.strip()])

        return sentences

    def _build_chunks(self, sentences: List[str]) -> List[str]:
        """
        Build overlapping chunks from sentences.

        Uses a sliding window approach with sentence-level granularity.
        """
        if not sentences:
            return []

        chunks = []
        current_chunk = []
        current_length = 0

        i = 0
        while i < len(sentences):
            sentence = sentences[i]
            sentence_len = len(sentence)

            # If single sentence exceeds chunk size, split it
            if sentence_len > self.chunk_size:
                # Flush current chunk first
                if current_chunk:
                    chunks.append(' '.join(current_chunk))
                    current_chunk = []
                    current_length = 0

                # Split long sentence into parts
                parts = self._split_long_sentence(sentence)
                chunks.extend(parts)
                i += 1
                continue

            # Check if adding this sentence would exceed chunk size
            if current_length + sentence_len + 1 > self.chunk_size:
                # Save current chunk
                if current_chunk:
                    chunks.append(' '.join(current_chunk))

                # Calculate overlap: keep last N characters worth of sentences
                overlap_sentences = self._get_overlap_sentences(
                    current_chunk, self.overlap_size
                )

                # Start new chunk with overlap
                current_chunk = overlap_sentences
                current_length = sum(len(s) + 1 for s in current_chunk)

            # Add sentence to current chunk
            current_chunk.append(sentence)
            current_length += sentence_len + 1
            i += 1

        # Don't forget the last chunk
        if current_chunk:
            chunk_text = ' '.join(current_chunk)
            # Only add if it's not too similar to previous chunk
            if not chunks or len(chunk_text) >= self.min_chunk_size:
                chunks.append(chunk_text)

        return chunks

    def _get_overlap_sentences(
        self,
        sentences: List[str],
        target_length: int
    ) -> List[str]:
        """Get sentences from the end to create overlap."""
        if not sentences:
            return []

        overlap = []
        current_length = 0

        # Work backwards through sentences
        for sentence in reversed(sentences):
            if current_length + len(sentence) > target_length:
                break
            overlap.insert(0, sentence)
            current_length += len(sentence) + 1

        return overlap

    def _split_long_sentence(self, sentence: str) -> List[str]:
        """Split a sentence that exceeds chunk size."""
        parts = []

        # Try to split on clause boundaries (commas, semicolons)
        clauses = re.split(r'[,;]\s*', sentence)

        current_part = []
        current_length = 0

        for clause in clauses:
            if current_length + len(clause) > self.chunk_size:
                if current_part:
                    parts.append(', '.join(current_part))
                current_part = [clause]
                current_length = len(clause)
            else:
                current_part.append(clause)
                current_length += len(clause) + 2

        if current_part:
            parts.append(', '.join(current_part))

        # If still too long, do hard split
        final_parts = []
        for part in parts:
            if len(part) > self.chunk_size:
                # Hard split with overlap
                for j in range(0, len(part), self.chunk_size - self.overlap_size):
                    final_parts.append(part[j:j + self.chunk_size])
            else:
                final_parts.append(part)

        return final_parts

    def _create_chunk(
        self,
        text: str,
        chunk_index: int,
        total_chunks: int,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a chunk record with metadata."""
        chunk = {
            "text": text,
            "chunk_index": chunk_index,
            "total_chunks": total_chunks,
            "char_count": len(text),
        }

        if metadata:
            chunk["metadata"] = metadata

        return chunk


# Default chunker instance
_default_chunker = None


def get_chunker(
    chunk_size: int = 1000,
    overlap_percent: float = 0.18
) -> TextChunker:
    """Get or create a chunker instance."""
    global _default_chunker
    if _default_chunker is None:
        _default_chunker = TextChunker(
            chunk_size=chunk_size,
            overlap_percent=overlap_percent
        )
    return _default_chunker


def chunk_document(
    doc_id: str,
    text: str,
    metadata: Dict[str, Any],
    chunk_size: int = 1000,
    overlap_percent: float = 0.18
) -> List[Dict[str, Any]]:
    """
    Convenience function to chunk a document for Pinecone.

    Args:
        doc_id: Base document ID
        text: Document text to chunk
        metadata: Document metadata (copied to each chunk)
        chunk_size: Target chunk size in characters
        overlap_percent: Overlap between chunks

    Returns:
        List of records ready for Pinecone, each with:
        - id: "{doc_id}_chunk_{index}"
        - text: Chunk text for embedding
        - metadata: Original metadata plus chunk info
    """
    chunker = TextChunker(chunk_size=chunk_size, overlap_percent=overlap_percent)
    chunks = chunker.chunk_text(text, metadata)

    records = []
    for chunk in chunks:
        chunk_metadata = chunk.get("metadata", {}).copy()
        chunk_metadata.update({
            "chunk_index": chunk["chunk_index"],
            "total_chunks": chunk["total_chunks"],
            "parent_id": doc_id,
        })

        records.append({
            "id": f"{doc_id}_chunk_{chunk['chunk_index']}",
            "text": chunk["text"],
            "metadata": chunk_metadata,
        })

    return records
