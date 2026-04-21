import { ALERT_STYLES } from '../utils/constants';

export default function AlertBadge({ alert }) {
  if (!alert || !alert.alert_type) return null;
  const style = ALERT_STYLES[alert.alert_type] || ALERT_STYLES.QUESTIONABLE;
  return (
    <span
      title={alert.headline || alert.alert_type}
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold ${style.bg} ${style.text}`}
    >
      {style.label}
    </span>
  );
}