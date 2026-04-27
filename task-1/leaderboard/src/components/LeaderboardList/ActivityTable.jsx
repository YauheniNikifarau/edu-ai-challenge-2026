import { useMemo, useState } from 'react';
import { sortActivitiesByDateDesc } from '../../utils/filters';
import { CategoryBadge } from '../CategoryBadge/CategoryBadge';
import styles from './ActivityTable.module.css';

const PAGE_SIZE = 10;

export function ActivityTable({ activities }) {
  const [showAll, setShowAll] = useState(false);

  const sorted = useMemo(() => sortActivitiesByDateDesc(activities), [activities]);
  const visible = showAll ? sorted : sorted.slice(0, PAGE_SIZE);
  const hasMore = sorted.length > PAGE_SIZE;

  return (
    <div className={styles.container}>
      <p className={styles.sectionLabel}>Recent Activity</p>

      <table className={styles.table}>
        <thead>
          <tr>
            <th className={`${styles.th} ${styles.colActivity}`}>Activity</th>
            <th className={`${styles.th} ${styles.colCategory}`}>Category</th>
            <th className={`${styles.th} ${styles.colDate}`}>Date</th>
            <th className={`${styles.th} ${styles.colPoints}`}>Points</th>
          </tr>
        </thead>
        <tbody>
          {visible.map((activity) => (
            <tr key={activity.id} className={styles.row}>
              <td className={`${styles.td} ${styles.colActivity}`}>
                {activity.title}
              </td>
              <td className={`${styles.td} ${styles.colCategory}`}>
                <CategoryBadge category={activity.category} />
              </td>
              <td className={`${styles.td} ${styles.colDate}`}>
                {activity.date}
              </td>
              <td className={`${styles.td} ${styles.colPoints}`}>
                +{activity.points}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {hasMore && (
        <button
          type="button"
          className={styles.showMoreBtn}
          onClick={(e) => {
            e.stopPropagation();
            setShowAll((prev) => !prev);
          }}
        >
          {showAll ? 'Show less' : `Show all ${sorted.length} activities`}
        </button>
      )}
    </div>
  );
}
