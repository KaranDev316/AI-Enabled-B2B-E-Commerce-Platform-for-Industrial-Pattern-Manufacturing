import fs from 'node:fs';
import path from 'node:path';

async function getEsbuild() {
  try {
    const wasm = await import('esbuild-wasm');
    await wasm.initialize({});
    return wasm;
  } catch (e) {
    const mod = await import('esbuild');
    return mod.default || mod;
  }
}

async function build() {
  const distDir = path.resolve('dist');
  const assetsDir = path.resolve('dist/assets');
  if (!fs.existsSync(assetsDir)) {
    fs.mkdirSync(assetsDir, { recursive: true });
  }

  const esbuild = await getEsbuild();

  // 1. Bundle JS and CSS using esbuild
  const result = await esbuild.build({
    entryPoints: ['src/main.jsx'],
    bundle: true,
    outfile: 'dist/assets/index.js',
    format: 'esm',
    target: 'es2022',
    loader: {
      '.js': 'jsx',
      '.jsx': 'jsx',
      '.png': 'dataurl',
      '.jpg': 'dataurl',
      '.svg': 'text',
    },
    define: {
      'process.env.NODE_ENV': '"production"',
      'import.meta.env.VITE_API_BASE_URL': '""',
    },
    minify: false,
    sourcemap: false,
  });

  // 2. Generate dist/index.html pointing to compiled bundle
  const htmlContent = `<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <meta name="description" content="KPC final-year BCA project development workspace" />
    <title>KPC — Development Workspace</title>
    <script type="module" crossorigin src="/assets/index.js"></script>
    <link rel="stylesheet" crossorigin href="/assets/index.css">
  </head>
  <body>
    <div id="root"></div>
  </body>
</html>
`;

  fs.writeFileSync(path.join(distDir, 'index.html'), htmlContent, 'utf-8');
  console.log('✓ Successfully built frontend bundle to dist/ (assets/index.js + assets/index.css + index.html)');
}

build().catch((err) => {
  console.error('Build error:', err);
  process.exit(1);
});
