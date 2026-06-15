import React from 'react';
import { LazyMotion, domAnimation, m } from 'framer-motion';

/**
 * Button - Componente de botón reutilizable
 * 
 * Características:
 * - Múltiples variantes (primary, secondary, danger, ghost)
 * - Tamaños (sm, md, lg)
 * - Estados (disabled, loading)
 * - Animaciones suaves
 * 
 * @param {object} props - { children, variant, size, loading, disabled, onClick, className }
 * @returns {JSX.Element}
 */
export function Button({
  children = '',
  variant = 'primary',
  size = 'md',
  loading = false,
  disabled = false,
  onClick = null,
  className = '',
  type = 'button',
}) {
  const variants = {
    primary:
      'bg-blue-600 text-white hover:bg-blue-700 active:bg-blue-800 disabled:bg-blue-300',
    secondary:
      'bg-gray-200 text-gray-900 hover:bg-gray-300 active:bg-gray-400 disabled:bg-gray-100',
    danger:
      'bg-red-600 text-white hover:bg-red-700 active:bg-red-800 disabled:bg-red-300',
    ghost: 'text-gray-700 hover:bg-gray-100 active:bg-gray-200 disabled:text-gray-400',
  };

  const sizes = {
    sm: 'px-3 py-1 text-sm',
    md: 'px-4 py-2 text-base',
    lg: 'px-6 py-3 text-lg',
  };

  return (
    <LazyMotion features={domAnimation}>
      <m.button
        whileHover={{ scale: disabled ? 1 : 1.02 }}
        whileTap={{ scale: disabled ? 1 : 0.98 }}
        type={type}
        onClick={onClick}
        disabled={disabled || loading}
        className={`rounded-lg font-medium transition inline-flex items-center gap-2 ${variants[variant]} ${sizes[size]} ${className}`}
      >
        {loading && (
          <m.span
            animate={{ rotate: 360 }}
            transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
          >
            ⟳
          </m.span>
        )}
        {children}
      </m.button>
    </LazyMotion>
  );
}



