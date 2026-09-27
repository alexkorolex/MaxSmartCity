/** @type {import('stylelint').Config} */
export default {
  extends: ['stylelint-config-standard'],
  ignoreFiles: ['dist/**', 'node_modules/**'],
  rules: {
    'alpha-value-notation': null,
    'at-rule-prelude-no-invalid': null,
    'at-rule-no-unknown': [true, { ignoreAtRules: ['theme', 'custom-variant', 'apply', 'utility', 'source', 'variant'] }],
    'import-notation': null,
    'at-rule-empty-line-before': null,
    'color-function-alias-notation': null,
    'color-function-notation': null,
    'color-hex-length': null,
    'custom-property-pattern': null,
    'custom-property-empty-line-before': null,
    'declaration-block-single-line-max-declarations': null,
    'declaration-block-no-redundant-longhand-properties': null,
    'media-feature-range-notation': null,
    'no-descending-specificity': null,
    'rule-empty-line-before': null,
    'selector-class-pattern': null,
    'value-keyword-case': null,
  },
};
