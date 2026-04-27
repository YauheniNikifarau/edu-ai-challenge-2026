import { EmployeeCard } from './EmployeeCard';
import styles from './LeaderboardList.module.css';

export function LeaderboardList({ employees, expandedEmployeeId, onToggle }) {
  return (
    <div className={styles.list}>
      {employees.map((employee) => (
        <EmployeeCard
          key={employee.id}
          employee={employee}
          isExpanded={expandedEmployeeId === employee.id}
          onToggle={onToggle}
        />
      ))}
    </div>
  );
}
