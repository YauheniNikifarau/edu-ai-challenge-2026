import { ActivityTable } from './ActivityTable';
import styles from './EmployeeCard.module.css';

function MonitorIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <rect x="1" y="2" width="14" height="10" rx="1.5" stroke="currentColor" strokeWidth="1.5" />
      <path d="M5 14h6M8 12v2" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}

function GradCapIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <path d="M8 2L15 6l-7 4-7-4 7-4z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
      <path d="M4 8v4c0 1.1 1.8 2 4 2s4-.9 4-2V8" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
      <path d="M15 6v4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}

function UniversityIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <path d="M8 1l7 3v1H1V4l7-3z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
      <rect x="1" y="13" width="14" height="2" rx="0.5" stroke="currentColor" strokeWidth="1.5" />
      <rect x="2" y="6" width="2" height="7" stroke="currentColor" strokeWidth="1.5" />
      <rect x="7" y="6" width="2" height="7" stroke="currentColor" strokeWidth="1.5" />
      <rect x="12" y="6" width="2" height="7" stroke="currentColor" strokeWidth="1.5" />
    </svg>
  );
}

function StarIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" fill="var(--color-accent-blue)" aria-hidden="true">
      <path d="M9 1.5l2 4.1 4.5.65-3.25 3.16.77 4.48L9 11.75l-4.02 2.14.77-4.48L2.5 6.25l4.5-.65z" />
    </svg>
  );
}

function ChevronIcon({ isOpen }) {
  return (
    <svg
      className={`${styles.chevron} ${isOpen ? styles.chevronOpen : ''}`}
      width="20"
      height="20"
      viewBox="0 0 20 20"
      fill="none"
      aria-hidden="true"
    >
      <path
        d="M5 8l5 5 5-5"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function EmployeeCard({ employee, isExpanded, onToggle }) {
  return (
    <div
      className={`${styles.card} ${isExpanded ? styles.cardExpanded : ''}`}
      onClick={() => onToggle(employee.id)}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onToggle(employee.id);
        }
      }}
      aria-expanded={isExpanded}
    >
      <div className={styles.header}>
        <span className={styles.rank}>{employee.rank}</span>

        <img
          src={employee.avatar}
          alt={employee.name}
          className={styles.avatar}
        />

        <div className={styles.identity}>
          <p className={styles.name}>{employee.name}</p>
          <p className={styles.jobTitle}>
            {employee.jobTitle} ({employee.department})
          </p>
        </div>

        <div className={styles.stats}>
          <div
            className={styles.iconGroup}
            aria-label={`Public Speaking: ${employee.publicSpeakingCount}`}
            style={{ display: employee.publicSpeakingCount === 0 ? 'none' : undefined }}
          >
            <span className={styles.iconWrap}>
              <MonitorIcon />
            </span>
            <span className={styles.iconCount}>{employee.publicSpeakingCount}</span>
            <div className={styles.tooltip}>Public Speaking</div>
          </div>

          <div
            className={styles.iconGroup}
            aria-label={`Education: ${employee.educationCount}`}
            style={{ display: employee.educationCount === 0 ? 'none' : undefined }}
          >
            <span className={styles.iconWrap}>
              <GradCapIcon />
            </span>
            <span className={styles.iconCount}>{employee.educationCount}</span>
            <div className={styles.tooltip}>Education</div>
          </div>

          <div
            className={styles.iconGroup}
            aria-label={`University Partners: ${employee.universityPartnersCount}`}
            style={{ display: employee.universityPartnersCount === 0 ? 'none' : undefined }}
          >
            <span className={styles.iconWrap}>
              <UniversityIcon />
            </span>
            <span className={styles.iconCount}>{employee.universityPartnersCount}</span>
            <div className={styles.tooltip}>University Partners</div>
          </div>
        </div>

        <div className={styles.divider} />

        <div className={styles.total}>
          <span className={styles.totalLabel}>Total</span>
          <div className={styles.totalScore}>
            <StarIcon />
            <span className={styles.totalValue}>{employee.filteredTotal}</span>
          </div>
        </div>

        <ChevronIcon isOpen={isExpanded} />
      </div>

      {isExpanded && (
        <div
          className={styles.expanded}
          onClick={(e) => e.stopPropagation()}
        >
          <ActivityTable activities={employee.filteredActivities} />
        </div>
      )}
    </div>
  );
}
