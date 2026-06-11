# Developer Documentation: Collocation Analyzer (NLTK + spaCy + pymorphy3)
**Module name:** `collocation\_analyzer.py`  
**Version:** 1.0  
**Purpose:** identification of collocations (stable bigrams and trigrams) from the text corpus of borscht recipes, followed by a comparison of the effectiveness of different methods (PMI, chi‑square, window counting). It is used for scientific research within the framework of the project "Extraction and analysis of collocations in culinary recipes".
### 1.Architecture Overview
The script performs the following steps sequentially:
1. **Loading the case** – reading a text file `borsch\_corpus\_lem\_natasha.txt ` (the result of the parser).
2. **Preprocessing** – removing punctuation, reducing to lowercase, lemmatization using pymorphy3.
3. **There are three ways to search for collocations:**

    * PMI (Pointwise Mutual Information) for bigrams and trigrams (NLTK).
    * Chi-square for bigrams (NLTK).
    * Windowed method (±2 tokens window) with frequency counting (manual implementation based on `collections.Counter').
4. **Output of results** for a given list of target words (ingredients, actions).

### 2. Dependencies
|Library|Version|Appoitment|
|-|-|-|
|`re`|built-in|cleaning the text from punctuation marks|
|`nltk`|≥3.6|collocation search (BigramCollocationFinder, metrics PMI, chi‑square)|
|`spacy`|≥3.0|tokenization (using `spacy.blank("ru")` – no model, just a rule for spaces)|
|`pymorphy3`|≥1.0|morphological analysis, reduction to normal form (lemma)|
|`collections.Counter`|buili-in|window counting of neighbors|

**NLTK data uploaded automatically:**
* `punkt` – tokenizer
* `punkt\_tab` is an auxiliary file for punkt.
* `stopwords` – not used in the code, but loaded (can be deleted).

**Install all dependencies:**
```bash
pip install nltk spacy pymorphy3
```

**Note:** the current code uses `spacy.blank("ru")` is an empty language pipeline that splits text only by spaces. For more accurate tokenization, you can replace it with `spacy.load("ru\_core\_news\_sm")'. You will need to download the Russian model.

### 3. Configuration and input data
**Name of the input file:**
```python
with open(r"C:\\Users\\borsch\_corpus\_lem\_natasha.txt", encoding="utf-8") as f:
    raw\_text = f.read()
```
**Recommendation:** enter the path to an environment variable or a command line parameter (for example, via `argparse`).
**List of target words (key ingredients and actions):**
The words are indicated in their original form. The script automatically lemmatizes them through pymorphy3 (to search by normal form).

```python
target\_words = \[
    "борщ", "свекла", "капуста", "лук", "морковь",
    "картофель", "варить", "жарить", "тушить", "нарезать",
    "добавить", "сметана", "зелень", "подавать"
]
```

### 4. Text preprocessing
Algorithm:
1. Delete all characters except letters and spaces: `re.sub(r"\[^\\w\\s]", " ", raw\_text)`.
2. Compression of multiple spaces: `re.sub(r"\\s+", " ", raw\_text).strip()`.
3. Tokenization via `spacy.blank("ru")`. Each token is checked for `token.is\_alpha` (alphabetic only).
4. Bringing tokens to lowercase.
5. Lemmatization of each token using `pymorphy3.MorphAnalyzer().parse(word)\[0].normal\_form`.
* If there is no correct lemma (for example, for rare words), pymorphy3 returns the original word (since the first parsing option is taken).
* Lemmatization is performed for each word separately, which is slow for large corpora (but acceptable for 25-50 recipes).

### 5. Functions and key variables

* 5.1 Global Objects
```python
morph = pymorphy3.MorphAnalyzer()
nlp = spacy.blank("ru")
```

* 5.2 Function `normalize(word) -> str`
Returns the normal form (lemma) for the specified word.

* 5.3 `target\_lemmas`
Dictionary `{lemma: source\_word}`. It is built automatically from `target\_words'.

* 5.4 Bigram search via PMI
For each target word, 10 bigrams with the highest PMI are selected, where it participates.
```python
    bigram\_finder = BigramCollocationFinder.from\_words(lemmatized\_tokens)

    bigram\_finder.apply\_freq\_filter(2)   #we discard pairs that occur less than 2 times.
    
    all\_bigram\_scored = bigram\_finder.score\_ngrams(bigram\_measures.pmi)
```

* 5.5 Trigram search via PMI
Similarly, but the filter frequency is 2, the top 5 trigrams are displayed.

* 5.6 Bigram search via chi‑square

```python
    bigram\_finder2 = BigramCollocationFinder.from\_words(lemmatized\_tokens)

    bigram\_finder2.apply\_freq\_filter(3)   #raising the threshold for the chi square

    all\_chi2\_scored = bigram\_finder2.score\_ngrams(bigram\_measures.chi\_sq)
```

* 5.7 Window‑based method.
For each occurrence of the target word, the neighbors on the left and right are taken (a window with a width of 2 before and 2 after). The frequency of joint occurrence is summed up. The 10 most frequent partners are displayed.
```python
window\_collocations = {lemma: Counter() for lemma in target\_lemmas}
for i, token\_lemma in enumerate(lemmatized\_tokens):
    if token\_lemma in target\_lemmas:
        start = max(0, i - 2)
        end = min(len(lemmatized\_tokens), i + 3)
        neighbors = lemmatized\_tokens\[start:i] + lemmatized\_tokens\[i+1:end]
        window\_collocations\[token\_lemma].update(neighbors)
```

### 6. Output data

The script does not output the results to the console. Instead, it creates a file `collocations_results.txt ` in the directory specified in the 'output_path` variable.  
By default, the path is hardcoded:

```python
output_path = r"C:\Users\Desktop\collocations_results.txt"
```
* **Bigrams (PMI)** – up to 10 pairs.
* **Trigrams (PMI)** – up to 5 triples.
* **Bigrams (chi‑square)** – up to 10 pairs.
* **Window method** – The 10 most frequent neighbors.

Example of an output fragment:

```
    ======================================================================
    Биграмные коллокации (PMI) для целевых слов
    ======================================================================
>>> свекла (свекла)
    свекла + варить               PMI = 5.2341   (партнёр: варить)
    свекла + очистить              PMI = 4.9823   (партнёр: очистить)
```
To read the results in Python after executing the script, use:

```python
with open("collocations_results.txt", "r", encoding="utf-8") as f:
    for line in f:
        print(line.rstrip())
```

### 7. Implementation features and potential problems

|Problem|Reason|Decision|
|-|-|-|
|**Low quality of tokenization**|`spacy.blank("ru")` does not break complex constructions (for example, "grate beetroot" -> one token?). In fact, it breaks it down by spaces, which is usually acceptable for cooking recipes.|Replace with `spacy.load("ru\_core\_news\_sm")– but it will increase the time.|
|**Lemmatization via pymorphy3 is slow**|A `Parse` object is created for each token. It's noticeable for a corpus of thousands of words.|Use the cache (dictionary), or switch to 'pymorphy3` with preloaded lemmas.|
|**Sensitivity to the form of the word in `target\_words'**|If the word is not written in its initial form, the lemma may not match. For example, "cooked" -> the "cook" lemma. The user must specify the words in the normal form.|Specify it explicitly in the documentation.|
|**No deletion of stop words**|Prepositions, conjunctions, and pronouns can get into collocations and clog up the result.|Add a stopword filter (a list of nltk.corpus.stopwords or your own).|
|**Different metrics for comparison**|PMI and chi‑square give different rankings. The script does not normalize them among themselves.|This is a research task, left as it is.|

### 8. Expansion and modification

* 8.1 Adding new target words.
Change the list of `target\_words'. New words will be lemmatized automatically.

 8.2 Changing the window size (for the window method).
Adjust the values of `i - 2` and `i + 3' (now half-width 2). To change the window to ±3, use `range(i-3, i+4)'.

* 8.3 Exporting the results to a file.
Add it after all calculations:

```python
import sys
sys.stdout = open("collocations\_report.txt", "w", encoding="utf-8")
sys.stdout.close()
```

### 9. Testing Recommendations

1. Take 2-3 recipes.
2. Run the script.
3. Manually check that:

   * Lemmatization works (for example, "beetroot" -> "beetroot", "roast" -> "roast").
   * Bigrams do not contain punctuation marks.
   * The window method gives meaningful results.

For unit tests (pytest), you can put the `normalize` function and the processing of the corpus into separate methods.

**Prospects for improvement (Future Work):** To increase the correlation with the reference tools in the code, replace PMI/χ2 with Log-Likelihood (G2) or T-score, which are designed to work with rare events and are better suited for small buildings.


