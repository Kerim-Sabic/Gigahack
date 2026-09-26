import { readFileSync } from 'node:fs';

const brand = JSON.parse(readFileSync(new URL('../../config/brand.json', import.meta.url), 'utf8'));
const escape = value => value.replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

export default {
  plugins: [{name:'product-display-name', transformIndexHtml: html => html.replace('__PRODUCT_NAME__', escape(brand.name))}],
};
