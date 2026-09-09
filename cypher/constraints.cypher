// ==============================================================================
// ShopGraph — Neo4j Uniqueness Constraints
// ==============================================================================
// These constraints enforce entity uniqueness across all primary nodes and
// automatically create underlying B-tree indexes for high-performance lookups.
// Compatible with Neo4j 5.x and Neo4j Aura.

// 1. User uniqueness constraint
CREATE CONSTRAINT constraint_user_id IF NOT EXISTS
FOR (u:User) REQUIRE u.id IS UNIQUE;

// 2. Product uniqueness constraint (canonical parent_asin)
CREATE CONSTRAINT constraint_product_id IF NOT EXISTS
FOR (p:Product) REQUIRE p.id IS UNIQUE;

// 3. Review uniqueness constraint (deterministic hash ID)
CREATE CONSTRAINT constraint_review_id IF NOT EXISTS
FOR (r:Review) REQUIRE r.id IS UNIQUE;

// 4. Brand uniqueness constraint (normalized deterministic brand_id)
CREATE CONSTRAINT constraint_brand_id IF NOT EXISTS
FOR (b:Brand) REQUIRE b.id IS UNIQUE;

// 5. Category uniqueness constraint (canonical full breadcrumb path)
CREATE CONSTRAINT constraint_category_id IF NOT EXISTS
FOR (c:Category) REQUIRE c.id IS UNIQUE;
