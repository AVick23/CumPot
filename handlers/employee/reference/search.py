import re
import difflib

from collections import defaultdict
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Set


STOPWORDS = {
    "и", "в", "на", "с", "по", "из", "за", "под", "над", "без", "для", "от", "к", "у", "о", "об",
    "при", "через", "между", "среди", "вокруг", "около", "возле", "мимо", "вдоль", "напротив",
    "позади", "впереди", "слева", "справа", "сверху", "снизу", "или", "как", "то", "что", "это",
    "так", "же", "быть", "этот", "весь", "все", "всё", "один", "другой", "сам", "самый", "такой",
    "только", "уже", "ещё", "если", "когда", "где", "куда", "откуда", "зачем", "почему", "потому",
    "поэтому", "итак", "далее", "например", "особенно", "кроме", "вместе", "вместо", "несмотря",
    "благодаря", "вследствие", "этом", "эти", "этих", "этим", "этой", "этого", "эту", "этими",
    "чтоб", "чтобы", "будто", "словно", "точно", "вроде", "также", "тоже", "притом", "причём",
    "зато", "однако", "впрочем", "ввиду", "наподобие", "касательно",
}

_RUSSIAN_SUFFIXES = (
    "иями", "ями", "ами", "иях", "ях", "ах",
    "овать", "евать", "ивать", "ывать",
    "ается", "ется", "ются", "аются", "яется",
    "ует", "ют", "ат", "ят", "ет", "ут",
    "ла", "ло", "ли", "ть", "ти", "чь",
    "ый", "ий", "ая", "яя", "ое", "ее", "ые", "ие",
    "ую", "юю", "ей", "ой", "ом", "ем",
    "ам", "ям", "ов", "ев",
    "ия", "иям", "иях",
    "е", "а", "я", "о", "у", "ы", "и", "ь",
)

_RUSSIAN_SUFFIXES_SORTED = sorted(_RUSSIAN_SUFFIXES, key=len, reverse=True)


def _stem(word: str) -> str:
    """
    Упрощённый русский стеммер.
    Не идеально лингвистически, но достаточно для поиска по рецептам.
    """
    for suffix in _RUSSIAN_SUFFIXES_SORTED:
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            return word[:-len(suffix)]

    return word


def tokenize(text: str) -> List[str]:
    """
    Разбивает текст на нормализованные токены.
    """
    if not text:
        return []

    text = text.lower().replace("ё", "е")

    words = re.findall(r"[a-zа-я0-9]+", text)
    result = []

    for word in words:
        if word.isdigit():
            if len(word) >= 1:
                result.append(word)
            continue

        if len(word) < 2:
            continue

        if word in STOPWORDS:
            continue

        stemmed = _stem(word)

        if len(stemmed) >= 2:
            result.append(stemmed)

    return result


@dataclass
class Recipe:
    id: int = 0
    name: str = ""
    category: str = ""
    subcategory: str = ""
    volume: str = ""
    ingredients: List[dict] = field(default_factory=list)
    instruction: str = ""
    description: str = ""
    shelf_life: Optional[int] = None
    source_file: str = ""


@dataclass
class ShelfLifeItem:
    id: int = 0
    name: str = ""
    category: str = ""
    subcategory: str = ""
    shelf_life_days: int = 0
    location: str = ""


class SearchIndex:
    def __init__(self):
        self.index: Dict[str, Set[int]] = defaultdict(set)
        self.recipes: Dict[int, Recipe] = {}
        self.vocabulary: Set[str] = set()
        self._fields: Dict[int, Dict[str, Set[str]]] = {}
        self._next_id = 1

    def add_recipe(self, recipe: Recipe) -> None:
        recipe.id = self._next_id
        self._next_id += 1

        self.recipes[recipe.id] = recipe

        name_tokens = set(tokenize(recipe.name))

        ingredient_tokens = set()

        for ingredient in recipe.ingredients:
            ingredient_tokens.update(
                tokenize(ingredient.get("name", ""))
            )

        category_tokens = set(tokenize(recipe.category))
        category_tokens.update(tokenize(recipe.subcategory))

        description_tokens = set(tokenize(recipe.description))
        instruction_tokens = set(tokenize(recipe.instruction))

        all_tokens = (
            name_tokens
            | ingredient_tokens
            | category_tokens
            | description_tokens
            | instruction_tokens
        )

        self._fields[recipe.id] = {
            "name": name_tokens,
            "ingredients": ingredient_tokens,
            "category": category_tokens,
            "description": description_tokens,
            "instruction": instruction_tokens,
        }

        for token in all_tokens:
            self.index[token].add(recipe.id)
            self.vocabulary.add(token)

    def get_recipe(self, recipe_id: int) -> Recipe | None:
        return self.recipes.get(recipe_id)

    def get_by_category(self, category: str) -> List[Recipe]:
        recipes = [
            recipe
            for recipe in self.recipes.values()
            if recipe.category == category
        ]

        return sorted(recipes, key=lambda recipe: recipe.name.lower())

    def get_all_categories(self) -> List[str]:
        return sorted(
            {
                recipe.category
                for recipe in self.recipes.values()
                if recipe.category
            }
        )

    def get_category_counts(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}

        for recipe in self.recipes.values():
            if not recipe.category:
                continue

            counts[recipe.category] = counts.get(recipe.category, 0) + 1

        return counts

    def _expand_token(self, token: str) -> List[str]:
        """
        Если токена нет в словаре — пробуем найти похожий.
        """
        if token in self.vocabulary:
            return [token]

        matches = difflib.get_close_matches(
            token,
            list(self.vocabulary),
            n=1,
            cutoff=0.75,
        )

        if matches:
            return [matches[0]]

        return []

    def search(self, query: str, limit: int = 50) -> List[Recipe]:
        raw_query = (query or "").lower().replace("ё", "е").strip()
        tokens = tokenize(query)

        if not raw_query or not tokens:
            return []

        expanded_tokens: List[str] = []

        for token in tokens:
            matches = self._expand_token(token)

            if matches:
                expanded_tokens.extend(matches)
            else:
                expanded_tokens.append(token)

        expanded_tokens = list(dict.fromkeys(expanded_tokens))

        candidates: Set[int] = set()

        for token in expanded_tokens:
            candidates |= self.index.get(token, set())

        # Fallback: если по стеммам ничего не нашли,
        # ищем прямым вхождением сырых слов.
        if not candidates:
            raw_tokens = re.findall(r"[a-zа-яё0-9]+", raw_query)

            for recipe in self.recipes.values():
                ingredients_text = " ".join(
                    ingredient.get("name", "")
                    for ingredient in recipe.ingredients
                )

                haystack = " ".join(
                    [
                        recipe.name.lower().replace("ё", "е"),
                        recipe.description.lower().replace("ё", "е"),
                        ingredients_text.lower().replace("ё", "е"),
                    ]
                )

                if any(raw_token in haystack for raw_token in raw_tokens):
                    candidates.add(recipe.id)

        if not candidates:
            return []

        scored = []

        for recipe_id in candidates:
            recipe = self.recipes.get(recipe_id)

            if not recipe:
                continue

            fields = self._fields.get(recipe_id, {})

            name_tokens = fields.get("name", set())
            ingredient_tokens = fields.get("ingredients", set())
            category_tokens = fields.get("category", set())
            description_tokens = fields.get("description", set())
            instruction_tokens = fields.get("instruction", set())

            matched_tokens = set()
            score = 0.0

            for token in expanded_tokens:
                if token in name_tokens:
                    score += 6
                    matched_tokens.add(token)

                if token in ingredient_tokens:
                    score += 4
                    matched_tokens.add(token)

                if token in category_tokens:
                    score += 3
                    matched_tokens.add(token)

                if token in description_tokens:
                    score += 2
                    matched_tokens.add(token)

                if token in instruction_tokens:
                    score += 1
                    matched_tokens.add(token)

            if raw_query and raw_query in recipe.name.lower().replace("ё", "е"):
                score += 10

            if raw_query and raw_query in recipe.description.lower().replace("ё", "е"):
                score += 3

            if expanded_tokens:
                score += (len(matched_tokens) / len(expanded_tokens)) * 4

            scored.append((score, recipe))

        scored.sort(key=lambda item: (-item[0], item[1].name.lower()))

        return [recipe for _, recipe in scored[:limit]]


_search_index: SearchIndex | None = None


def get_search_index() -> SearchIndex:
    global _search_index

    if _search_index is None:
        _search_index = SearchIndex()

    return _search_index


def reset_search_index() -> SearchIndex:
    global _search_index

    _search_index = SearchIndex()

    return _search_index


def get_categories() -> List[str]:
    return get_search_index().get_all_categories()


def get_category_counts() -> Dict[str, int]:
    return get_search_index().get_category_counts()