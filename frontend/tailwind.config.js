/** @type {import('tailwindcss').Config} */
export default {
  // Tell Tailwind to scan all JSX files so unused styles get purged in production
  content: [
    "./index.html",
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    extend: {
      // Custom IBM-inspired color palette
      colors: {
        ibm: {
          blue:   '#0f62fe',   // IBM primary blue
          hover:  '#0353e9',   // hover state
          dark:   '#161616',   // IBM Carbon dark
          gray:   '#393939',
          light:  '#f4f4f4',
        },
      },
      fontFamily: {
        sans: ['"IBM Plex Sans"', 'ui-sans-serif', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
