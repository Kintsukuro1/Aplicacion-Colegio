import React from 'react';

/**
 * Badge - Componente de etiqueta/distintivo
 * 
 * Características:
 * - Múltiples variantes de color
 * - Tamaños pequeño y normal
 * - Ícono opcional
 * - Dismissible
 * 
 * @param {object} props - { children, variant, size, icon, dismissible, onDismiss }
 * @returns {JSX.Element}
 */
export function Badge({
  children = '',
  variant = 'gray',
  size = 'md',
  icon = null,
  dismissible = false,
  onDismiss = null,
}) {
  const variants = {
    gray: 'bg-gray-100 text-gray-800',
    blue: 'bg-blue-100 text-blue-800',
    green: 'bg-green-100 text-green-800',
    red: 'bg-red-100 text-red-800',
    yellow: 'bg-yellow-100 text-yellow-800',
    purple: 'bg-purple-100 text-purple-800',
    success: 'bg-green-100 text-green-800',
    warning: 'bg-yellow-100 text-yellow-800',
    error: 'bg-red-100 text-red-800',
    info: 'bg-blue-100 text-blue-800',
  };

  const sizes = {
    sm: 'px-2 py-1 text-xs',
    md: 'px-3 py-1 text-sm',
  };

  return (
    <span className={`inline-flex items-center gap-1 rounded-full font-medium ${variants[variant]} ${sizes[size]}`}>
      {icon && <span>{icon}</span>}
      <span>{children}</span>
      {dismissible && (
        <button
          onClick={onDismiss}
          className="ml-1 hover:opacity-70 transition"
          aria-label="Cerrar"
        >
          ✕
        </button>
      )}
    </span>
  );
}



