"""
ShopGraph Query Understanding Layer
===================================
Parses natural-language e-commerce questions into structured constraints,
intents, and retrieval strategies.
"""

import re
from typing import List, Optional, Tuple
from app.schemas.query import QueryIntent, RetrievalStrategy, ExtractedConstraints

# Known Musical Instruments department/category keywords
CATEGORY_KEYWORDS = {
    "guitar": "Guitars",
    "electric guitar": "Electric Guitars",
    "acoustic guitar": "Acoustic Guitars",
    "bass": "Bass Guitars",
    "drum": "Drums & Percussion",
    "cymbal": "Cymbals",
    "snare": "Snare Drums",
    "microphone": "Microphones",
    "mic": "Microphones",
    "headphone": "Headphones",
    "audio interface": "Audio Interfaces",
    "amplifier": "Amplifiers",
    "amp": "Amplifiers",
    "pedal": "Effects & Pedals",
    "keyboard": "Keyboards & MIDI",
    "piano": "Digital Pianos",
    "synthesizer": "Synthesizers",
    "cable": "Cables & Interconnects",
    "stand": "Stands",
    "ukulele": "Ukuleles",
    "violin": "Violins",
    "flute": "Flutes",
    "saxophone": "Saxophones",
    "trumpet": "Brass",
    "tuner": "Tuners & Metronomes",
    "strap": "Straps",
    "strings": "Strings",
    "pick": "Picks & Pick Holders",
    "software": "Software",
}

# Known popular audio & instrument brands
KNOWN_BRANDS = [
    "Fender", "Gibson", "Ibanez", "Yamaha", "Shure", "Audio-Technica", "Boss",
    "Roland", "Behringer", "Sennheiser", "Marshall", "D'Addario", "Ernie Ball",
    "Focusrite", "PreSonus", "Mackie", "Electro-Harmonix", "Dunlop", "Korg",
    "Casio", "Donner", "Neumann", "AKG", "Samson", "Rode", "Pyle", "TC Electronic",
    "Zoom", "Hosa", "Gator", "Hercules", "Snark", "M-Audio", "Arturia"
]

# ASIN pattern: 10 alphanumeric uppercase characters starting with B (standard Amazon format)
ASIN_PATTERN = re.compile(r"\b(B0[0-9A-Z]{8})\b")


class QueryParser:
    """Robust, fast parser combining deterministic extraction with LLM grounding."""

    def parse(self, raw_query: str) -> ExtractedConstraints:
        query_text = raw_query.strip()
        query_lower = query_text.lower()

        # 1. Extract product ASINs
        product_ids = ASIN_PATTERN.findall(query_text)

        # 2. Extract Price Constraints
        price_min, price_max = self._extract_price(query_lower)

        # 3. Extract Rating Constraints
        rating_min = self._extract_rating(query_lower)

        # 4. Extract Category
        category_name = self._extract_category(query_lower)

        # 5. Extract Brand
        brand_name = self._extract_brand(query_text)

        # 6. Extract Review Aspects
        aspects = self._extract_aspects(query_lower)

        # 7. Classify Intent
        intent = self._classify_intent(query_lower, product_ids, price_min, price_max, rating_min, aspects)

        # 8. Select Optimal Retrieval Strategy
        strategy = self._select_strategy(intent, price_min, price_max, rating_min, aspects, category_name, brand_name)

        return ExtractedConstraints(
            intent=intent,
            strategy=strategy,
            category_id=None,
            category_name=category_name,
            brand_name=brand_name,
            price_min=price_min,
            price_max=price_max,
            rating_min=rating_min,
            review_aspects=aspects,
            product_ids=product_ids,
            raw_query=query_text,
        )

    def _extract_price(self, text: str) -> Tuple[Optional[float], Optional[float]]:
        """Extracts upper and lower price bounds, avoiding confusion with star ratings."""
        # Pattern: between $X and $Y
        m_between = re.search(r"between\s+\$?(\d+(?:\.\d+)?)\s+(?:and|to)\s+\$?(\d+(?:\.\d+)?)", text)
        if m_between:
            return float(m_between.group(1)), float(m_between.group(2))

        # Pattern: under / less than / below / cheaper than $X
        m_under = re.search(r"(?:under|less than|below|cheaper than|max(?:imum)? of)\s+\$?(\d+(?:\.\d+)?)(?!\s*star|\s*rating)", text)
        if m_under:
            return None, float(m_under.group(1))

        # Pattern: over / above / more than / at least $X (must have $ OR not be followed by stars/ratings)
        m_over = re.search(r"(?:over|above|more than|at least|minimum of)\s+\$(\d+(?:\.\d+)?)", text)
        if m_over:
            return float(m_over.group(1)), None

        # Pattern: $X or less
        m_or_less = re.search(r"\$?(\d+(?:\.\d+)?)\s+or\s+(?:less|cheaper|under)", text)
        if m_or_less:
            return None, float(m_or_less.group(1))

        # Pattern: $X budget
        m_budget = re.search(r"\$?(\d+(?:\.\d+)?)\s*(?:dollar|bucks|budget)", text)
        if m_budget:
            return None, float(m_budget.group(1))

        return None, None

    def _extract_rating(self, text: str) -> Optional[float]:
        """Extracts minimum rating constraints like '4 stars', 'highly rated', 'at least 4.5'."""
        m_stars = re.search(r"(?:at least|minimum|above|over)?\s*(\d(?:\.\d)?)\s*(?:star|\+?\s*stars|rating)", text)
        if m_stars:
            val = float(m_stars.group(1))
            if 1.0 <= val <= 5.0:
                return val

        if any(w in text for w in ["top rated", "highly rated", "best rated", "good ratings"]):
            return 4.0

        return None

    def _extract_category(self, text: str) -> Optional[str]:
        # Longest match first to catch 'electric guitar' before 'guitar'
        sorted_keys = sorted(CATEGORY_KEYWORDS.keys(), key=len, reverse=True)
        for key in sorted_keys:
            # Word boundary check
            if re.search(r"\b" + re.escape(key) + r"(?:s)?\b", text):
                return CATEGORY_KEYWORDS[key]
        return None

    def _extract_brand(self, text: str) -> Optional[str]:
        for brand in KNOWN_BRANDS:
            if re.search(r"\b" + re.escape(brand) + r"\b", text, re.IGNORECASE):
                return brand
        return None

    def _extract_aspects(self, text: str) -> List[str]:
        common_aspects = [
            "beginner", "warm", "clarity", "sound quality", "build quality",
            "durability", "noise", "latency", "recording", "vocal", "acoustic",
            "portable", "heavy", "sturdy", "cheap", "value", "professional",
            "practice", "live performance", "studio", "easy to use"
        ]
        found = []
        for aspect in common_aspects:
            if aspect in text:
                found.append(aspect)
        return found

    def _classify_intent(
        self,
        text: str,
        product_ids: List[str],
        p_min: Optional[float],
        p_max: Optional[float],
        r_min: Optional[float],
        aspects: List[str],
    ) -> QueryIntent:
        # Comparison
        if len(product_ids) >= 2 or "compare" in text or " vs " in text or "difference between" in text:
            return QueryIntent.COMPARISON

        # Product Explanation / Why recommended
        if re.search(r"why\s+(?:was|is|would|should)?.*(?:recommend|suggest|buy)", text):
            return QueryIntent.PRODUCT_EXPLANATION

        # Review Intelligence / Sentiment analysis
        if any(w in text for w in [
            "what do reviewers", "reviewers like", "reviewer feedback", "review themes",
            "reviews like", "complaints", "pros and cons", "negative reviews",
            "positive reviews", "feedback", "like and dislike"
        ]):
            return QueryIntent.REVIEW_INTELLIGENCE

        # Similarity Search
        if any(w in text for w in ["similar to", "alternative to", "products like", "looks like", "alternatives to"]):
            return QueryIntent.SIMILARITY_SEARCH

        # Category exploration
        if any(w in text for w in ["which brands have", "what brands make", "categories of", "subcategories", "list brands"]):
            return QueryIntent.CATEGORY_EXPLORATION

        # Recommendation
        if any(w in text for w in ["recommend", "best", "top", "suggest", "which should i buy"]):
            return QueryIntent.RECOMMENDATION

        # Graph Relationship Exploration
        if any(w in text for w in ["bought together", "shared purchaser", "who bought", "co-reviewed", "connected to"]):
            return QueryIntent.GRAPH_RELATIONSHIP_EXPLORATION

        # Default: Product search
        return QueryIntent.PRODUCT_SEARCH

    def _select_strategy(
        self,
        intent: QueryIntent,
        p_min: Optional[float],
        p_max: Optional[float],
        r_min: Optional[float],
        aspects: List[str],
        category: Optional[str],
        brand: Optional[str],
    ) -> RetrievalStrategy:
        # Explicit graph traversals (structural queries)
        if intent in (QueryIntent.CATEGORY_EXPLORATION, QueryIntent.GRAPH_RELATIONSHIP_EXPLORATION):
            return RetrievalStrategy.GRAPH_ONLY

        # Pure semantic queries with no structured constraints
        has_structured_filters = bool(p_min or p_max or r_min or brand)
        if not has_structured_filters and aspects and intent == QueryIntent.SIMILARITY_SEARCH:
            return RetrievalStrategy.VECTOR_ONLY

        # Most e-commerce queries benefit from both structured graph filters and semantic ranking
        return RetrievalStrategy.HYBRID


# Global singleton parser
query_parser = QueryParser()
