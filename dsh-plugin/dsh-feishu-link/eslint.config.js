// dsh-feishu-link · ESLint v9 flat config

import js from '@eslint/js'
import globals from 'globals'

export default [
  // ============ base ============
  js.configs.recommended,

  // ============ Global ignores ============
  // 注：cordis_define 函数体（host.js / client.js / package/lib/client.js）顶层 return 是必需的；
  //     ESLint v9 espree 默认不接受顶级 return；这些文件不 lint（仿 waystation 项目做法）。
  {
    ignores: [
      'node_modules/',
      'dist/',
      'coverage/',
      '.git/',
      'package/node_modules/',
      'host.js',
      'client.js',
      'package/lib/client.js',
      'docs/',
      'CHANGELOG.md',
      'README.md',
      'ACCEPTANCE.md',
      'DESIGN.md',
      'SPEC.md',
      'LICENSE',
      'ROADMAP-completion.md',
      'docs/UNINSTALL.md',
      'docs/ADR-GRILLING-UX.md',
      '.editorconfig',
      '.prettierrc',
      '.gitignore',
      '.npmignore',
      'package.json',
      'package/package.json',
    ],
  },

  // ============ 默认规则（所有 .js / .mjs / .cjs 文件 sourceType: module）============
  {
    files: ['**/*.js', '**/*.mjs', '**/*.cjs'],
    languageOptions: {
      ecmaVersion: 2023,
      sourceType: 'module',
      globals: {
        ...globals.node,
        ...globals.browser,
        console: 'readonly',
        setTimeout: 'readonly',
        clearTimeout: 'readonly',
        setInterval: 'readonly',
        clearInterval: 'readonly',
        URLSearchParams: 'readonly',
      },
    },
    rules: {
      'no-unused-vars': [
        'warn',
        { argsIgnorePattern: '^_', varsIgnorePattern: '^_' },
      ],
      'no-undef': 'error',
      'no-fallthrough': 'warn',
      'no-implicit-globals': 'error',
      'prefer-const': 'warn',
      'no-var': 'error',
      'no-empty': ['error', { allowEmptyCatch: true }],
      'no-useless-escape': 'warn',
      'no-unreachable': 'error',
      'valid-typeof': 'error',
      'no-prototype-builtins': 'off',
    },
  },

  // ============ package/lib/index.js（ESM host 半）============
  // 注：npm bundle host 半的 connection.rpc.handle 已在全局改写，
  // 但 harness.handleEvent 仍残留（残留的 bug，见 main listener 内 fireBindChanged）
  {
    files: ['package/lib/index.js'],
    languageOptions: {
      sourceType: 'module',
      globals: {
        ...globals.node,
      },
    },
  },

  // ============ tests/ 目录 ============
  {
    files: ['tests/**/*.mjs'],
    languageOptions: {
      globals: {
        ...globals.node,
      },
    },
    rules: {
      'no-console': 'off',
    },
  },

  // ============ scripts/ 目录 ============
  {
    files: ['scripts/**/*.cjs', 'scripts/**/*.mjs'],
    languageOptions: {
      globals: {
        ...globals.node,
      },
    },
    rules: {
      'no-console': 'off',
    },
  },

  // ============ lib/ 目录 ============
  {
    files: ['lib/**/*.mjs'],
    languageOptions: {
      sourceType: 'module',
      globals: {
        ...globals.node,
        URLSearchParams: 'readonly',
      },
    },
    rules: {
      'no-console': 'off',
    },
  },

  // ============ helper/ 目录 ============
  {
    files: ['helper/**/*.mjs'],
    languageOptions: {
      sourceType: 'module',
      globals: {
        ...globals.node,
        URLSearchParams: 'readonly',
      },
    },
  },
]
