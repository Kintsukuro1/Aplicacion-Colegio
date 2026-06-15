/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './templates/**/*.html',
    './static/js/**/*.js',
  ],
  corePlugins: {
    preflight: false,
  },
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      colors: {
        premium: {
          bg: '#f6f8fb',
          surface: '#ffffff',
          soft: '#eef3f9',
          line: '#dbe4ef',
          text: '#233245',
          muted: '#6c7f95',
          primary: '#7b9acc',
          primaryStrong: '#6789bf',
          success: '#7fb89a',
          warning: '#d7b072',
          danger: '#d18b96'
        },
      },
      boxShadow: {
        soft: '0 6px 18px rgba(31, 52, 73, 0.08)',
        panel: '0 2px 8px rgba(31, 52, 73, 0.06)',
      },
      borderRadius: {
        xl2: '1rem',
      },
      transitionDuration: {
        250: '250ms',
      },
    },
  },
  plugins: [],
};
