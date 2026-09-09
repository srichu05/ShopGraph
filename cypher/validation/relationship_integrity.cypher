// ==============================================================================
// ShopGraph Validation — Relationship Integrity Checks
// ==============================================================================

// 1. Total counts by relationship type
MATCH ()-[r:WROTE]->() WITH count(r) AS wrote_count
MATCH ()-[r:REVIEWS]->() WITH wrote_count, count(r) AS reviews_count
MATCH ()-[r:PURCHASED]->() WITH wrote_count, reviews_count, count(r) AS purchased_count
MATCH ()-[r:BRANDED_BY]->() WITH wrote_count, reviews_count, purchased_count, count(r) AS branded_count
MATCH ()-[r:BELONGS_TO]->() WITH wrote_count, reviews_count, purchased_count, branded_count, count(r) AS belongs_count
MATCH ()-[r:SUB_CATEGORY_OF]->() WITH wrote_count, reviews_count, purchased_count, branded_count, belongs_count, count(r) AS subcategory_count
RETURN wrote_count, reviews_count, purchased_count, branded_count, belongs_count, subcategory_count;

// 2. Orphan Review Check: Every Review MUST have exactly one author (User) and one target (Product)
MATCH (r:Review)
WHERE NOT (r)<-[:WROTE]-(:User)
RETURN count(r) AS reviews_without_user;

MATCH (r:Review)
WHERE NOT (r)-[:REVIEWS]->(:Product)
RETURN count(r) AS reviews_without_product;

// 3. Category Hierarchy Check: Every subcategory (level > 0) MUST connect to its parent category
MATCH (c:Category)
WHERE c.level > 0 AND NOT (c)-[:SUB_CATEGORY_OF]->(:Category)
RETURN count(c) AS orphaned_categories;

// 4. Product Category Check: Every product should connect to a leaf category
MATCH (p:Product)
WHERE NOT (p)-[:BELONGS_TO]->(:Category)
RETURN count(p) AS products_without_category;

// 5. Product Brand Check: Products with brand_id should connect to Brand
MATCH (p:Product)
WHERE p.brand_id IS NOT NULL AND NOT (p)-[:BRANDED_BY]->(:Brand)
RETURN count(p) AS products_missing_brand_rel;
