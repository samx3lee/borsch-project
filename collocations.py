import re
import spacy
import pymorphy3
import nltk
from nltk.collocations import BigramCollocationFinder, TrigramCollocationFinder
from nltk.metrics import BigramAssocMeasures, TrigramAssocMeasures

nltk.download("punkt", quiet=True)
nltk.download("punkt_tab", quiet=True)
nltk.download("stopwords", quiet=True)

morph = pymorphy3.MorphAnalyzer()
nlp = spacy.blank("ru")

target_words = [
    "борщ", "свекла", "капуста", "лук", "морковь",
    "картофель", "варить", "жарить", "тушить", "нарезать",
    "добавить", "сметана", "зелень", "подавать"
]

def normalize(word):
    return morph.parse(word)[0].normal_form

target_lemmas = {normalize(w): w for w in target_words}

with open(r"C:\Users\Timur\OneDrive\Desktop\код\borsch_corpus_lem_natasha.txt", encoding="utf-8") as f:
    raw_text = f.read()

raw_text = re.sub(r"[^\w\s]", " ", raw_text)
raw_text = re.sub(r"\s+", " ", raw_text).strip()

doc = nlp(raw_text)
tokens = [token.text.lower() for token in doc if token.is_alpha]

lemmatized_tokens = [normalize(t) for t in tokens]

print("=" * 70)
print("биграмные коллокации (PMI) для целевых слов")
print("=" * 70)

bigram_finder = BigramCollocationFinder.from_words(lemmatized_tokens)
bigram_finder.apply_freq_filter(2)

bigram_measures = BigramAssocMeasures()
all_bigram_scored = bigram_finder.score_ngrams(bigram_measures.pmi)

for target_lemma, original_word in sorted(target_lemmas.items(), key=lambda x: x[1]):
    relevant = [
        (w1, w2, score)
        for (w1, w2), score in all_bigram_scored
        if w1 == target_lemma or w2 == target_lemma
    ]
    relevant_sorted = sorted(relevant, key=lambda x: x[2], reverse=True)[:10]
    print(f"\n>>> {original_word} ({target_lemma})")
    if relevant_sorted:
        for w1, w2, score in relevant_sorted:
            partner = w2 if w1 == target_lemma else w1
            print(f"    {w1} + {w2:<20} PMI = {score:.4f}   (партнёр: {partner})")
    else:
        print("    коллокации не найдены")

print("\n" + "=" * 70)
print("триграмные коллокации (PMI) для целевых слов")
print("=" * 70)

trigram_finder = TrigramCollocationFinder.from_words(lemmatized_tokens)
trigram_finder.apply_freq_filter(2)

trigram_measures = TrigramAssocMeasures()
all_trigram_scored = trigram_finder.score_ngrams(trigram_measures.pmi)

for target_lemma, original_word in sorted(target_lemmas.items(), key=lambda x: x[1]):
    relevant = [
        (w1, w2, w3, score)
        for (w1, w2, w3), score in all_trigram_scored
        if target_lemma in (w1, w2, w3)
    ]
    relevant_sorted = sorted(relevant, key=lambda x: x[3], reverse=True)[:5]
    print(f"\n>>> {original_word} ({target_lemma})")
    if relevant_sorted:
        for w1, w2, w3, score in relevant_sorted:
            print(f"    {w1} + {w2} + {w3:<20} PMI = {score:.4f}")
    else:
        print("    коллокации не найдены")

print("\n" + "=" * 70)
print("частотные биграммы (chi-square) для целевых слов")
print("=" * 70)

bigram_finder2 = BigramCollocationFinder.from_words(lemmatized_tokens)
bigram_finder2.apply_freq_filter(3)
all_chi2_scored = bigram_finder2.score_ngrams(bigram_measures.chi_sq)

for target_lemma, original_word in sorted(target_lemmas.items(), key=lambda x: x[1]):
    relevant = [
        (w1, w2, score)
        for (w1, w2), score in all_chi2_scored
        if w1 == target_lemma or w2 == target_lemma
    ]
    relevant_sorted = sorted(relevant, key=lambda x: x[2], reverse=True)[:10]
    print(f"\n>>> {original_word} ({target_lemma})")
    if relevant_sorted:
        for w1, w2, score in relevant_sorted:
            print(f"    {w1} + {w2:<20} chi2 = {score:.4f}")
    else:
        print("    коллокации не найдены")

print("\n" + "=" * 70)
print("коллокации через spaCy (окно ±2 токена)")
print("=" * 70)

from collections import Counter

window_collocations = {lemma: Counter() for lemma in target_lemmas}

for i, token_lemma in enumerate(lemmatized_tokens):
    if token_lemma in target_lemmas:
        start = max(0, i - 2)
        end = min(len(lemmatized_tokens), i + 3)
        neighbors = lemmatized_tokens[start:i] + lemmatized_tokens[i+1:end]
        window_collocations[token_lemma].update(neighbors)

for target_lemma, original_word in sorted(target_lemmas.items(), key=lambda x: x[1]):
    top = window_collocations[target_lemma].most_common(10)
    print(f"\n>>> {original_word} ({target_lemma})")
    if top:
        for neighbor, count in top:
            print(f"    {neighbor:<25} частота = {count}")
    else:
        print("    коллокации не найдены")