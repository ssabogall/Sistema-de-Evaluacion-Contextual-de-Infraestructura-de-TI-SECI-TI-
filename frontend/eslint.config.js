import js from "@eslint/js";
import tseslint from "typescript-eslint";
import reactHooks from "eslint-plugin-react-hooks";
import reactRefresh from "eslint-plugin-react-refresh";
import prettierConfig from "eslint-config-prettier";

// Deliberadamente minimo: recomendados de JS/TS + reglas de React Hooks
// (atrapan bugs reales de dependencias en useEffect/useMemo) + el plugin
// de Vite para fast refresh. Prettier maneja el formato, por eso al final
// se desactivan las reglas de estilo de ESLint que chocarian con el
// formateador (prettierConfig siempre debe ir ultimo).
export default tseslint.config(
  { ignores: ["dist", "node_modules"] },
  {
    extends: [js.configs.recommended, ...tseslint.configs.recommended],
    files: ["**/*.{ts,tsx}"],
    languageOptions: {
      ecmaVersion: 2022,
    },
    plugins: {
      "react-hooks": reactHooks,
      "react-refresh": reactRefresh,
    },
    rules: {
      ...reactHooks.configs.recommended.rules,
      "react-refresh/only-export-components": ["warn", { allowConstantExport: true }],
    },
  },
  prettierConfig,
);
