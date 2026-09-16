import React from 'react';
import { Star, Scale, Info, Check } from 'lucide-react';
import { ProductSummary, ProductDetail } from '../types';

interface ProductCardProps {
  product: ProductSummary | ProductDetail;
  onSelect: (product: any) => void;
  onToggleCompare: (product: any) => void;
  isCompared: boolean;
  score?: number;
}

export const ProductCard: React.FC<ProductCardProps> = ({
  product,
  onSelect,
  onToggleCompare,
  isCompared,
  score,
}) => {
  return (
    <div className="group bg-card rounded-xl border border-border/80 overflow-hidden hover:border-primary/40 hover:shadow-md transition-all duration-200 flex flex-col justify-between">
      {/* Product Image & Top Overlays */}
      <div
        onClick={() => onSelect(product)}
        className="relative aspect-[4/3] bg-white overflow-hidden p-3 flex items-center justify-center border-b border-border/40 cursor-pointer"
      >
        <img
          src={
            product.image_url ||
            'https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?auto=format&fit=crop&w=600&q=80'
          }
          alt={product.title}
          className="w-full h-full object-contain object-center group-hover:scale-105 transition-transform duration-300"
        />

        {/* Top Badges */}
        <div className="absolute top-2.5 left-2.5 flex flex-col gap-1 items-start">
          {product.brand_name && (
            <span className="text-[10px] uppercase font-bold tracking-wider bg-white/95 text-foreground px-2 py-0.5 rounded shadow-sm">
              {product.brand_name}
            </span>
          )}
          {score !== undefined && (
            <span className="text-[10px] font-bold bg-primary text-primary-foreground px-2 py-0.5 rounded shadow-sm">
              Match {Math.round(score * 100)}%
            </span>
          )}
        </div>

        {/* Quick Compare Button on hover */}
        <button
          onClick={(e) => {
            e.stopPropagation();
            onToggleCompare(product);
          }}
          className={`absolute top-2.5 right-2.5 p-1.5 rounded-lg text-xs font-medium shadow-sm transition-all ${
            isCompared
              ? 'bg-secondary text-white'
              : 'bg-white/90 text-foreground hover:bg-white'
          }`}
          title={isCompared ? 'Remove from comparison' : 'Add to compare'}
        >
          {isCompared ? <Check className="w-3.5 h-3.5" /> : <Scale className="w-3.5 h-3.5" />}
        </button>
      </div>

      {/* Content Section */}
      <div className="p-4 flex-1 flex flex-col justify-between">
        <div>
          <h3
            onClick={() => onSelect(product)}
            className="font-serif text-sm sm:text-base font-semibold text-foreground line-clamp-2 hover:text-primary cursor-pointer transition-colors leading-snug mb-2"
          >
            {product.title}
          </h3>

          {/* Rating */}
          <div className="flex items-center space-x-1.5 text-xs text-amber-600 mb-3">
            <Star className="w-3.5 h-3.5 fill-amber-500 text-amber-500" />
            <span className="font-semibold text-foreground">
              {product.average_rating ? product.average_rating.toFixed(1) : 'N/A'}
            </span>
            <span className="text-muted-foreground text-[11px]">
              ({product.rating_count.toLocaleString()} reviews)
            </span>
          </div>
        </div>

        {/* Price & Action Row */}
        <div className="pt-3 border-t border-border/50 flex items-center justify-between">
          <div>
            <span className="text-xs text-muted-foreground block">Price</span>
            <span className="text-base font-bold text-foreground">
              {product.price !== null && product.price !== undefined
                ? `$${product.price.toFixed(2)}`
                : 'Unlisted'}
            </span>
          </div>

          <div className="flex items-center space-x-1.5">
            <button
              onClick={() => onSelect(product)}
              className="flex items-center space-x-1 px-2.5 py-1.5 rounded-md text-xs font-medium bg-muted hover:bg-primary hover:text-primary-foreground transition-colors"
            >
              <Info className="w-3.5 h-3.5" />
              <span>Explain</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
