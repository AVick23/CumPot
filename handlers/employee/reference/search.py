import re
import string
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional, List

# Импортируем nltk
try:
    import nltk
    nltk.data.find('tokenizers/punkt')
except (LookupError, NameError):
    import nltk
    nltk.download('punkt')

from nltk.stem import SnowballStemmer

stemmer = SnowballStemmer("russian")

STOPWORDS = {
    'и', 'в', 'на', 'с', 'по', 'из', 'за', 'под', 'над', 'без', 'для', 'от', 'к', 'у', 'о', 'об',
    'при', 'через', 'между', 'среди', 'вокруг', 'около', 'возле', 'мимо', 'вдоль', 'напротив',
    'позади', 'впереди', 'слева', 'справа', 'сверху', 'снизу', 'или', 'как', 'то', 'что', 'это',
    'так', 'же', 'быть', 'этот', 'весь', 'все', 'всё', 'один', 'другой', 'сам', 'самый', 'такой',
    'только', 'уже', 'ещё', 'если', 'когда', 'где', 'куда', 'откуда', 'зачем', 'почему', 'потому',
    'поэтому', 'итак', 'далее', 'например', 'особенно', 'кроме', 'вместе', 'вместо', 'несмотря',
    'благодаря', 'вследствие', 'этом', 'этом', 'эти', 'этих', 'этим', 'этой', 'этого', 'этом',
    'эту', 'этими', 'этих', 'этого', 'этой', 'этом', 'этом', 'эту', 'эти', 'этих', 'этим', 'этими',
    'чтоб', 'чтобы', 'будто', 'словно', 'какбы', 'точно', 'вроде', 'также', 'тоже', 'притом',
    'причём', 'зато', 'однако', 'впрочем', 'вследствие', 'ввиду', 'вроде', 'наподобие', 'касательно'
}

def tokenize(text: str) -> List[str]:
    if not text:
        return []
    text = text.translate(str.maketrans('', '', string.punctuation))
    words = text.lower().split()
    result = []
    for w in words:
        if len(w) >= 3 and w not in STOPWORDS:
            stemmed = stemmer.stem(w)
            if len(stemmed) >= 2:
                result.append(stemmed)
    return result


@dataclass
class Recipe:
    id: int = 0   # будет перезаписан при добавлении
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
        self.index = defaultdict(set)
        self.recipes: dict[int, Recipe] = {}
        self.vocabulary = set()
        self._next_id = 1

    def add_recipe(self, recipe: Recipe) -> None:
        recipe.id = self._next_id
        self._next_id += 1
        self.recipes[recipe.id] = recipe
        texts = [
            recipe.name,
            recipe.description,
            ' '.join(ing.get('name', '') for ing in recipe.ingredients),
            recipe.instruction[:300]
        ]
        for text in texts:
            if text:
                for token in tokenize(text):
                    self.index[token].add(recipe.id)
                    self.vocabulary.add(token)

    def search(self, query: str) -> List[Recipe]:
        tokens = tokenize(query)
        if not tokens:
            return []

        corrected_tokens = []
        for token in tokens:
            if token in self.vocabulary:
                corrected_tokens.append(token)
            else:
                import difflib
                matches = difflib.get_close_matches(token, list(self.vocabulary), n=1, cutoff=0.7)
                if matches:
                    corrected_tokens.append(matches[0])
                else:
                    corrected_tokens.append(token)

        result_ids = set(self.index.get(corrected_tokens[0], set()))
        for token in corrected_tokens[1:]:
            result_ids &= self.index.get(token, set())

        if not result_ids:
            for token in corrected_tokens:
                result_ids |= self.index.get(token, set())

        scored = []
        for recipe_id in result_ids:
            recipe = self.recipes[recipe_id]
            score = 0
            for token in corrected_tokens:
                if token in tokenize(recipe.name):
                    score += 3
                if any(token in tokenize(ing.get('name', '')) for ing in recipe.ingredients):
                    score += 2
                if token in tokenize(recipe.description):
                    score += 1
            scored.append((score, recipe))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [r for _, r in scored]

    def get_by_category(self, category: str) -> List[Recipe]:
        return [r for r in self.recipes.values() if r.category == category]

    def get_all_categories(self) -> List[str]:
        return sorted({r.category for r in self.recipes.values() if r.category})

    def get_recipe(self, recipe_id: int) -> Recipe | None:
        return self.recipes.get(recipe_id)


_search_index = None

def get_search_index() -> SearchIndex:
    global _search_index
    if _search_index is None:
        _search_index = SearchIndex()
    return _search_index

def get_categories() -> List[str]:
    return get_search_index().get_all_categories()