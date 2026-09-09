// ==============================================================================
// ShopGraph — Representative Multi-Hop Cypher Queries
// ==============================================================================
// These queries demonstrate the analytical and traversal capabilities of the
// ShopGraph knowledge graph without relying on materialized all-pairs edges.

// Query 1: Find products in a category (e.g., Electric Guitars)
MATCH (p:Product)-[:BELONGS_TO]->(c:Category)
WHERE c.name = 'Electric Guitars' OR c.id CONTAINS 'Electric Guitars'
RETURN p.id, p.title, p.average_rating, p.price, c.name AS category
ORDER BY p.average_rating DESC, p.rating_count DESC
LIMIT 10;

// Query 2: Find products by brand (e.g., Fender)
MATCH (p:Product)-[:BRANDED_BY]->(b:Brand)
WHERE toLower(b.name) CONTAINS 'fender'
RETURN p.id, p.title, p.average_rating, p.price, b.name AS brand
ORDER BY p.average_rating DESC
LIMIT 10;

// Query 3: Find products under a full canonical category path
MATCH (p:Product)-[:BELONGS_TO]->(c:Category)
WHERE c.id = 'Musical Instruments > Guitars > Electric Guitars > Solid Body'
RETURN p.id, p.title, p.price, p.average_rating
ORDER BY p.average_rating DESC
LIMIT 10;

// Query 4: Find products with high verified-purchase review counts
MATCH (u:User)-[:PURCHASED]->(p:Product)
WITH p, count(u) AS verified_buyer_count
MATCH (r:Review)-[:REVIEWS]->(p)
RETURN p.id, p.title, p.average_rating, verified_buyer_count, count(r) AS total_reviews
ORDER BY verified_buyer_count DESC
LIMIT 10;

// Query 5: Find users who reviewed a product along with their rating and review snippet
MATCH (u:User)-[:WROTE]->(r:Review)-[:REVIEWS]->(p:Product {id: $product_id})
RETURN u.id AS user_id, r.rating, r.title, substring(r.text, 0, 150) AS snippet, r.timestamp
ORDER BY r.helpful_votes DESC, r.timestamp DESC
LIMIT 10;

// Query 6: Multi-Hop Traversal: User -> Review -> Product -> Brand
MATCH (u:User {id: $user_id})-[:WROTE]->(r:Review)-[:REVIEWS]->(p:Product)-[:BRANDED_BY]->(b:Brand)
RETURN u.id, r.rating, r.title, p.title AS product_title, b.name AS brand_name, r.timestamp
ORDER BY r.timestamp DESC;

// Query 7: Taxonomy Traversal: Product -> Category -> Parent Category -> Root
MATCH (p:Product {id: $product_id})-[:BELONGS_TO]->(leaf:Category)
OPTIONAL MATCH path = (leaf)-[:SUB_CATEGORY_OF*1..5]->(root:Category)
WHERE root.level = 0
RETURN p.title, [n IN nodes(path) | n.name] AS hierarchy_names, [n IN nodes(path) | n.id] AS hierarchy_paths;

// Query 8: Dynamic Shared Verified Purchasers (No all-pairs edges needed!)
// Finds products with the highest overlap of verified purchasers with a target product
MATCH (p1:Product {id: $product_id})<-[:PURCHASED]-(u:User)-[:PURCHASED]->(p2:Product)
WHERE p1 <> p2
RETURN p2.id, p2.title, p2.average_rating, p2.price, count(DISTINCT u) AS shared_verified_purchasers
ORDER BY shared_verified_purchasers DESC, p2.average_rating DESC
LIMIT 10;

// Query 9: Aspect / Keyword Search in Reviews for a Product Category
MATCH (p:Product)-[:BELONGS_TO]->(c:Category)
WHERE c.id CONTAINS 'Microphones'
MATCH (r:Review)-[:REVIEWS]->(p)
WHERE r.rating >= 4.0 AND (toLower(r.text) CONTAINS 'clarity' OR toLower(r.text) CONTAINS 'warm')
RETURN p.id, p.title, p.price, p.average_rating, r.title AS review_title, substring(r.text, 0, 200) AS snippet
LIMIT 10;

// Query 10: Multi-Hop Recommendation Traversal:
// Recommend products from the same category or brand that share verified purchasers,
// returning the graph reasoning path.
MATCH (target:Product {id: $product_id})<-[:PURCHASED]-(u:User)-[:PURCHASED]->(rec:Product)
WHERE target <> rec
MATCH (rec)-[:BELONGS_TO]->(cat:Category)
MATCH (rec)-[:BRANDED_BY]->(brand:Brand)
WITH rec, cat, brand, count(DISTINCT u) AS shared_buyers
WHERE shared_buyers >= 1
RETURN rec.id AS recommended_id,
       rec.title AS recommended_title,
       rec.price AS price,
       rec.average_rating AS rating,
       cat.name AS category,
       brand.name AS brand,
       shared_buyers,
       "Connected via " + toString(shared_buyers) + " shared verified purchaser(s)" AS graph_explanation
ORDER BY shared_buyers DESC, rec.average_rating DESC
LIMIT 5;
