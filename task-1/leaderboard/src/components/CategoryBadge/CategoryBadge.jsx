import styles from './CategoryBadge.module.css';

export function CategoryBadge({ category }) {
  return <span className={styles.badge}>{category}</span>;
}
