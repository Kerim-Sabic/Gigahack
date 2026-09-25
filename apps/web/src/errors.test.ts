// @vitest-environment jsdom
import { afterEach, expect, it } from 'vitest';
import { errorMessage } from './errors';
import { setUiLanguage } from './translations';

afterEach(() => setUiLanguage('en'));
it('renders actionable session and conflict errors in the selected language', () => {
  setUiLanguage('ro');
  expect(errorMessage('revision_conflict')).toContain('Reîmprospătați');
  setUiLanguage('ru');
  expect(errorMessage('authentication_required')).toBe('Войдите снова.');
  expect(errorMessage('unknown_internal_code')).not.toContain('unknown_internal_code');
});
