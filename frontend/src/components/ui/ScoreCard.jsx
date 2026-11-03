import { useI18n } from '../../i18n/useI18n';
import ProgressBar from './ProgressBar';
export default function ScoreCard({ title, accuracy, correct, sample }) {
  const { t, language } = useI18n();
  const format = new Intl.NumberFormat(language, { maximumFractionDigits: 10 });
  return (
    <div className="score-tile">
      <span>{title}</span>
      <strong>
        {accuracy == null ? t('notAvailable') : `${format.format(accuracy)}%`}
      </strong>
      {accuracy != null && (
        <ProgressBar value={accuracy} label={title} animated />
      )}
      <small>
        {format.format(correct ?? 0)} / {format.format(sample ?? 0)}{' '}
        {t('observations')}
      </small>
    </div>
  );
}
