// @ts-check

// This runs in Node.js - Don't use client-side code here (browser APIs, JSX...)

/**
 * Creating a sidebar enables you to:
 - create an ordered group of docs
 - render a sidebar for each doc of that group
 - provide next/previous navigation

 The sidebars can be generated from the filesystem, or explicitly defined here.

 Create as many sidebars as you want.

 @type {import('@docusaurus/plugin-content-docs').SidebarsConfig}
 */
const sidebars = {
  // Main documentation sidebar - comprehensive structure
  docsSidebar: [
    'intro',
    {
      type: 'category',
      label: 'Getting Started',
      items: [
        'getting-started/quick-start',
        'getting-started/installation',
        'getting-started/verification',
      ],
    },
    {
      type: 'category',
      label: 'MCP Client Setup',
      items: [
        'setup/overview',
        'setup/claude-desktop',
        'setup/cursor-ai',
        'setup/windsurf',
        'setup/vscode',
      ],
    },
    {
      type: 'category',
      label: 'Tools Reference',
      items: [
        'tools/overview',
        {
          type: 'category',
          label: 'SkyFi Satellite Tools',
          items: [
            'tools/skyfi/overview',
            // Individual tool pages will be added
          ],
        },
        {
          type: 'category',
          label: 'OpenStreetMap Tools',
          items: [
            'tools/osm/overview',
            // Individual tool pages will be added
          ],
        },
      ],
    },
    {
      type: 'category',
      label: 'Legacy Tutorial',
      collapsed: true,
      items: [
        'tutorial-basics/create-a-document',
        'tutorial-basics/create-a-blog-post',
        'tutorial-basics/markdown-features',
        'tutorial-basics/deploy-your-site',
        'tutorial-basics/congratulations',
      ],
    },
    {
      type: 'category',
      label: 'Advanced',
      collapsed: true,
      items: [
        'tutorial-extras/manage-docs-versions',
        'tutorial-extras/translate-your-site',
      ],
    },
  ],
};

export default sidebars;
