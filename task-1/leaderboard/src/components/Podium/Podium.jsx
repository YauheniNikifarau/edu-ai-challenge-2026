import { PodiumSlot } from './PodiumSlot';
import styles from './Podium.module.css';

export function Podium({ topThree }) {
  if (topThree.length === 0) return null;

  const [first, second, third] = topThree;

  return (
    <div className={styles.podium}>
      {second && (
        <PodiumSlot
          employee={second}
          position={2}
          hidden={!second.searchVisible}
        />
      )}
      <PodiumSlot
        employee={first}
        position={1}
        hidden={!first.searchVisible}
      />
      {third && (
        <PodiumSlot
          employee={third}
          position={3}
          hidden={!third.searchVisible}
        />
      )}
    </div>
  );
}
