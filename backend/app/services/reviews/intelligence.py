"""
ShopGraph Review Intelligence Service
=====================================
Analyzes customer reviews to extract rating distributions, verified purchase ratios,
aspect-based sentiment (sound quality, build quality, ease of use), and helpful quote highlights.
"""

from collections import Counter
from typing import Any, Dict, List, Optional
from app.schemas.review import (
    ReviewItem,
    RatingDistribution,
    AspectSentiment,
    ReviewIntelligenceReport,
)
from app.services.retrieval.graph_retriever import graph_retriever, GraphRetriever

ASPECT_PATTERNS = {
    "sound quality": ["sound", "tone", "audio", "clarity", "bass", "treble", "warmth", "noise", "hiss"],
    "build quality": ["build", "sturdy", "solid", "durable", "construction", "metal", "plastic", "cheaply made", "rugged"],
    "ease of use": ["easy", "simple", "intuitive", "plug and play", "setup", "complicated", "manual"],
    "value for money": ["value", "price", "affordable", "worth", "bargain", "overpriced", "expensive"],
}

POSITIVE_WORDS = {"great", "good", "excellent", "love", "perfect", "amazing", "crisp", "sturdy", "best", "fantastic", "clear", "flawless"}
NEGATIVE_WORDS = {"bad", "terrible", "poor", "broken", "noisy", "hiss", "flimsy", "broke", "worst", "disappointed", "cheap", "useless"}


class ReviewIntelligenceService:
    """Extracts qualitative and quantitative signals from review interactions."""

    def __init__(self, g_retriever: Optional[GraphRetriever] = None):
        self.retriever = g_retriever or graph_retriever

    def analyze_product_reviews(
        self,
        product_id: str,
        reviews: Optional[List[ReviewItem]] = None,
        limit: int = 50,
    ) -> ReviewIntelligenceReport:
        """Analyzes a product's reviews to generate a structured intelligence report."""
        if reviews is None:
            reviews = self.retriever.get_reviews_for_product(product_id, limit=limit)

        if not reviews:
            return ReviewIntelligenceReport(
                product_id=product_id,
                distribution=RatingDistribution(),
                aspects=[],
                top_positive_snippets=[],
                top_negative_snippets=[],
                summary="No reviews currently recorded for this product in the knowledge graph.",
            )

        # 1. Rating Distribution & Verification metrics
        star_counts: Dict[int, int] = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        verified_cnt = 0
        unverified_cnt = 0
        total_rating = 0.0

        for r in reviews:
            star = max(1, min(5, round(r.rating)))
            star_counts[star] += 1
            total_rating += r.rating
            if r.verified_purchase:
                verified_cnt += 1
            else:
                unverified_cnt += 1

        avg_rating = round(total_rating / len(reviews), 2)
        distribution = RatingDistribution(
            total_reviews=len(reviews),
            average_rating=avg_rating,
            verified_count=verified_cnt,
            unverified_count=unverified_cnt,
            star_counts=star_counts,
        )

        # 2. Aspect-based Sentiment Analysis
        aspect_matches: Dict[str, Dict[str, Any]] = {
            aspect: {"positive": 0, "negative": 0, "quotes": []} for aspect in ASPECT_PATTERNS
        }

        positive_snippets = []
        negative_snippets = []

        for r in reviews:
            text = (r.text or "").strip()
            text_lower = text.lower()
            if not text:
                continue

            # Check aspect presence
            for aspect, keywords in ASPECT_PATTERNS.items():
                if any(kw in text_lower for kw in keywords):
                    words = set(text_lower.split())
                    pos_hits = len(words & POSITIVE_WORDS)
                    neg_hits = len(words & NEGATIVE_WORDS)

                    if pos_hits >= neg_hits and r.rating >= 4.0:
                        aspect_matches[aspect]["positive"] += 1
                        if len(aspect_matches[aspect]["quotes"]) < 3 and len(text) > 30:
                            aspect_matches[aspect]["quotes"].append(text[:150] + ("..." if len(text) > 150 else ""))
                    elif neg_hits > pos_hits and r.rating <= 2.0:
                        aspect_matches[aspect]["negative"] += 1
                        if len(aspect_matches[aspect]["quotes"]) < 3 and len(text) > 30:
                            aspect_matches[aspect]["quotes"].append(text[:150] + ("..." if len(text) > 150 else ""))

            # Top snippets
            if r.rating >= 4.5 and len(text) > 40 and len(positive_snippets) < 4:
                positive_snippets.append(text[:180] + ("..." if len(text) > 180 else ""))
            elif r.rating <= 2.0 and len(text) > 40 and len(negative_snippets) < 4:
                negative_snippets.append(text[:180] + ("..." if len(text) > 180 else ""))

        aspect_sentiments: List[AspectSentiment] = []
        for aspect, data in aspect_matches.items():
            tot = data["positive"] + data["negative"]
            if tot > 0:
                sentiment = "positive" if data["positive"] >= data["negative"] else "negative"
                aspect_sentiments.append(AspectSentiment(
                    aspect=aspect,
                    sentiment=sentiment,
                    mention_count=tot,
                    sample_quotes=data["quotes"],
                ))

        # Overall summary text
        verif_pct = (verified_cnt / len(reviews)) * 100 if reviews else 0
        summary = (
            f"Analyzed {len(reviews)} reviews ({verif_pct:.1f}% verified purchases). "
            f"Average score is {avg_rating}/5.0 with {star_counts[5] + star_counts[4]} positive reviews (4-5 stars) "
            f"and {star_counts[1] + star_counts[2]} critical reviews (1-2 stars)."
        )

        return ReviewIntelligenceReport(
            product_id=product_id,
            distribution=distribution,
            aspects=aspect_sentiments,
            top_positive_snippets=positive_snippets,
            top_negative_snippets=negative_snippets,
            summary=summary,
        )


review_intelligence = ReviewIntelligenceService()
