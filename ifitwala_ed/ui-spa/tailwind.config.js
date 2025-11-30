// ifitwala_ed/ui-spa/tailwind.config.js

import frappeUiPreset from 'frappe-ui/tailwind';
import colors from 'tailwindcss/colors';

const withOpacity = (variable) => ({ opacityValue }) => {
  if (opacityValue === undefined) {
    return `rgb(var(${variable}) / 1)`;
  }
  return `rgb(var(${variable}) / ${opacityValue})`;
};

export default {
  presets: [frappeUiPreset],
  content: ['./index.html', './src/**/*.{vue,js,ts}', './node_modules/frappe-ui/src/**/*.{vue,js,ts}'],
  theme: {
    extend: {
      boxShadow: {
        inner: 'inset 0 2px 4px 0 rgb(0 0 0 / 0.05)',
      },
      opacity: { 15: '0.15', 65: '0.65', 85: '0.85' },
      colors: {
        slate: colors.slate,
        ink: withOpacity('--ink-rgb'),
        'slate-token': withOpacity('--slate-rgb'),
        canopy: withOpacity('--canopy-rgb'),
        leaf: withOpacity('--leaf-rgb'),
        moss: withOpacity('--moss-rgb'),
        sky: withOpacity('--sky-rgb'),
        sand: withOpacity('--sand-rgb'),
        clay: withOpacity('--clay-rgb'),
        jacaranda: withOpacity('--jacaranda-rgb'),
        flame: withOpacity('--flame-rgb'),
        border: withOpacity('--border-rgb'),
      },
    },
  },
  plugins: [],
};
