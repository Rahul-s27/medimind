/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './index.html',
    './src/**/*.{js,jsx,ts,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          500: '#b85c1e',
          600: '#a5521a',
        },
      },
    },
  },
  plugins: [],
}


