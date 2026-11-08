"""Compare tinycomplete with the naive approach (scan everything, then rank)."""
import heapq
import random
import string
import time

from tinycomplete import Autocomplete

N, K = 200_000, 5
rng = random.Random(42)
words = {"".join(rng.choices(string.ascii_lowercase, k=rng.randint(3, 10))): rng.randint(1, 10_000) for _ in range(N)}

t = time.perf_counter()
ac = Autocomplete.from_words(words.items())
print(f"Built trie with {len(ac):,} words in {time.perf_counter() - t:.2f}s\n")

items = list(words.items())


def naive(prefix):
    hits = [(w, s) for w, s in items if w.startswith(prefix)]
    return [w for w, _ in heapq.nsmallest(K, hits, key=lambda t: (-t[1], t[0]))]


def timeit(fn, prefix, reps):
    t = time.perf_counter()
    for _ in range(reps):
        fn(prefix)
    return (time.perf_counter() - t) / reps * 1000


print(f"{'prefix':<8}{'naive (ms)':>12}{'tinycomplete (ms)':>20}{'speed-up':>11}")
for prefix in ["a", "ab", "abc", "xyz"]:
    assert ac.suggest(prefix, K) == naive(prefix)
    a = timeit(naive, prefix, 5)
    b = timeit(lambda p: ac.suggest(p, K), prefix, 200)
    print(f"{prefix:<8}{a:>12.2f}{b:>20.3f}{a / b:>10.0f}x")
