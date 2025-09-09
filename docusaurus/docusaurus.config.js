// @ts-check
// `@type` JSDoc annotations allow editor autocompletion and type checking
// (when paired with `@ts-check`).
// There are various equivalent ways to declare your Docusaurus config.
// See: https://docusaurus.io/docs/api/docusaurus-config

import {themes as prismThemes} from 'prism-react-renderer';

// This runs in Node.js - Don't use client-side code here (browser APIs, JSX...)

/** @type {import('@docusaurus/types').Config} */
const config = {
  title: 'SkyFi MCP Server',
  tagline: 'Model Context Protocol server for satellite imagery and geospatial intelligence',
  favicon: 'img/favicon.ico',

  // Future flags, see https://docusaurus.io/docs/api/docusaurus-config#future
  future: {
    v4: true, // Improve compatibility with the upcoming Docusaurus v4
  },

  // Set the production url of your site here
  url: 'https://pskinnertech.github.io',
  // Set the /<baseUrl>/ pathname under which your site is served
  // For GitHub pages deployment, it is often '/<projectName>/'
  baseUrl: '/',

  // GitHub pages deployment config.
  // If you aren't using GitHub pages, you don't need these.
  organizationName: 'PSkinnerTech', // Usually your GitHub org/user name.
  projectName: 'SkyFi-MCP-server', // Usually your repo name.

  onBrokenLinks: 'throw',
  onBrokenMarkdownLinks: 'warn',

  // Even if you don't use internationalization, you can use this field to set
  // useful metadata like html lang. For example, if your site is Chinese, you
  // may want to replace "en" with "zh-Hans".
  i18n: {
    defaultLocale: 'en',
    locales: ['en'],
  },

  presets: [
    [
      'classic',
      /** @type {import('@docusaurus/preset-classic').Options} */
      ({
        docs: {
          sidebarPath: './sidebars.js',
          // Please change this to your repo.
          // Remove this to remove the "edit this page" links.
          editUrl:
            'https://github.com/PSkinnerTech/SkyFi-MCP-server/tree/main/docusaurus/',
        },
        blog: false, // Disable blog functionality
        theme: {
          customCss: './src/css/custom.css',
        },
      }),
    ],
  ],

  themeConfig:
    /** @type {import('@docusaurus/preset-classic').ThemeConfig} */
    ({
      // Replace with your project's social card
      image: 'img/skyfi-social-card.jpg',
      navbar: {
        title: 'MCP Server',
        logo: {
          alt: 'MCP Server Logo',
          src: 'img/logo.png',
        },
        items: [
          {
            type: 'docSidebar',
            sidebarId: 'docsSidebar',
            position: 'left',
            label: 'Documentation',
          },
          {
            href: 'https://github.com/PSkinnerTech/SkyFi-MCP-server',
            label: 'GitHub',
            position: 'right',
          },
          {
            href: 'https://skyfi.com',
            label: 'SkyFi Platform',
            position: 'right',
          },
        ],
      },
      footer: {
        style: 'dark',
        links: [
          {
            title: 'Documentation',
            items: [
              {
                label: 'Getting Started',
                to: '/',
              },
              {
                label: 'Tools Reference',
                to: '/tools/overview',
              },
              {
                label: 'MCP Protocol',
                to: '/technical/mcp-protocol',
              },
            ],
          },
          {
            title: 'SkyFi Platform',
            items: [
              {
                label: 'SkyFi Website',
                href: 'https://skyfi.com',
              },
              {
                label: 'Platform API',
                href: 'https://app.skyfi.com/platform-api',
              },
              {
                label: 'SkyFi Documentation',
                href: 'https://docs.skyfi.com',
              },
            ],
          },
          {
            title: 'Development',
            items: [
              {
                label: 'GitHub Repository',
                href: 'https://github.com/PSkinnerTech/SkyFi-MCP-server',
              },
              {
                label: 'Issues & Support',
                href: 'https://github.com/PSkinnerTech/SkyFi-MCP-server/issues',
              },
              {
                label: 'MCP Protocol',
                href: 'https://modelcontextprotocol.io',
              },
            ],
          },
          {
            title: 'Community',
            items: [
              {
                label: 'GitHub',
                href: 'https://github.com/PSkinnerTech/SkyFi-MCP-server',
              },
            ],
          },
        ],
        copyright: `Copyright © ${new Date().getFullYear()} SkyFi MCP Server. Built with Docusaurus.`,
      },
      prism: {
        theme: prismThemes.github,
        darkTheme: prismThemes.dracula,
      },
    }),
};

export default config;
