import React from 'react';
import { Sparkles, GitGraph, Search, Scale, Activity } from 'lucide-react';
import { HealthStatus } from '../types';

interface NavbarProps {
  onOpenAskAi: () => void;
  onOpenCatalog: () => void;
  compareCount: number;
  onOpenCompare: () => void;
  health: HealthStatus | null;
}

export const Navbar: React.FC<NavbarProps> = ({
  onOpenAskAi,
  onOpenCatalog,
  compareCount,
  onOpenCompare,
  health,
}) => {
  const isBackendReachable = health !== null && health.status !== 'offline';
  const isNeo4jLive = isBackendReachable && health?.services?.neo4j?.status === 'connected';
  const isDegraded = isBackendReachable && !isNeo4jLive;

  return (
    <header className="sticky top-0 z-40 w-full backdrop-blur-md bg-background/90 border-b border-border/80 transition-all duration-200">
      {/* Top status banner */}
      <div className="bg-muted/70 border-b border-border/50 text-xs py-1.5 px-4 text-muted-foreground flex items-center justify-between">
        <div className="container mx-auto flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <span
              className={`inline-block w-2 h-2 rounded-full ${
                isNeo4jLive
                  ? 'bg-secondary animate-pulse'
                  : isDegraded
                  ? 'bg-amber-500'
                  : 'bg-destructive/80'
              }`}
            />
            <span className="font-medium text-foreground">ShopGraph Engine v1.0</span>
            <span className="hidden sm:inline text-muted-foreground">
              {isNeo4jLive
                ? '• Knowledge Graph + Graph-RAG Active'
                : isDegraded
                ? '• Backend Online (Database Degraded)'
                : '• Offline Demo Fallback Active'}
            </span>
          </div>

          <div className="flex items-center space-x-3">
            <div className="flex items-center space-x-1.5 text-[11px]">
              <Activity className="w-3.5 h-3.5 text-muted-foreground" />
              <span>Neo4j:</span>
              <span
                className={`font-semibold px-1.5 py-0.5 rounded text-[10px] ${
                  isNeo4jLive
                    ? 'bg-secondary/15 text-secondary'
                    : isDegraded
                    ? 'bg-amber-500/15 text-amber-800'
                    : 'bg-accent/30 text-amber-800'
                }`}
              >
                {isNeo4jLive
                  ? 'Neo4j Live (Connected)'
                  : isDegraded
                  ? 'Neo4j Offline'
                  : 'Backend Offline (Demo Fallback)'}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Main navigation */}
      <div className="container mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
        {/* Brand */}
        <a href="#" className="flex items-center space-x-2.5 group">
          <div className="w-9 h-9 rounded-lg bg-primary flex items-center justify-center text-primary-foreground shadow-sm group-hover:scale-105 transition-transform duration-200">
            <GitGraph className="w-5 h-5 text-white" />
          </div>
          <div className="flex flex-col">
            <span className="font-serif text-xl font-bold tracking-tight text-foreground leading-none">
              ShopGraph
            </span>
            <span className="text-[10px] uppercase font-semibold tracking-wider text-muted-foreground mt-0.5">
              Explainable Graph-RAG
            </span>
          </div>
        </a>

        {/* Center navigation links */}
        <nav className="hidden md:flex items-center space-x-8 text-sm font-medium">
          <button
            onClick={onOpenCatalog}
            className="text-muted-foreground hover:text-foreground transition-colors"
          >
            Explore Gear
          </button>
          <a
            href="#categories"
            className="text-muted-foreground hover:text-foreground transition-colors"
          >
            Categories
          </a>
          <a
            href="#how-it-works"
            className="text-muted-foreground hover:text-foreground transition-colors"
          >
            How It Works
          </a>
          <a
            href="#faq"
            className="text-muted-foreground hover:text-foreground transition-colors"
          >
            Documentation
          </a>
        </nav>

        {/* Actions */}
        <div className="flex items-center space-x-2 sm:space-x-3">
          {/* Compare toggle button */}
          <button
            onClick={onOpenCompare}
            className="relative px-3 py-1.5 text-xs sm:text-sm font-medium rounded-md border border-border hover:bg-muted text-foreground flex items-center space-x-1.5 transition-colors"
          >
            <Scale className="w-4 h-4 text-muted-foreground" />
            <span className="hidden sm:inline">Compare</span>
            {compareCount > 0 && (
              <span className="w-5 h-5 rounded-full bg-primary text-primary-foreground text-[10px] font-bold flex items-center justify-center animate-in zoom-in">
                {compareCount}
              </span>
            )}
          </button>

          {/* Quick Search */}
          <button
            onClick={onOpenCatalog}
            className="p-2 rounded-md hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
            title="Search catalog"
          >
            <Search className="w-4 h-4" />
          </button>

          {/* Ask ShopGraph AI trigger */}
          <button
            onClick={onOpenAskAi}
            className="flex items-center space-x-1.5 px-3.5 py-1.5 sm:px-4 sm:py-2 text-xs sm:text-sm font-medium rounded-md bg-primary text-primary-foreground hover:opacity-95 shadow-sm transition-all duration-150 hover:shadow"
          >
            <Sparkles className="w-4 h-4" />
            <span>Ask ShopGraph</span>
          </button>
        </div>
      </div>
    </header>
  );
};
