import { useEffect, useMemo, useState } from 'react';
import I18nContext from './i18nContext';
import en from './en.json';
import hi from './hi.json';
import te from './te.json';

const dictionaries = { en, hi, te };
function getStoredLanguage() {
  try {
    const stored = localStorage.getItem('classpulse.language');
    return Object.hasOwn(dictionaries, stored) ? stored : 'en';
  } catch {
    return 'en';
  }
}

export function I18nProvider({ children }) {
  const [language, setLanguage] = useState(getStoredLanguage);

  useEffect(() => {
    try {
      localStorage.setItem('classpulse.language', language);
    } catch (error) {
      console.error('[ClassPulse i18n] Could not persist language choice', error);
    }
    document.documentElement.lang = language;
  }, [language]);

  const value = useMemo(
    () => ({
      language,
      setLanguage,
      t(key, values = {}) {
        const message = dictionaries[language]?.[key] || en[key] || key;
        return Object.entries(values).reduce(
          (translated, [name, value]) =>
            translated.replaceAll(`{${name}}`, String(value)),
          message,
        );
      },
    }),
    [language],
  );

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}
