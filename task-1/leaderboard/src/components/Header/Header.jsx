import styles from './Header.module.css';

export function Header() {
  return (
    <header className={styles.header}>
      <h1 className={styles.title}>Leaderboard</h1>
      <p className={styles.subtitle}>Top performers based on contributions and activity</p>
    </header>
  );
}
