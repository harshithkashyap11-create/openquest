import { Languages } from 'lucide-react';
import { useI18n } from '../i18n/useI18n';

const languages = [
  ['en', 'english'],
  ['hi', 'hindi'],
  ['te', 'telugu'],
];

export default function LanguageSelector({
  compact = false,
  labelKey = 'language',
}) {
  const { language, setLanguage, t } = useI18n();
  return (
    <label
      className={`language-control ${compact ? 'language-control-compact' : ''}`}
    >
      <Languages size={16} aria-hidden="true" />
      <span className={compact ? 'sr-only' : ''}>{t(labelKey)}</span>
      <select
        aria-label={t(labelKey)}
        value={language}
        onChange={(event) => setLanguage(event.target.value)}
      >
        {languages.map(([code, label]) => (
          <option key={code} value={code}>
            {t(label)}
          </option>
        ))}
      </select>
    </label>
  );
}
