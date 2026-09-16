import React, { useState, useMemo, useEffect } from 'react';
import { Filter, RotateCcw, Search, SlidersHorizontal, Code2, ChevronDown, ChevronUp } from 'lucide-react';
import { ProductDetail, ProductSummary } from '../types';
import { ProductCard } from './ProductCard';
import { api } from '../services/api';

interface ProductDirectoryProps {
  products: (ProductDetail | ProductSummary)[];
  onSelectProduct: (product: any) => void;
  onToggleCompare: (product: any) => void;
  comparedIds: string[];
  selectedCategory: string | null;
  onSelectCategory: (categoryId: string | null) => void;
}

const CATEGORY_LABEL_MAP: Record<string, string> = {
  cat_guitars: 'Guitars',
  cat_mics: 'Microphones',
  cat_interfaces: 'Recording',
  cat_keys: 'Keyboards',
  cat_drums: 'Drums',
  cat_studio: 'Studio',
};

export const ProductDirectory: React.FC<ProductDirectoryProps> = ({
  products: initialProducts,
  onSelectProduct,
  onToggleCompare,
  comparedIds,
  selectedCategory,
  onSelectCategory,
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedBrand, setSelectedBrand] = useState<string | null>(null);
  const [maxPrice, setMaxPrice] = useState<number>(1000);
  const [minRating, setMinRating] = useState<number>(4.0);
  const [sortBy, setSortBy] = useState<'rating' | 'price_asc' | 'price_desc'>('rating');

  const [liveProducts, setLiveProducts] = useState<ProductSummary[] | null>(null);
  const [totalFound, setTotalFound] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [cypherQuery, setCypherQuery] = useState<string | null>(null);
  const [showCypher, setShowCypher] = useState(false);

  // Dynamically query real backend when filters change
  useEffect(() => {
    let isCancelled = false;
    setLoading(true);

    const categoryFilter = selectedCategory
      ? CATEGORY_LABEL_MAP[selectedCategory] || selectedCategory
      : undefined;

    const timer = setTimeout(() => {
      api
        .searchProducts({
          query: searchQuery.trim() || '*',
          category: categoryFilter,
          brand: selectedBrand || undefined,
          min_rating: minRating,
          max_price: maxPrice,
          limit: 30,
        })
        .then((res) => {
          if (!isCancelled) {
            setLiveProducts(res.products);
            setTotalFound(res.total_found);
            setCypherQuery(res.cypher_query || null);
          }
        })
        .catch((err) => {
          console.warn('Live search error, falling back:', err);
        })
        .finally(() => {
          if (!isCancelled) setLoading(false);
        });
    }, 250);

    return () => {
      isCancelled = true;
      clearTimeout(timer);
    };
  }, [searchQuery, selectedCategory, selectedBrand, maxPrice, minRating]);

  // Determine active item list
  const activeProducts = useMemo(() => {
    const list = liveProducts !== null ? liveProducts : initialProducts;
    return [...list].sort((a, b) => {
      if (sortBy === 'rating') {
        return (b.average_rating ?? 0) - (a.average_rating ?? 0);
      }
      if (sortBy === 'price_asc') {
        return (a.price ?? 9999) - (b.price ?? 9999);
      }
      if (sortBy === 'price_desc') {
        return (b.price ?? 0) - (a.price ?? 0);
      }
      return 0;
    });
  }, [liveProducts, initialProducts, sortBy]);

  // Extract available brands from products
  const brands = useMemo(() => {
    const bSet = new Set<string>();
    (liveProducts || initialProducts).forEach((p) => {
      if (p.brand_name) bSet.add(p.brand_name);
    });
    return Array.from(bSet).sort();
  }, [liveProducts, initialProducts]);

  const resetFilters = () => {
    setSearchQuery('');
    onSelectCategory(null);
    setSelectedBrand(null);
    setMaxPrice(1000);
    setMinRating(4.0);
    setSortBy('rating');
  };

  return (
    <section id="directory" className="py-16 bg-background">
      <div className="container mx-auto px-4 sm:px-6">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-end justify-between mb-8 pb-4 border-b border-border/60">
          <div>
            <span className="text-xs font-bold uppercase tracking-wider text-primary bg-primary/10 px-2.5 py-0.5 rounded-full mb-2 inline-block">
              Product Catalog
            </span>
            <h2 className="font-serif text-3xl font-bold text-foreground">
              Filterable Gear Directory
            </h2>
            <p className="text-sm text-muted-foreground mt-1">
              Explore verified musical gear nodes retrieved directly from Neo4j with multi-dimensional criteria.
            </p>
          </div>

          <div className="mt-4 md:mt-0 flex items-center space-x-3">
            <span className="text-xs text-muted-foreground">
              Showing <strong className="text-foreground">{activeProducts.length}</strong>
              {totalFound !== null ? ` of ${totalFound}` : ''} verified nodes
            </span>
            <button
              onClick={resetFilters}
              className="inline-flex items-center space-x-1 text-xs text-muted-foreground hover:text-foreground px-2.5 py-1.5 rounded border border-border/80 hover:bg-muted transition-colors"
            >
              <RotateCcw className="w-3 h-3" />
              <span>Reset</span>
            </button>
          </div>
        </div>

        {/* Directory Layout: Sidebar + Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          {/* Facet Filters Sidebar (3 cols) */}
          <div className="lg:col-span-3 space-y-6">
            <div className="bg-card rounded-xl border border-border/80 p-5 space-y-5">
              <div className="flex items-center justify-between pb-3 border-b border-border/50">
                <span className="text-xs font-bold uppercase tracking-wider text-foreground flex items-center space-x-1.5">
                  <SlidersHorizontal className="w-3.5 h-3.5 text-primary" />
                  <span>Structured Filters</span>
                </span>
                <Filter className="w-3.5 h-3.5 text-muted-foreground" />
              </div>

              {/* Keyword Search */}
              <div>
                <label className="text-xs font-semibold text-foreground block mb-1.5">
                  Search Catalog
                </label>
                <div className="relative">
                  <Search className="w-3.5 h-3.5 text-muted-foreground absolute left-3 top-2.5" />
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="e.g. guitar, mic, interface..."
                    className="w-full text-xs bg-muted/50 border border-border/80 rounded-lg pl-8 pr-3 py-2 outline-none focus:border-primary text-foreground"
                  />
                </div>
              </div>

              {/* Category Filter */}
              <div>
                <label className="text-xs font-semibold text-foreground block mb-1.5">
                  Category Hierarchy
                </label>
                <select
                  value={selectedCategory || ''}
                  onChange={(e) => onSelectCategory(e.target.value || null)}
                  className="w-full text-xs bg-muted/50 border border-border/80 rounded-lg px-3 py-2 outline-none focus:border-primary text-foreground"
                >
                  <option value="">All Categories</option>
                  <option value="cat_guitars">Guitars & Basses</option>
                  <option value="cat_mics">Microphones & Vocals</option>
                  <option value="cat_interfaces">Audio Interfaces</option>
                  <option value="cat_keys">Keyboards & Synths</option>
                  <option value="cat_drums">Drums & Percussion</option>
                  <option value="cat_studio">Studio Monitors</option>
                </select>
              </div>

              {/* Brand Filter */}
              <div>
                <label className="text-xs font-semibold text-foreground block mb-1.5">
                  Brand Node
                </label>
                <select
                  value={selectedBrand || ''}
                  onChange={(e) => setSelectedBrand(e.target.value || null)}
                  className="w-full text-xs bg-muted/50 border border-border/80 rounded-lg px-3 py-2 outline-none focus:border-primary text-foreground"
                >
                  <option value="">All Brands ({brands.length})</option>
                  {brands.map((b) => (
                    <option key={b} value={b}>
                      {b}
                    </option>
                  ))}
                </select>
              </div>

              {/* Price Ceiling */}
              <div>
                <div className="flex justify-between text-xs font-semibold text-foreground mb-1.5">
                  <span>Max Price</span>
                  <span className="text-primary font-bold">${maxPrice}</span>
                </div>
                <input
                  type="range"
                  min={50}
                  max={1000}
                  step={25}
                  value={maxPrice}
                  onChange={(e) => setMaxPrice(Number(e.target.value))}
                  className="w-full accent-primary cursor-pointer"
                />
                <div className="flex justify-between text-[10px] text-muted-foreground mt-1">
                  <span>$50</span>
                  <span>$1,000</span>
                </div>
              </div>

              {/* Min Rating */}
              <div>
                <div className="flex justify-between text-xs font-semibold text-foreground mb-1.5">
                  <span>Min Rating</span>
                  <span className="text-amber-600 font-bold">{minRating} ★</span>
                </div>
                <div className="grid grid-cols-3 gap-1.5">
                  {[4.0, 4.3, 4.5].map((r) => (
                    <button
                      key={r}
                      onClick={() => setMinRating(r)}
                      className={`text-xs py-1 rounded border transition-colors ${
                        minRating === r
                          ? 'bg-primary/10 border-primary text-primary font-bold'
                          : 'border-border/80 hover:bg-muted text-muted-foreground'
                      }`}
                    >
                      {r}+ ★
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* Read-Only Cypher Query Inspector */}
            {cypherQuery && (
              <div className="bg-card rounded-xl border border-border/80 overflow-hidden">
                <button
                  onClick={() => setShowCypher(!showCypher)}
                  className="w-full p-3 bg-muted/40 hover:bg-muted/70 flex items-center justify-between text-xs font-semibold text-foreground transition-colors"
                >
                  <div className="flex items-center space-x-1.5">
                    <Code2 className="w-3.5 h-3.5 text-primary" />
                    <span>Cypher Query Executed</span>
                  </div>
                  {showCypher ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                </button>
                {showCypher && (
                  <div className="p-3 bg-muted/20 border-t border-border/60">
                    <pre className="font-mono text-[11px] text-muted-foreground overflow-x-auto whitespace-pre-wrap leading-relaxed">
                      {cypherQuery}
                    </pre>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Product Grid (9 cols) */}
          <div className="lg:col-span-9 space-y-4">
            {/* Sort controls */}
            <div className="flex items-center justify-between text-xs bg-card p-3 rounded-xl border border-border/60">
              <span className="text-muted-foreground">
                {loading ? 'Retrieving live nodes from Neo4j...' : 'Showing matching gear with grounded attributes'}
              </span>
              <div className="flex items-center space-x-2">
                <span className="font-semibold text-foreground">Sort By:</span>
                <select
                  value={sortBy}
                  onChange={(e) => setSortBy(e.target.value as any)}
                  className="bg-muted/60 border border-border/80 rounded px-2 py-1 outline-none text-xs text-foreground"
                >
                  <option value="rating">Highest Rated</option>
                  <option value="price_asc">Price: Low to High</option>
                  <option value="price_desc">Price: High to Low</option>
                </select>
              </div>
            </div>

            {/* Grid */}
            {loading ? (
              <div className="py-16 text-center space-y-3 bg-card rounded-2xl border border-border">
                <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin mx-auto" />
                <p className="text-sm font-medium text-foreground">Querying Neo4j knowledge graph...</p>
              </div>
            ) : activeProducts.length > 0 ? (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
                {activeProducts.map((product) => (
                  <ProductCard
                    key={product.id}
                    product={product}
                    onSelect={onSelectProduct}
                    onToggleCompare={onToggleCompare}
                    isCompared={comparedIds.includes(product.id)}
                  />
                ))}
              </div>
            ) : (
              <div className="bg-card rounded-2xl border border-dashed border-border p-12 text-center">
                <p className="text-base font-semibold text-foreground mb-1">
                  No products match your criteria
                </p>
                <p className="text-xs text-muted-foreground mb-4">
                  Try relaxing your price ceiling or selecting all categories.
                </p>
                <button
                  onClick={resetFilters}
                  className="px-4 py-2 bg-primary text-primary-foreground text-xs font-semibold rounded-lg hover:opacity-90 transition-opacity"
                >
                  Reset All Filters
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </section>
  );
};
