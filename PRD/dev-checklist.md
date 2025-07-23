# Development Setup Checklist

## Prerequisites
- [ ] Node.js 18+ installed
- [ ] Docker Desktop installed
- [ ] Git configured
- [ ] Code editor with TypeScript support (VS Code recommended)
- [ ] Postman or similar API testing tool
- [ ] Access to SkyFi API key for testing

## Project Initialization
- [ ] Create new repository: `skyfi-mcp-server`
- [ ] Initialize Node.js project: `npm init -y`
- [ ] Set up TypeScript:
  ```bash
  npm install -D typescript @types/node @types/express
  npx tsc --init
  ```
- [ ] Configure `tsconfig.json`:
  ```json
  {
    "compilerOptions": {
      "target": "ES2022",
      "module": "commonjs",
      "outDir": "./dist",
      "rootDir": "./src",
      "strict": true,
      "esModuleInterop": true,
      "skipLibCheck": true,
      "forceConsistentCasingInFileNames": true
    }
  }
  ```

## Core Dependencies
- [ ] Install MCP SDK: `npm install @modelcontextprotocol/sdk`
- [ ] Install server framework:
  ```bash
  npm install express cors helmet compression body-parser
  npm install -D @types/cors @types/compression
  ```
- [ ] Install utilities:
  ```bash
  npm install dotenv axios winston joi uuid
  npm install -D @types/uuid
  ```
- [ ] Install SSE support: `npm install express-sse`

## Development Dependencies
- [ ] Testing framework:
  ```bash
  npm install -D jest @types/jest ts-jest supertest @types/supertest
  ```
- [ ] Linting and formatting:
  ```bash
  npm install -D eslint @typescript-eslint/parser @typescript-eslint/eslint-plugin
  npm install -D prettier eslint-config-prettier
  ```
- [ ] Development tools:
  ```bash
  npm install -D nodemon ts-node
  npm install -D concurrently
  ```

## Project Structure
- [ ] Create directory structure:
  ```
  skyfi-mcp-server/
  ├── src/
  │   ├── index.ts
  │   ├── server.ts
  │   ├── config/
  │   │   ├── index.ts
  │   │   └── constants.ts
  │   ├── middleware/
  │   │   ├── auth.ts
  │   │   ├── errorHandler.ts
  │   │   └── rateLimiter.ts
  │   ├── tools/
  │   │   ├── skyfi/
  │   │   ├── osm/
  │   │   └── weather/
  │   ├── services/
  │   │   ├── skyfiApi.ts
  │   │   ├── billing.ts
  │   │   └── cache.ts
  │   ├── utils/
  │   │   ├── logger.ts
  │   │   └── validators.ts
  │   └── types/
  │       └── index.ts
  ├── tests/
  ├── docs/
  ├── scripts/
  ├── docker/
  └── k8s/
  ```

## Configuration Files
- [ ] Create `.env.example`:
  ```env
  NODE_ENV=development
  PORT=3000
  SKYFI_API_URL=https://app.skyfi.com/platform-api
  SKYFI_API_KEY=sk-development-key
  OPENWEATHER_API_KEY=your-key
  REDIS_URL=redis://localhost:6379
  LOG_LEVEL=debug
  ```
- [ ] Create `.gitignore`:
  ```
  node_modules/
  dist/
  .env
  .env.local
  *.log
  .DS_Store
  coverage/
  .nyc_output/
  ```
- [ ] Create `package.json` scripts:
  ```json
  {
    "scripts": {
      "dev": "nodemon",
      "build": "tsc",
      "start": "node dist/index.js",
      "test": "jest",
      "test:watch": "jest --watch",
      "lint": "eslint src/**/*.ts",
      "format": "prettier --write src/**/*.ts"
    }
  }
  ```

## Local Services Setup
- [ ] Start Redis container:
  ```bash
  docker run -d -p 6379:6379 --name skyfi-redis redis:alpine
  ```
- [ ] Create local SkyFi credentials:
  ```bash
  mkdir -p ~/.skyfi
  echo '{"api_key": "sk-test-key", "tier": "pro"}' > ~/.skyfi/credentials.json
  ```
- [ ] Set up local SSL (for testing):
  ```bash
  openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes
  ```

## IDE Configuration
- [ ] VS Code extensions:
  - [ ] ESLint
  - [ ] Prettier
  - [ ] TypeScript Hero
  - [ ] REST Client
  - [ ] Docker
- [ ] Create `.vscode/settings.json`:
  ```json
  {
    "editor.formatOnSave": true,
    "editor.defaultFormatter": "esbenp.prettier-vscode",
    "editor.codeActionsOnSave": {
      "source.fixAll.eslint": true
    }
  }
  ```

## Git Setup
- [ ] Initialize git: `git init`
- [ ] Create initial commit:
  ```bash
  git add .
  git commit -m "Initial MCP server setup"
  ```
- [ ] Add remote origin
- [ ] Create development branch: `git checkout -b develop`

## Verification
- [ ] Run TypeScript compiler: `npm run build`
- [ ] Start development server: `npm run dev`
- [ ] Access health endpoint: `curl http://localhost:3000/health`
- [ ] Run tests: `npm test`
- [ ] Check linting: `npm run lint`

## Documentation Setup
- [ ] Create README.md with setup instructions
- [ ] Create CONTRIBUTING.md
- [ ] Create API.md for endpoint documentation
- [ ] Set up Swagger/OpenAPI spec
- [ ] Create example requests collection