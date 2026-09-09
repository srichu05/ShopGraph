// ==============================================================================
// ShopGraph Validation — Semantic & Boundary Checks
// ==============================================================================

// 1. Verified Purchase Semantics:
// A user must ONLY have a PURCHASED edge if verified_purchase is true
MATCH (u:User)-[pur:PURCHASED]->(p:Product)
WHERE pur.verified IS NULL OR pur.verified = false
RETURN count(pur) AS invalid_unverified_purchases;

// 2. Price Semantics:
// Missing prices must be NULL, never $0.00 or free
MATCH (p:Product)
WHERE p.price = 0 OR p.price = 0.0
RETURN count(p) AS suspicious_zero_prices;

// Check products with NULL price
MATCH (p:Product)
WHERE p.price IS NULL
RETURN count(p) AS products_with_null_price;

// 3. Variant Semantics:
// Product.id must be parent_asin. Review.variant_asin must be populated.
MATCH (r:Review)
WHERE r.variant_asin IS NULL
RETURN count(r) AS reviews_missing_variant_asin;

// Confirm that variant ASINs distinct from parent_asin did not become orphan Product nodes
MATCH (r:Review)-[:REVIEWS]->(p:Product)
WHERE r.variant_asin <> p.id
RETURN count(DISTINCT r.variant_asin) AS unique_child_asins_in_reviews;

// 4. Boundary Check: Ensure NO illegal all-pairs edges were materialized
MATCH ()-[r:CO_PURCHASED_WITH]->() RETURN count(r) AS forbidden_co_purchased;
MATCH ()-[r:BOUGHT_TOGETHER]->() RETURN count(r) AS forbidden_bought_together;
MATCH ()-[r:SIMILAR_TO]->() RETURN count(r) AS materialized_similar_to;
