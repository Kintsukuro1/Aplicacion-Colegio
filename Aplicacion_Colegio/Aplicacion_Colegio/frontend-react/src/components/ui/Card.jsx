import React from 'react';
import { LazyMotion, domAnimation, m } from 'framer-motion';

/**
 * Card - Componente de tarjeta reutilizable
 * 
 * Características:
 * - Elevación visual con sombra hover
 * - Animación suave de entrada
 * - Variantes: default, hover-lift, interactive
 * - Responsivo
 * 
 * @param {object} props - { children, variant, onClick, className, animate }
 * @returns {JSX.Element}
 */
export function Card({
  children = null,
  variant = 'default',
  onClick = null,
  className = '',
  animate = true,
}) {
  const variants = {
    default: 'bg-white rounded-lg shadow border border-zinc-200',
    hover_lift: 'bg-white rounded-lg shadow border border-zinc-200 hover:shadow-lg hover:-translate-y-1 cursor-pointer transition-all',
    interactive: 'bg-white rounded-lg shadow-sm border border-zinc-200 hover:shadow-md active:shadow-none cursor-pointer transition-all',
  };

  const baseClass = variants[variant] || variants.default;

  return (
    <LazyMotion features={domAnimation}>
      <m.div
        initial={animate ? { opacity: 0, y: 10 } : false}
        animate={animate ? { opacity: 1, y: 0 } : false}
        whileHover={variant === 'hover_lift' ? { y: -2 } : {}}
        onClick={onClick}
        className={`${baseClass} p-4 ${className}`}
      >
        {children}
      </m.div>
    </LazyMotion>
  );
}

/**
 * CardHeader - Header de tarjeta
 */
export function CardHeader({ title = '', subtitle = '', icon = null }) {
  return (
    <div className="flex items-start justify-between mb-3">
      <div className="flex items-center gap-2">
        {icon && <span className="text-2xl">{icon}</span>}
        <div>
          {title && <h3 className="font-semibold text-zinc-900">{title}</h3>}
          {subtitle && <p className="text-sm text-zinc-500">{subtitle}</p>}
        </div>
      </div>
    </div>
  );
}

/**
 * CardBody - Cuerpo de tarjeta
 */
export function CardBody({ children = null }) {
  return <div className="text-zinc-700 text-sm">{children}</div>;
}

