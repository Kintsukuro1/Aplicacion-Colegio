import { useEffect, useRef } from 'react';

/**
 * Barra de búsqueda reutilizable con clear y shortcut Ctrl+K.
 *
 * Props:
 *   value       - valor controlado
 *   onChange     - callback(string)
 *   placeholder  - placeholder text
 *   label        - aria-label for input
 */
export default function SearchBar({
  value = '',
  onChange,
  placeholder = 'Buscar por nombre, email, RUT...',
  label = 'Buscar',
}) {
  const inputRef = useRef(null);

  function updateSearchQuery(e) {
    onChange?.(e.target.value);
  }

  function handleClear() {
    onChange?.('');
    inputRef.current?.focus();
  }

  // Ctrl+K para focus rápido
  useEffect(() => {
    function onKey(e) {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        inputRef.current?.focus();
        inputRef.current?.select();
      }
    }
    window.addEventListener('keydown', onKey);
    return () => {
      window.removeEventListener('keydown', onKey);
    };
  }, []);

  return (
    <div className="search-bar">
      <svg className="search-bar-icon" viewBox="0 0 20 20" fill="currentColor" width="18" height="18">
        <path
          fillRule="evenodd"
          d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z"
          clipRule="evenodd"
        />
      </svg>
      <input
        ref={inputRef}
        id="searchbar-input"
        type="text"
        value={value}
        onChange={updateSearchQuery}
        placeholder={placeholder}
        aria-label={label}
        autoComplete="off"
        spellCheck={false}
      />
      {value ? (
        <button
          type="button"
          className="search-bar-clear"
          onClick={handleClear}
          aria-label="Limpiar búsqueda"
        >
          X
        </button>
      ) : (
        <kbd className="search-bar-shortcut">Ctrl+K</kbd>
      )}
    </div>
  );
}

