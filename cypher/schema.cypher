// ==============================================================================
// ShopGraph — Neo4j Schema Indexes
// ==============================================================================
// Indexes supporting common structured search, filtering, and traversal patterns.
// Constraints from constraints.cypher already provide unique indexes for .id fields.

// Product search and filter indexes
CREATE INDEX index_product_title IF NOT EXISTS
FOR (p:Product) ON (p.title);

CREATE INDEX index_product_price IF NOT EXISTS
FOR (p:Product) ON (p.price);

CREATE INDEX index_product_rating IF NOT EXISTS
FOR (p:Product) ON (p.average_rating);

CREATE INDEX index_product_main_category IF NOT EXISTS
FOR (p:Product) ON (p.main_category);

// Review filter and sorting indexes
CREATE INDEX index_review_rating IF NOT EXISTS
FOR (r:Review) ON (r.rating);

CREATE INDEX index_review_timestamp IF NOT EXISTS
FOR (r:Review) ON (r.timestamp);

CREATE INDEX index_review_variant IF NOT EXISTS
FOR (r:Review) ON (r.variant_asin);

CREATE INDEX index_review_verified IF NOT EXISTS
FOR (r:Review) ON (r.verified_purchase);

// Brand and Category search indexes
CREATE INDEX index_brand_name IF NOT EXISTS
FOR (b:Brand) ON (b.name);

CREATE INDEX index_category_name IF NOT EXISTS
FOR (c:Category) ON (c.name);

CREATE INDEX index_category_level IF NOT EXISTS
FOR (c:Category) ON (c.level);
