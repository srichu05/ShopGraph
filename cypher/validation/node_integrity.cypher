// ==============================================================================
// ShopGraph Validation — Node Integrity Checks
// ==============================================================================

// 1. Total counts by node label
MATCH (p:Product) WITH count(p) AS products
MATCH (u:User) WITH products, count(u) AS users
MATCH (r:Review) WITH products, users, count(r) AS reviews
MATCH (b:Brand) WITH products, users, reviews, count(b) AS brands
MATCH (c:Category) WITH products, users, reviews, brands, count(c) AS categories
RETURN products, users, reviews, brands, categories;

// 2. Check for missing or blank IDs
MATCH (p:Product) WHERE p.id IS NULL OR trim(p.id) = '' RETURN count(p) AS invalid_product_ids;
MATCH (u:User) WHERE u.id IS NULL OR trim(u.id) = '' RETURN count(u) AS invalid_user_ids;
MATCH (r:Review) WHERE r.id IS NULL OR trim(r.id) = '' RETURN count(r) AS invalid_review_ids;
MATCH (b:Brand) WHERE b.id IS NULL OR trim(b.id) = '' RETURN count(b) AS invalid_brand_ids;
MATCH (c:Category) WHERE c.id IS NULL OR trim(c.id) = '' RETURN count(c) AS invalid_category_ids;

// 3. Check that Category IDs are full canonical paths (not just leaf names)
// Path-based IDs must contain ' > ' if level > 0
MATCH (c:Category)
WHERE c.level > 0 AND NOT c.id CONTAINS ' > '
RETURN count(c) AS invalid_category_path_ids;

// 4. Check that no duplicate Category IDs exist
MATCH (c:Category)
WITH c.id AS cat_id, count(*) AS cnt
WHERE cnt > 1
RETURN cat_id, cnt LIMIT 10;
