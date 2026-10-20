import {themes as prismThemes} from 'prism-react-renderer';
import type {Config} from '@docusaurus/types';
import type * as Preset from '@docusaurus/preset-classic';

const config: Config = {
  title: 'OpenVoiceUI',
  tagline: 'The open-source voice AI that actually does work.',
  favicon: 'img/favicon.svg',

  future: {
    v4: true,
  },

  url: 'https://alexi5000.github.io',
  baseUrl: '/OpenVoiceUI_ClawLI/',

  organizationName: 'Alexi5000',
  projectName: 'OpenVoiceUI_ClawLI',
  trailingSlash: false,

  onBrokenLinks: 'throw',
  markdown: { hooks: { onBrokenMarkdownLinks: 'warn' } },

  i18n: {
    defaultLocale: 'en',
    locales: ['en'],
  },

  presets: [
    [
      'classic',
      {
        docs: {
          path: '../docs',
          sidebarPath: './sidebars.ts',
          routeBasePath: '/',
          editUrl: 'https://github.com/Alexi5000/OpenVoiceUI_ClawLI/edit/main/',
        },
        blog: false,
        theme: {
          customCss: './src/css/custom.css',
        },
      } satisfies Preset.Options,
    ],
  ],

  themeConfig: {
    image: 'img/social-card.jpg',
    colorMode: {
      defaultMode: 'dark',
      respectPrefersColorScheme: true,
    },
    navbar: {
      title: 'OpenVoiceUI',
      logo: {
        alt: 'OpenVoiceUI',
        src: 'img/favicon.svg',
      },
      items: [
        {
          type: 'docSidebar',
          sidebarId: 'docs',
          position: 'left',
          label: 'Docs',
        },
        {
          to: '/reference/api',
          label: 'API',
          position: 'left',
        },
        {
          href: 'https://github.com/MCERQUA/openvoiceui-plugins',
          label: 'Plugins',
          position: 'left',
        },
        {
          href: 'https://github.com/Alexi5000/OpenVoiceUI_ClawLI',
          label: 'GitHub',
          position: 'right',
        },
        {
          href: 'https://www.npmjs.com/package/openvoiceui',
          label: 'npm',
          position: 'right',
        },
      ],
    },
    footer: {
      style: 'dark',
      links: [
        {
          title: 'Docs',
          items: [
            {label: 'Getting Started', to: '/getting-started/installation'},
            {label: 'Canvas System', to: '/features/canvas-system'},
            {label: 'Plugin System', to: '/extending/plugin-system'},
            {label: 'API Reference', to: '/reference/api'},
          ],
        },
        {
          title: 'Community',
          items: [
            {label: 'Upstream Discussions', href: 'https://github.com/MCERQUA/OpenVoiceUI/discussions'},
            {label: 'Plugins Repository', href: 'https://github.com/MCERQUA/openvoiceui-plugins'},
            {label: 'Report an Issue', href: 'https://github.com/Alexi5000/OpenVoiceUI_ClawLI/issues'},
          ],
        },
        {
          title: 'More',
          items: [
            {label: 'Website', href: 'https://openvoiceui.com'},
            {label: 'npm', href: 'https://www.npmjs.com/package/openvoiceui'},
            {label: 'OpenClaw', href: 'https://openclaw.org'},
          ],
        },
      ],
      copyright: `Copyright ${new Date().getFullYear()} OpenVoiceUI Contributors. MIT Licensed.`,
    },
    prism: {
      theme: prismThemes.github,
      darkTheme: prismThemes.dracula,
      additionalLanguages: ['bash', 'json', 'python', 'yaml'],
    },
  } satisfies Preset.ThemeConfig,
};

export default config;
