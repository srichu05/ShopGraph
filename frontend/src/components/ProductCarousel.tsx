import React, { useRef } from 'react';
import { ChevronLeft, ChevronRight, Sparkles } from 'lucide-react';
import { ProductSummary, ProductDetail } from '../types';
import { ProductCard } from './ProductCard';

interface ProductCarouselProps {
  title: string;
  subtitle?: string;
  products: (ProductSummary | ProductDetail)[];
  onSelectProduct: (product: any) => void;
  onToggleCompare: (product: any) => void;
  comparedIds: string[];
}

export const ProductCarousel: React.FC<ProductCarouselProps> = ({
  title,
  subtitle,
  products,
  onSelectProduct,
  onToggleCompare,
  comparedIds,
}) => {
  const scrollRef = useRef<HTMLDivElement>(null);

  const scroll = (direction: 'left' | 'right') => {
    if (scrollRef.current) {
      const scrollAmount = direction === 'left' ? -350 : 350;
      scrollRef.current.scrollBy({ left: scrollAmount, behavior: 'smooth' });
    }
  };

  return (
    <section className="py-14 bg-background border-b border-border/60">
      <div className="container mx-auto px-4 sm:px-6">
        {/* Header with Navigation Chevrons */}
        <div className="flex items-end justify-between mb-8">
          <div>
            <div className="inline-flex items-center space-x-1.5 text-xs font-semibold text-primary mb-1.5">
              <Sparkles className="w-3.5 h-3.5" />
              <span>Grounded Recommendations</span>
            </div>
            <h2 className="font-serif text-2xl sm:text-3xl font-bold text-foreground">
              {title}
            </h2>
            {subtitle && (
              <p className="text-xs sm:text-sm text-muted-foreground mt-1">
                {subtitle}
              </p>
            )}
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={() => scroll('left')}
              className="p-2 rounded-full border border-border bg-card hover:bg-muted text-foreground transition-colors shadow-sm"
              title="Scroll left"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <button
              onClick={() => scroll('right')}
              className="p-2 rounded-full border border-border bg-card hover:bg-muted text-foreground transition-colors shadow-sm"
              title="Scroll right"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Horizontal Carousel Track */}
        <div
          ref={scrollRef}
          className="flex space-x-5 overflow-x-auto no-scrollbar pb-4 pt-1 snap-x snap-mandatory"
        >
          {products.map((prod) => (
            <div
              key={prod.id}
              className="min-w-[280px] sm:min-w-[320px] max-w-[320px] shrink-0 snap-start"
            >
              <ProductCard
                product={prod}
                onSelect={onSelectProduct}
                onToggleCompare={onToggleCompare}
                isCompared={comparedIds.includes(prod.id)}
              />
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};
