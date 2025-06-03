
// ifitwala_ed/tailwind.config.js
const forms = require('@tailwindcss/forms');

module.exports = {

  /* Remove Preflight – no global resets */
  corePlugins: { preflight: false },

  /* Plugins that *only* generate class-based utilities */
  plugins: [
    forms({ strategy: 'class' }), // ⇒ .desk-tw .form-input { … }
    require('@tailwindcss/typography')({ className: 'tw-prose' })
  ],

  /*  Purge only files that belong to the Desk-TW namespace */
  content: [
    './ifitwala_ed/schedule/page/student_group_cards/**/*.{js,html}',
    './ifitwala_ed/public/js/student_group_cards.js',
    './ifitwala_ed/public/css/student_group_cards.css'
  ],

  /* Safelist any dynamic utilities you build in JS */
  safelist: [
    'bg-blue-600','hover:bg-blue-700','text-white',
    'flex','justify-center','mt-6',
    'text-center','text-2xl','font-semibold',
    'text-gray-800','text-sm','text-gray-500',
    'rounded','rounded-xl','shadow','duration-200','hover:-translate-y-1',
    'px-5','py-2'
  ],

  theme: { extend: {} }
};
