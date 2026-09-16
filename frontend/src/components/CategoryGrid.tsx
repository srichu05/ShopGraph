import React from 'react';
import { ArrowRight, Music2 } from 'lucide-react';
import { MOCK_CATEGORIES } from '../services/mockData';

interface CategoryGridProps {
  onSelectCategory: (categoryId: string) => void;
}

export const CategoryGrid: React.FC<CategoryGridProps> = ({ onSelectCategory }) => {
  return (
    <section id="categories" className="py-16 bg-muted/30 border-y border-border/60">
      <div className="container mx-auto px-4 sm:px-6">
        {/* Section title */}
        <div className="flex flex-col md:flex-row md:items-end justify-between mb-10">
          <div>
            <span className="text-xs font-bold uppercase tracking-wider text-primary bg-primary/10 px-2.5 py-0.5 rounded-full mb-2 inline-block">
              Ontology Explorer
            </span>
            <h2 className="font-serif text-3xl sm:text-4xl font-bold text-foreground">
              Amazon Musical Instruments Taxonomy
            </h2>
            <p className="text-sm text-muted-foreground mt-1.5 max-w-xl">
              Traverse our canonical category hierarchy. Every node connects products, brands, and
              verified reviewer graphs.
            </p>
          </div>

          <div className="mt-4 md:mt-0 flex items-center space-x-2 text-xs font-semibold text-primary">
            <Music2 className="w-4 h-4" />
            <span>6 Canonical Categories Mapped</span>
          </div>
        </div>

        {/* 6-Column Card Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {MOCK_CATEGORIES.map((cat) => (
            <div
              key={cat.id}
              onClick={() => onSelectCategory(cat.id)}
              className="group cursor-pointer bg-card rounded-2xl border border-border/80 overflow-hidden hover:border-primary/50 hover:shadow-lg transition-all duration-300 flex flex-col"
            >
              <div className="relative h-48 overflow-hidden bg-muted">
                <img
                  src={cat.image}
                  alt={cat.name}
                  className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-black/20 to-transparent" />
                <div className="absolute top-3 right-3">
                  <span className="text-[11px] font-semibold bg-white/90 text-foreground px-2.5 py-1 rounded-full shadow-sm">
                    {cat.itemCount.toLocaleString()} products
                  </span>
                </div>
                <div className="absolute bottom-3 left-4 right-4">
                  <h3 className="font-serif text-xl font-bold text-white group-hover:text-accent transition-colors">
                    {cat.name}
                  </h3>
                </div>
              </div>

              <div className="p-5 flex-1 flex flex-col justify-between">
                <p className="text-xs text-muted-foreground leading-relaxed mb-4">
                  {cat.description}
                </p>

                <div className="flex items-center justify-between pt-3 border-t border-border/50 text-xs font-medium text-foreground group-hover:text-primary transition-colors">
                  <span>Explore in Catalog</span>
                  <ArrowRight className="w-4 h-4 transform group-hover:translate-x-1 transition-transform" />
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};
