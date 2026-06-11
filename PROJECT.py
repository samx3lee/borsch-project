import requests
import re
import time
from urllib.parse import urljoin
from bs4 import BeautifulSoup
import pymorphy3

# ========== НАСТРОЙКИ ==========
BASE_URL = "https://povar.ru"
SEARCH_URL = "https://povar.ru/xmlsearch"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

# Инициализация pymorphy (один раз)
print("🔧 Загрузка морфологического анализатора...")
morph = pymorphy3.MorphAnalyzer()
print("Анализатор загружен!\n")

# ========== ФУНКЦИЯ ЛЕММАТИЗАЦИИ ==========
def lemmatize_text(text):
    """
    Лемматизация текста через pymorphy3.
    Приводит все слова к начальной форме.
    """
    if not text or not isinstance(text, str):
        return ""
    
    # Приводим к нижнему регистру
    text = text.lower()
    
    # Находим все слова (только кириллица, можно с дефисом)
    words = re.findall(r'[а-яё]+(?:-[а-яё]+)?', text)
    
    lemmas = []
    for word in words:
        try:
            # Лемматизируем слово
            parsed = morph.parse(word)[0]
            lemma = parsed.normal_form
            lemmas.append(lemma)
        except:
            # Если что-то пошло не так, оставляем как есть
            lemmas.append(word)
    
    return ' '.join(lemmas)

# ========== ПАРСИНГ ПОИСКОВОЙ ВЫДАЧИ ==========
def get_recipe_links(query="борщ", max_recipes=30):
    """Собирает ссылки на рецепты с поисковой выдачи povar.ru"""
    links = []
    page = 1
    
    while len(links) < max_recipes and page <= 10:
        params = {
            "query": query,
            "page": page
        }
        print(f"  Загружаю страницу поиска {page}...")
        
        try:
            resp = requests.get(SEARCH_URL, params=params, headers=headers, timeout=10)
            soup = BeautifulSoup(resp.text, "html.parser")
            
            # Ищем все ссылки на рецепты
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if "/recipes/" in href and "recipe" in href:
                    full_url = urljoin(BASE_URL, href)
                    if full_url not in links and "?page" not in full_url:
                        # Проверяем, что это про борщ
                        link_text = a.get_text(strip=True).lower()
                        if "борщ" in link_text:
                            links.append(full_url)
                            print(f"      Найдено: {link_text[:50]}")
                            if len(links) >= max_recipes:
                                break
            
            # Проверяем наличие следующей страницы
            next_page = soup.find("a", text=re.compile(r"Следующая|>", re.I))
            if not next_page:
                break
                
            page += 1
            time.sleep(1)
            
        except Exception as e:
            print(f"    Ошибка: {e}")
            break
    
    return links[:max_recipes]

# ========== ПАРСИНГ ОДНОГО РЕЦЕПТА ==========
def parse_recipe(url):
    """Извлекает название, ингредиенты и текст приготовления с povar.ru"""
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.encoding = 'utf-8'
        soup = BeautifulSoup(resp.text, "html.parser")
        
        # --- 1. Название рецепта ---
        title_tag = soup.find("h1")
        title = title_tag.text.strip() if title_tag else "Без названия"
        
        # --- 2. Ингредиенты (блок "Состав / Ингредиенты") ---
        ingredients = []
        
        # Ищем заголовок с ингредиентами
        ingredients_header = soup.find(["h2", "h3"], string=re.compile(r"Состав|Ингредиенты", re.I))
        if ingredients_header:
            next_elem = ingredients_header.find_next()
            if next_elem:
                # Ищем список ингредиентов
                if next_elem.name == "ul":
                    for li in next_elem.find_all("li"):
                        ing_text = li.get_text(strip=True)
                        if ing_text:
                            ingredients.append(ing_text)
                else:
                    ing_list = next_elem.find("ul")
                    if ing_list:
                        for li in ing_list.find_all("li"):
                            ing_text = li.get_text(strip=True)
                            if ing_text:
                                ingredients.append(ing_text)
        
        # Запасной вариант: ищем div с классом ingredients
        if not ingredients:
            ing_block = soup.find("div", class_=re.compile(r"ingredients|composition", re.I))
            if ing_block:
                for li in ing_block.find_all("li"):
                    ing_text = li.get_text(strip=True)
                    if ing_text:
                        ingredients.append(ing_text)
        
        # --- 3. Текст приготовления ---
        cooking_steps = []
        
        # Ищем заголовок "Как приготовить"
        cooking_header = soup.find(["h2", "h3"], string=re.compile(r"Как приготовить", re.I))
        if cooking_header:
            current = cooking_header.find_next()
            while current and len(cooking_steps) < 30:
                if current.name in ["p", "div", "li"]:
                    text = current.get_text(strip=True)
                    if len(text) > 30 and not any(x in text.lower() for x in ["спасибо", "комментарий", "оценить"]):
                        cooking_steps.append(text)
                current = current.find_next()
                # Останавливаемся на следующем заголовке
                if current and current.name in ["h2", "h3"] and "похожие" not in current.text.lower():
                    break
        
        # Запасной вариант: берём все длинные параграфы
        if not cooking_steps:
            for p in soup.find_all("p"):
                text = p.get_text(strip=True)
                if len(text) > 80 and not any(x in text.lower() for x in ["спасибо", "комментарий", "калорийность"]):
                    cooking_steps.append(text)
        
        cooking_text = " ".join(cooking_steps)
        
        # --- 4. Проверка и результат ---
        if not cooking_text or len(cooking_text) < 100:
            print(f"     Пропускаем: слишком мало текста")
            return None
        
        ingredients_text = "; ".join(ingredients) if ingredients else "Не найдены"
        full_text = f"{title}\nИНГРЕДИЕНТЫ: {ingredients_text}\nПРИГОТОВЛЕНИЕ: {cooking_text}"
        
        print(f"     {title[:50]}...")
        print(f"       Ингредиентов: {len(ingredients)}, текст: {len(cooking_text)} симв.")
        
        return full_text
        
    except Exception as e:
        print(f"    Ошибка: {e}")
        return None

# ========== ЛЕММАТИЗАЦИЯ ВСЕХ РЕЦЕПТОВ ==========
def lemmatize_corpus(input_file, output_file):
    """Читает файл с рецептами, лемматизирует, сохраняет"""
    
    print(f"\n Читаю файл {input_file}...")
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Разделяем рецепты по разделителю
    recipes = re.split(r'={70,}', content)
    
    processed_recipes = []
    
    for i, recipe in enumerate(recipes, 1):
        if not recipe.strip():
            continue
        
        print(f"  Лемматизация рецепта {i}...")
        
        # Разделяем на части
        lines = recipe.strip().split('\n')
        
        title = ""
        ingredients = ""
        cooking = ""
        current_section = None
        
        for line in lines:
            if line.startswith('ИНГРЕДИЕНТЫ:'):
                current_section = 'ingredients'
                ingredients = line.replace('ИНГРЕДИЕНТЫ:', '').strip()
            elif line.startswith('ПРИГОТОВЛЕНИЕ:'):
                current_section = 'cooking'
                cooking = line.replace('ПРИГОТОВЛЕНИЕ:', '').strip()
            elif current_section == 'ingredients':
                ingredients += ' ' + line.strip()
            elif current_section == 'cooking':
                cooking += ' ' + line.strip()
            elif not title and line.strip() and not line.startswith('='):
                title = line.strip()
        
        # Лемматизируем
        title_lem = lemmatize_text(title)
        ingredients_lem = lemmatize_text(ingredients)
        cooking_lem = lemmatize_text(cooking)
        
        # Собираем обратно
        processed = f"{title_lem}\nИНГРЕДИЕНТЫ: {ingredients_lem}\nПРИГОТОВЛЕНИЕ: {cooking_lem}"
        processed_recipes.append(processed)
    
    # Сохраняем
    with open(output_file, 'w', encoding='utf-8') as f:
        for recipe in processed_recipes:
            f.write(recipe + "\n\n" + "="*70 + "\n\n")
    
    print(f"\n Сохранено {len(processed_recipes)} рецептов в {output_file}")
    return processed_recipes

# ========== ОСНОВНОЙ ЗАПУСК ==========
def main():
    print("="*60)
    print(" ПАРСИНГ И ЛЕММАТИЗАЦИЯ РЕЦЕПТОВ БОРЩА")
    print("="*60)
    
    # Шаг 1: Поиск ссылок
    print("\n Поиск рецептов борща...")
    recipe_urls = get_recipe_links("борщ", max_recipes=25)
    
    if len(recipe_urls) == 0:
        print("\n Рецепты не найдены. Проверьте подключение к интернету.")
        return
    
    print(f"\n Найдено {len(recipe_urls)} рецептов")
    
    # Шаг 2: Парсинг рецептов
    print("\n Парсинг рецептов...")
    raw_recipes = []
    
    for i, url in enumerate(recipe_urls, 1):
        print(f"\n  [{i}/{len(recipe_urls)}]")
        recipe_text = parse_recipe(url)
        if recipe_text:
            raw_recipes.append(recipe_text)
        time.sleep(0.5)
    
    # Шаг 3: Сохранение сырых рецептов
    raw_file = "borsch_corpus_raw.txt"
    with open(raw_file, "w", encoding="utf-8") as f:
        for recipe in raw_recipes:
            f.write(recipe + "\n\n" + "="*70 + "\n\n")
    
    print(f"\n Сырые рецепты сохранены в {raw_file}")
    print(f"   Всего спарсено: {len(raw_recipes)} рецептов")
    
    # Шаг 4: Лемматизация
    if raw_recipes:
        lem_file = "borsch_corpus_lem.txt"
        lemmatize_corpus(raw_file, lem_file)
        
        print("\n" + "="*60)
        print("ГОТОВО!")
        print("="*60)
        print(f"\n Файл для ANTconc: {lem_file}")
    else:
        print("\n Не удалось спарсить ни одного рецепта")

# Запускаем программу
if __name__ == "__main__":
    main()