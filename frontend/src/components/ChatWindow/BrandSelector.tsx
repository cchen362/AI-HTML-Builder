import { useState, useEffect, useRef, useCallback } from 'react';
import { api } from '../../services/api';
import type { BrandProfile } from '../../types';
import './BrandSelector.css';

const DEFAULT_TEAL = '#14B8A6';

interface BrandSelectorProps {
  activeBrandId: string | null;
  onBrandChange: (brandId: string | null) => void;
  disabled?: boolean;
}

export default function BrandSelector({ activeBrandId, onBrandChange, disabled }: BrandSelectorProps) {
  const [brands, setBrands] = useState<BrandProfile[]>([]);
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  // Fetch brands on mount
  useEffect(() => {
    api.fetchBrands()
      .then(({ brands: list }) => {
        setBrands(list);
        // Validate stored selection
        if (activeBrandId && !list.some(b => b.id === activeBrandId)) {
          onBrandChange(null);
        }
      })
      .catch(() => setBrands([]));
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Close on click-outside or Escape
  useEffect(() => {
    if (!open) return;
    const handleClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false);
    };
    const timer = setTimeout(() => {
      document.addEventListener('click', handleClick);
      document.addEventListener('keydown', handleKey);
    }, 0);
    return () => {
      clearTimeout(timer);
      document.removeEventListener('click', handleClick);
      document.removeEventListener('keydown', handleKey);
    };
  }, [open]);

  const activeBrand = brands.find(b => b.id === activeBrandId) ?? null;
  const dotColor = activeBrand?.accent_color ?? DEFAULT_TEAL;
  const label = activeBrand?.name ?? 'BRAND';

  const handleSelect = useCallback((brandId: string | null) => {
    onBrandChange(brandId);
    setOpen(false);
  }, [onBrandChange]);

  // Don't render if no brands available
  if (brands.length === 0) return null;

  return (
    <div className="brand-selector" ref={ref}>
      <button
        type="button"
        className={`brand-pill${open ? ' open' : ''}`}
        onClick={() => setOpen(!open)}
        disabled={disabled}
      >
        <span className="brand-pill-dot" style={{ backgroundColor: dotColor }} />
        <span>{label}</span>
        <svg className="brand-pill-chevron" width="8" height="8" viewBox="0 0 8 8" fill="none" stroke="currentColor" strokeWidth="1.5">
          <path d="M1.5 5L4 2.5L6.5 5" />
        </svg>
      </button>

      {open && (
        <div className="brand-dropdown">
          <button
            type="button"
            className="brand-dropdown-item"
            onClick={() => handleSelect(null)}
          >
            <span className="brand-dropdown-dot" style={{ backgroundColor: DEFAULT_TEAL }} />
            <span className="brand-dropdown-name">Default</span>
            {!activeBrandId && (
              <svg className="brand-dropdown-check" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3"><path d="M20 6L9 17l-5-5"/></svg>
            )}
          </button>
          {brands.map(brand => (
            <button
              key={brand.id}
              type="button"
              className="brand-dropdown-item"
              onClick={() => handleSelect(brand.id)}
            >
              <span className="brand-dropdown-dot" style={{ backgroundColor: brand.accent_color }} />
              <span className="brand-dropdown-name">{brand.name}</span>
              {activeBrandId === brand.id && (
                <svg className="brand-dropdown-check" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3"><path d="M20 6L9 17l-5-5"/></svg>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
