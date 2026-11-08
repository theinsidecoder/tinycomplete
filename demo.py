from tinycomplete import Autocomplete

ac = Autocomplete.from_words([
    ("python", 95), ("pytorch", 88), ("pytest", 40), ("pandas", 77), ("postgres", 74),
])

print(ac.suggest("py"))           # ['python', 'pytorch', 'pytest']
print(ac.suggest("p", k=2))       # ['python', 'pytorch']

# the user picked "pytest" -> make it more popular
ac.bump("pytest", 100)
print(ac.suggest("py", k=1))      # ['pytest']
