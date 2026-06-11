## Developer Documentation: Borscht recipe parser with povar.ru
Parser version: 1.0  
Implementation language: Python 3.7+
### 1. Architecture Overview
The parser is a single-threaded script with no external dependencies (except for `requests`, `BeautifulSoup', and standard modules). It works in two stages:
1. Link collection – through the search endpoint `/xmlsearch' with pagination.
2. Content extraction – for each link, the name, ingredients and cooking text are extracted, followed by writing to a file.

**Data flow:**
`search query` -> `get\_recipe\_links()' -> `URL list' -> `parse\_recipe()` for each URL -> `borsch\_corpus.txt `

All HTTP requests use a single `User-Agent` to simulate a browser.

### 2. Dependencies


| Library | Version      | Appointment                     |
|------------|-------------|--------------------------------|
| `requests` | ≥2.25.0     | HTTP requests, processing timeouts |
| `beautifulsoup4` | ≥4.9.0 | HTML parsing (looking for tags, attributes) |
| `re`       | integrated | text filtering and header search |
| `time`     | integrated  | delays between requests       |
| `urllib.parse` | integrated | formation of absolute URLs    |

Installation: 

```bash

pip install requests beautifulsoup4

```

### 3. Configuration constants

```python

BASE\_URL = "https://povar.ru"                     # the base domain

SEARCH\_URL = "https://povar.ru/xmlsearch" 

headers = {"User-Agent": "Mozilla/5.0 ..."}     

```

**Features:**  

- The search URL is fixed, the parameters are passed via `params=` to `requests.get()'.  

- The `User-Agent` can be replaced with any current one to avoid blocking.

### 4. Functions and algorithms
#### 4.1 `get\_recipe\_links(query="борщ", max\_recipes=30) -> list`
Collects up to `max\_recipes` URLs of recipes matching the search query.

**Parameters:**  
- `query` – the search string (passed to the `query` parameter of the XML search).  

- `max\_recipes' – the maximum number of links to return.

**The algorithm:**
1. Initialize `page = 1` and an empty list of `links'.  

2. The loop `while len(links) < max\_recipes and page <= 10`:

&#x20; - 'BeautifulSoup' parses the response.  

&#x20; - Searches for all `<a href>`: if `href` contains `/recipes/` and `recipe` and is not yet in the list, it generates the full URL via `urljoin()`.  

&#x20; - Extracts the link text, lowercase it, checks for `borscht` or `soup'.  

&#x20; - Adds the URL to the list (early interruption when `max\_recipes' is reached).  

&#x20; - Searches for the pagination element: `<a>` with the text "Next" or ">" (regular expression `r"Next|>"`, flag `re.I`). If not found, exit.  

&#x20; - Increases the `page', the delay is `time.sleep(1)` (so as not to overload the server). 

3. Returns `links\[:max\_recipes]`.

*Note:*  

- The filter for the words `borscht/soup' in the link text is hardwired, but it is easy to parameterize or remove it.  

- Pagination relies on the Russian text "Next" – it may break if the site changes localization.  

- If there is a request error (network, timeout), the function is interrupted and returns the already collected links.

#### 4.2 `parse\_recipe(url) -> str or None`

**Purpose:** extracts the name, ingredients, and instructions from the recipe page and returns formatted text.

**Parameters:**  

- `url' – the full URL of the recipe page (for example, `https://povar.ru/recipes/borsch\_klassicheskij-12345 `).


**Output format:**

```
Заголовок рецепта                            #Recipe title

ИНГРЕДИЕНТЫ: ингредиент 1; ингредиент 2;...  #ingredients

ПРИГОТОВЛЕНИЕ: текст приготовления           #cooking text

```

**The algorithm:**

1. **HTTP request** with a timeout of 10 seconds. It is set to `resp.encoding = 'utf-8" (the site returns in UTF-8).  

2. **Name** – searches for the first tag `<h1>`, returns `"Untitled" if missing.  

3. **Ingredients** (multi-step search):

- Searches for the header `<h2>` or `<h3>`, the contents of which (using the regular expression `r'Structure|Ingredients"`, `re.I`).  

- If found, moves to the next element `next\_elem= header.find\_next()'.  

- If `next\_elem.name == "ul"` – extracts all `<li>`.  

- Otherwise, it tries to find the `<ul>` tag inside `next\_elem' and the `<li>` lists from it.  

- If it didn't work, it searches for a `div` with classes containing `ingredients` or `composition` (case–insensitive), from it – `<li>`.  

- Each ingredient is cleaned via `.get\_text(strip=True)`.

4. **Cooking instructions:**  

- Searches for the heading `<h2>` or `<h3>` with the text `How to cook` (regexp `re.I`).  

- Bypasses subsequent nodes (`while current and len(cooking\_steps) < 30`):  

- If the node is a tag `<p>`, `<div>` or `<li>` – extracts the text.  

- Filters short strings (`len(text) > 30`) and strings containing stop words (`thank you', `comment', `rate', `add comment').  

- Adds to `cooking\_steps'.  

- Stops if it encounters the following heading `<h2>`/`<h3>` (except when the heading contains `"similar"`).  

- If it was not possible to find the steps in this way, it makes a fallback: it searches for all the `<p>` tags, selects lines longer than 80 characters, filtering service words (`calories`, `proteins', `fats', etc.).  

- Glues the steps separated by a space in `cooking\_text'. 

5. **Validation:** if `cooking\_text` is empty or shorter than 100 characters, the function returns `None' (the recipe is considered incomplete).  

6. **String formation:**
```python

  full\_text = f"{title}\\nИНГРЕДИЕНТЫ: {ingredients\_text}\\nПРИГОТОВЛЕНИЕ: {cooking\_text}"
 
```

**Notes:**  

- The ingredients are separated by a semicolon (`; `).  

- If the ingredients are not found, the output is `"Not found"`.  

- The stopword filter is hard-coded in strings – not localized for other languages.  

- The logic of searching for instructions can skip steps if they are not located in a row or inside complex nested blocks (for example, inside `<div class="recipe-step">`). The code assumes a flat structure – a potentially fragile place.

### 5. Main block

```python

print(" Поиск рецептов борща...")

recipe\_urls = get\_recipe\_links("борщ", max\_recipes=25)

if recipe\_urls:

   recipes = \[]

   for i, url in enumerate(recipe\_urls, 1):

       text = parse\_recipe(url)

       if text:

          recipes.append(text)

       time.sleep(0.5)   


```

### 6. Error handling


| Type of error                      | Where is it intercepted      | Action                                      |
|---------------------------------|--------------------------|-----------------------------------------------|
| `requests.exceptions.RequestException` (timeout, connection) | `get\_recipe\_links()` и `parse\_recipe()` | Prints a message, interrupts the current cycle, returns what has already been collected. |
| Lack of expected HTML tags | inside `parse\_recipe()`  | Continues execution with an empty list/row; returns `None` if the cooking text could not be extracted. |
| Decoding error (rare)    | –                        | UTF-8 is assumed, no other encoding is processed. |

### 7. Extensibility and modification points

To adapt the parser to other sections of the site or other culinary queries:

- **Change the link filter** (line `if "borscht" in link\_text or "soup" in link\_text').  

Make the function parameter: `keyword\_filter=\["borscht"]`.

- **Change the ingredient selectors** – the headers with the text "Composition"/"Ingredients" and the classes `ingredients/composition` are currently used. If the site changes the layout, you need to update the regular expressions in `soup.find(..., string=re.compile(...))` and classes.

- **Change stop words to filter instructions** – list `\["thank you", "comment", ...]` make it a constant.

- **Add export to JSON/CSV** – change the main block of the record.

**For collocation analysis:** the output `.txt` is ready to be uploaded to AntConc (each recipe is separated by a separator `=`×70). If you need clean text without markers, you can remove the lines `INGREDIENTS'.:` and the separators.

**Prospects for improvement (Future Work)**: To increase the correlation with the reference tools in the code, replace PMI/χ2 with Log-Likelihood (G2) or T-score, which are designed to work with rare events and are better suited for small buildings.

### 8.Known limitations

1. **Sensitivity to HTML structure** – when updating the design `povar.ru the parser may stop finding ingredients or cooking steps. It requires periodic verification.

2. **There is no dynamic content processing** – the site is static, JS is not used, so `requests' is enough.

3. **There is no logging** – only informational messages are displayed in the console. For industrial use, it is worth adding the `logging` module.

4. **No multithreading support** – The collection of recipes is sequential. When collecting thousands of recipes, you can speed up through `concurrent.futures`, but with courtesy (rate limiting).

5. **The encoding of the** file is always UTF-8. Notepad may not display correctly when opened in Windows (Notepad++ or VS Code is recommended).

6. **Methodological limitation** To extract collocations in the script, the PMI and χ2 metrics were used, which, as comparison with AntConc showed, are sensitive to the size of the case. The results obtained on their basis should not be interpreted as an absolute measure of the strength of the collocation without additional filtering.


### 9. Usage example

After running the parser:

- File `borsch\_corpus.txt ` is passed to AntConc to search for collocations manually (using the "Collocates" function).

- The same file is also processed by an NLTK or spaCy script: tokenization, stopword filtering, bigram/trigram allocation, mutual information calculation (PMI) or log-likelihood.



