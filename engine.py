"""Core autocomplete engine.

Data structures used:
  * Trie  - stores words by shared prefixes, so finding a prefix costs O(len(prefix)).
  * Heap  - a priority queue that always hands us the most promising branch first.

Trick that makes it fast: every trie node remembers `best`, the highest weight
found anywhere below it. The heap uses that number to explore the best branches
first, so we can stop after k results instead of scanning every match.
"""

from __future__ import annotations

import heapq
import json
from typing import Dict, Iterable, Iterator, List, Optional, Tuple, Union

NEG_INF = float("-inf")
_WORD, _NODE = 0, 1


class _Node:
    __slots__ = ("children", "is_word", "weight", "best")

    def __init__(self) -> None:
        self.children: Dict[str, "_Node"] = {}
        self.is_word = False
        self.weight: float = 0
        self.best: float = NEG_INF  # max weight in this node's whole subtree


class Autocomplete:
    """Prefix autocomplete with ranked results.

    >>> ac = Autocomplete()
    >>> ac.add("python", 90); ac.add("pytest", 40); ac.add("java", 70)
    >>> ac.suggest("py", k=2)
    ['python', 'pytest']
    """

    def __init__(self, case_sensitive: bool = False) -> None:
        self._root = _Node()
        self._size = 0
        self.case_sensitive = case_sensitive

    # ---------- helpers ----------
    def _norm(self, text: str) -> str:
        return text if self.case_sensitive else text.lower()

    def _path(self, text: str) -> Optional[List[_Node]]:
        """Nodes from the root down to `text`, or None if it is not in the trie."""
        node = self._root
        path = [node]
        for ch in text:
            node = node.children.get(ch)
            if node is None:
                return None
            path.append(node)
        return path

    @staticmethod
    def _refresh(path: List[_Node]) -> None:
        """Recompute `best` bottom-up along a path."""
        for node in reversed(path):
            best = node.weight if node.is_word else NEG_INF
            for child in node.children.values():
                if child.best > best:
                    best = child.best
            node.best = best

    # ---------- write ----------
    def add(self, word: str, weight: float = 1) -> None:
        """Insert `word`, or overwrite its weight if it already exists."""
        word = self._norm(word)
        if not word:
            raise ValueError("word must not be empty")
        node = self._root
        path = [node]
        for ch in word:
            nxt = node.children.get(ch)
            if nxt is None:
                nxt = node.children[ch] = _Node()
            node = nxt
            path.append(node)
        if node.is_word:
            old = node.weight
        else:
            node.is_word = True
            self._size += 1
            old = NEG_INF
        node.weight = weight
        if weight >= old:  # fast path: best can only go up
            for n in path:
                if weight > n.best:
                    n.best = weight
        else:  # weight went down: recompute along the path
            self._refresh(path)

    def bump(self, word: str, by: float = 1) -> None:
        """Make a word more popular (call this when a user picks a suggestion)."""
        self.add(word, self.weight(word) + by)

    def remove(self, word: str) -> bool:
        """Delete a word. Returns True if it existed."""
        word = self._norm(word)
        path = self._path(word)
        if not word or path is None or not path[-1].is_word:
            return False
        end = path[-1]
        end.is_word, end.weight = False, 0
        self._size -= 1
        for i in range(len(path) - 1, 0, -1):  # prune dead branches
            node = path[i]
            if node.children or node.is_word:
                break
            del path[i - 1].children[word[i - 1]]
        self._refresh(path)
        return True

    # ---------- read ----------
    def weight(self, word: str) -> float:
        path = self._path(self._norm(word))
        return path[-1].weight if path and path[-1].is_word else 0

    def suggest_with_scores(self, prefix: str, k: int = 5) -> List[Tuple[str, float]]:
        """Top-k completions as (word, weight), best first, ties alphabetical."""
        prefix = self._norm(prefix)
        path = self._path(prefix)
        if path is None or k <= 0:
            return []
        start = path[-1]
        heap: list = [(-start.best, prefix, _NODE, start)]
        out: List[Tuple[str, float]] = []
        while heap and len(out) < k:
            neg, text, kind, node = heapq.heappop(heap)
            if kind == _WORD:
                out.append((text, -neg))
                continue
            if node.is_word:
                heapq.heappush(heap, (-node.weight, text, _WORD, node))
            for ch, child in node.children.items():
                heapq.heappush(heap, (-child.best, text + ch, _NODE, child))
        return out

    def suggest(self, prefix: str, k: int = 5) -> List[str]:
        """Top-k completions, best first."""
        return [w for w, _ in self.suggest_with_scores(prefix, k)]

    def items(self) -> Iterator[Tuple[str, float]]:
        """Yield every (word, weight) in the trie."""
        stack = [("", self._root)]
        while stack:
            text, node = stack.pop()
            if node.is_word:
                yield text, node.weight
            for ch, child in node.children.items():
                stack.append((text + ch, child))

    # ---------- build / save / load ----------
    @classmethod
    def from_words(
        cls,
        words: Iterable[Union[str, Tuple[str, float]]],
        case_sensitive: bool = False,
    ) -> "Autocomplete":
        ac = cls(case_sensitive=case_sensitive)
        for item in words:
            if isinstance(item, str):
                ac.add(item)
            else:
                ac.add(item[0], item[1])
        return ac

    def save(self, path: str) -> None:
        data = {"case_sensitive": self.case_sensitive, "words": dict(self.items())}
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)

    @classmethod
    def load(cls, path: str) -> "Autocomplete":
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_words(data["words"].items(), data.get("case_sensitive", False))

    # ---------- dunder ----------
    def __len__(self) -> int:
        return self._size

    def __contains__(self, word: object) -> bool:
        if not isinstance(word, str):
            return False
        path = self._path(self._norm(word))
        return bool(path and path[-1].is_word)

    def __repr__(self) -> str:
        return f"Autocomplete(words={self._size}, case_sensitive={self.case_sensitive})"
