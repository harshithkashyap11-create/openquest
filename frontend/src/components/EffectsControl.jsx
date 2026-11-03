import { Zap } from 'lucide-react';
import { useLiteEffects } from '../hooks/useLiteEffects';
import { useI18n } from '../i18n/useI18n';
export default function EffectsControl() {
  const { t } = useI18n();
  const { preference, setPreference, lite } = useLiteEffects();
  return (
    <label
      className="effects-control"
      title={lite ? t('liteActive') : t('fullActive')}
    >
      <Zap size={16} aria-hidden="true" />
      <span className="sr-only">{t('effects')}</span>
      <select
        value={preference}
        onChange={(event) => setPreference(event.target.value)}
        aria-label={t('effects')}
      >
        <option value="auto">{t('effectsAuto')}</option>
        <option value="lite">{t('effectsLite')}</option>
        <option value="full">{t('effectsFull')}</option>
      </select>
    </label>
  );
}
