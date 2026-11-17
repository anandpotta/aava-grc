/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./src/**/*.{html,ts}'],
  theme: {
    extend: {
      colors: {
        aava:    { DEFAULT:'#6666CC', 50:'#F4F4FD', 100:'#EEEEFA', 200:'#D6D6F3', 400:'#8A8AD9', 600:'#5252B8', 700:'#43439B', 900:'#2B2B66' },
        magenta: { DEFAULT:'#CC0066', 50:'#FBE6F0', 100:'#F7CFE2', 700:'#A30052' },
        jade:    { DEFAULT:'#008567', 50:'#E2F3EE', 100:'#C7E8DE', 700:'#006B53' },
        gold:    { DEFAULT:'#FFCC00', 50:'#FFF6D6', 700:'#8A6D00' },
        ink:     { DEFAULT:'#212121', 600:'#4A4A52', 400:'#71758A', 200:'#C9CBD6' },
        shell:   { DEFAULT:'#F2F2F4', 100:'#F8F8FA' }
      },
      fontFamily: { sans: ['Aptos','Inter','Segoe UI','system-ui','sans-serif'] },
      boxShadow: { card:'0 1px 2px rgba(33,33,33,.06), 0 1px 1px rgba(33,33,33,.04)', pop:'0 12px 32px rgba(33,33,33,.14)' }
    }
  },
  plugins: []
}
