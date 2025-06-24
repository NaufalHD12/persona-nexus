/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './templates/**/*.html',
    './**/templates/**/*.html'
  ],
  theme: {
    extend: {
      colors: {
        'soft-cream': '#FDFCEC',
        
        // Warna aksen tetap seperti biasa
        'primary-accent': '#FFD900',
        'secondary-accent': '#F29D35',
        
        // 'deep-brown' sekarang menjadi sebuah objek (palet warna)
        'deep-brown': {
          100: '#EAE4D6', // Paling terang
          200: '#D4CA9F',
          300: '#BBAA78', // Shade yang Anda tanyakan
          400: '#A18A58',
          500: '#877343', // Mid-tone
          600: '#746235',
          700: '#615127',
          800: '#4D4019',
          900: '#3A2F0B', // Warna asli/paling gelap
          DEFAULT: '#3A2F0B', // Ini akan menjadi nilai untuk kelas `text-deep-brown`
        },
      },
      fontFamily: {
        'poppins': ['Poppins', 'sans-serif'],
        'lato': ['Lato', 'sans-serif'],
      },
      boxShadow: {
        underline: "inset 0 -2px 0 0"
      }
    },
  },
  plugins: [
    require('@tailwindcss/forms'),
    require('@tailwindcss/typography'),
  ],
}

