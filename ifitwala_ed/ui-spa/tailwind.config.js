import frappeUiPreset from 'frappe-ui/tailwind';

const withOpacity = (variable) => ({ opacityValue }) => {
  if (opacityValue === undefined) {
    return `rgb(var(${variable}) / 1)`;
  }
  return `rgb(var(${variable}) / ${opacityValue})`;
};

export default {
  presets: [frappeUiPreset],
  content: ['./index.html', './src/**/*.{vue,js,ts}'],
  theme: {
    extend: {
      opacity: { 15: '0.15', 65: '0.65', 85: '0.85' },
      colors: {
        ink: withOpacity('--ink-rgb'),
        slate: withOpacity('--slate-rgb'),
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
