import styles from './PodiumSlot.module.css';

const POSITION_CONFIG = {
  1: {
    ringColor: 'var(--color-ring-gold)',
    badgeColor: 'var(--color-rank-badge-1)',
    blockColor: 'var(--color-podium-gold)',
    numeralColor: 'var(--color-podium-gold-text)',
    blockHeight: 120,
  },
  2: {
    ringColor: 'var(--color-ring-silver)',
    badgeColor: 'var(--color-rank-badge-2)',
    blockColor: 'var(--color-podium-silver)',
    numeralColor: 'var(--color-podium-silver-text)',
    blockHeight: 72,
  },
  3: {
    ringColor: 'var(--color-ring-bronze)',
    badgeColor: 'var(--color-rank-badge-3)',
    blockColor: 'var(--color-podium-bronze)',
    numeralColor: 'var(--color-podium-bronze-text)',
    blockHeight: 60,
  },
};

export function PodiumSlot({ employee, position, hidden }) {
  const config = POSITION_CONFIG[position];

  return (
    <div
      className={`${styles.slot} ${position === 1 ? styles.slotFirst : ''}`}
      style={hidden ? { display: 'none' } : undefined}
    >
      <div className={styles.info}>
        <div className={styles.avatarWrapper}>
          <img
            src={employee.avatar}
            alt={employee.name}
            className={styles.avatar}
            style={{ borderColor: config.ringColor }}
          />
          <span
            className={styles.rankBadge}
            style={{ backgroundColor: config.badgeColor }}
          >
            {position}
          </span>
        </div>

        <p className={styles.name}>{employee.name}</p>
        <p className={styles.jobTitle}>
          {employee.jobTitle} ({employee.department})
        </p>

        <div className={styles.score}>
          <svg width="16" height="16" viewBox="0 0 16 16" fill="var(--color-accent-blue)" aria-hidden="true">
            <path d="M8 1l1.8 3.6L14 5.3l-3 2.9.7 4.1L8 10.4l-3.7 1.9.7-4.1-3-2.9 4.2-.7z" />
          </svg>
          <span className={styles.scoreValue}>{employee.filteredTotal}</span>
        </div>
      </div>

      <div
        className={styles.block}
        style={{
          height: config.blockHeight,
          backgroundColor: config.blockColor,
        }}
      >
        <span className={styles.blockNumeral} style={{ color: config.numeralColor }}>
          {position}
        </span>
      </div>
    </div>
  );
}
