import { useState, useEffect } from 'react';
import { Navbar } from './components/Navbar';
import { HeroSection } from './components/HeroSection';
import { ProductCarousel } from './components/ProductCarousel';
import { CategoryGrid } from './components/CategoryGrid';
import { ProductDirectory } from './components/ProductDirectory';
import { HowItWorks } from './components/HowItWorks';
import { FAQAccordion } from './components/FAQAccordion';
import { Footer } from './components/Footer';
import { ProductModal } from './components/ProductModal';
import { AskShopGraph } from './components/AskShopGraph';
import { CompareDrawer } from './components/CompareDrawer';
import { ProductDetail, ProductSummary, HealthStatus } from './types';
import { MOCK_PRODUCTS } from './services/mockData';
import { api } from './services/api';

export function App() {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [products, setProducts] = useState<(ProductDetail | ProductSummary)[]>(MOCK_PRODUCTS);
  const [selectedProduct, setSelectedProduct] = useState<ProductDetail | ProductSummary | null>(null);
  const [comparedProducts, setComparedProducts] = useState<ProductDetail[]>([]);
  const [isAskAiOpen, setIsAskAiOpen] = useState<boolean>(false);
  const [activeAiQuery, setActiveAiQuery] = useState<string>('');
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);

  // Check health and initialize products from live backend
  useEffect(() => {
    api.getHealth().then((status) => {
      setHealth(status);
    });

    // Attempt to load products from live API
    api
      .searchProducts({ limit: 20 })
      .then((res) => {
        if (res.products && res.products.length > 0 && !res.isDemoFallback) {
          setProducts(res.products);
        }
      })
      .catch((err) => {
        console.info('Running in demo catalog mode:', err);
      });
  }, []);

  // Comparison toggle handler
  const handleToggleCompare = (product: any) => {
    setComparedProducts((prev) => {
      const exists = prev.some((p) => p.id === product.id);
      if (exists) {
        return prev.filter((p) => p.id !== product.id);
      } else {
        if (prev.length >= 4) {
          alert('You can compare up to 4 products simultaneously.');
          return prev;
        }
        return [...prev, product as ProductDetail];
      }
    });
  };

  const handleRemoveCompare = (productId: string) => {
    setComparedProducts((prev) => prev.filter((p) => p.id !== productId));
  };

  const handleClearCompare = () => {
    setComparedProducts([]);
  };

  const handleOpenAskAiWithQuery = (query: string) => {
    setActiveAiQuery(query);
    setIsAskAiOpen(true);
  };

  const handleSelectCategory = (categoryId: string | null) => {
    setSelectedCategory(categoryId);
    const el = document.getElementById('directory');
    if (el) {
      el.scrollIntoView({ behavior: 'smooth' });
    }
  };

  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col font-sans selection:bg-accent selection:text-foreground">
      {/* Sticky Top Navigation */}
      <Navbar
        onOpenAskAi={() => setIsAskAiOpen(true)}
        onOpenCatalog={() => {
          const el = document.getElementById('directory');
          if (el) el.scrollIntoView({ behavior: 'smooth' });
        }}
        compareCount={comparedProducts.length}
        onOpenCompare={() => {
          if (comparedProducts.length >= 2) {
            // Compare drawer will show button
          } else {
            alert('Select at least 2 products using the compare icon to open the comparison matrix.');
          }
        }}
        health={health}
      />

      <main className="flex-1">
        {/* Hero Section with Asymmetric Bento Grid */}
        <HeroSection
          onSearch={(q) => handleOpenAskAiWithQuery(q)}
          onOpenAskAiWithQuery={handleOpenAskAiWithQuery}
          featuredProduct={products[0]}
          onSelectProduct={setSelectedProduct}
        />

        {/* Top-Rated Recommendations Carousel */}
        <ProductCarousel
          title="Curated Studio & Stage Equipment"
          subtitle="Top Bayesian-ranked musical gear verified across thousands of customer nodes"
          products={products}
          onSelectProduct={setSelectedProduct}
          onToggleCompare={handleToggleCompare}
          comparedIds={comparedProducts.map((p) => p.id)}
        />

        {/* Musical Instrument Taxonomy Explorer */}
        <CategoryGrid onSelectCategory={handleSelectCategory} />

        {/* Filterable Catalog Directory */}
        <ProductDirectory
          products={products}
          onSelectProduct={setSelectedProduct}
          onToggleCompare={handleToggleCompare}
          comparedIds={comparedProducts.map((p) => p.id)}
          selectedCategory={selectedCategory}
          onSelectCategory={setSelectedCategory}
        />

        {/* System Architecture Explanation */}
        <HowItWorks />

        {/* Architectural FAQ Accordion */}
        <FAQAccordion />
      </main>

      {/* Directory Footer */}
      <Footer health={health} />

      {/* Product Detail Modal */}
      <ProductModal
        product={selectedProduct}
        onClose={() => setSelectedProduct(null)}
        onToggleCompare={handleToggleCompare}
        isCompared={selectedProduct ? comparedProducts.some((p) => p.id === selectedProduct.id) : false}
      />

      {/* Ask ShopGraph AI Conversational Console */}
      <AskShopGraph
        isOpen={isAskAiOpen}
        onClose={() => setIsAskAiOpen(false)}
        initialQuery={activeAiQuery}
        onSelectProduct={setSelectedProduct}
        onToggleCompare={handleToggleCompare}
        comparedIds={comparedProducts.map((p) => p.id)}
      />

      {/* Sticky Bottom Comparison Drawer */}
      <CompareDrawer
        comparedProducts={comparedProducts}
        onRemoveProduct={handleRemoveCompare}
        onClearAll={handleClearCompare}
      />
    </div>
  );
}

export default App;
