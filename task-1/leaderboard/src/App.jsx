import { useState, useMemo } from 'react';
import { Header } from './components/Header/Header';
import { Filters } from './components/Filters/Filters';
import { Podium } from './components/Podium/Podium';
import { LeaderboardList } from './components/LeaderboardList/LeaderboardList';
import { EmptyState } from './components/EmptyState/EmptyState';
import { useLeaderboard } from './hooks/useLeaderboard';
import employeesData from './data/employees.json';
import styles from './App.module.css';

const allEmployees = employeesData.employees;

function App() {
  const [year, setYear] = useState('all');
  const [quarter, setQuarter] = useState('all');
  const [category, setCategory] = useState('all');
  const [search, setSearch] = useState('');
  const [expandedEmployeeId, setExpandedEmployeeId] = useState(null);

  const yearOptions = useMemo(() => {
    const years = Array.from(
      new Set(allEmployees.flatMap((e) => e.activities.map((a) => a.year)))
    ).sort((a, b) => b - a);
    return [
      { value: 'all', label: 'All Years' },
      ...years.map((y) => ({ value: String(y), label: String(y) })),
    ];
  }, []);

  const { rankedEmployees, topThree } = useLeaderboard(
    allEmployees,
    { year, quarter, category, search }
  );

  function handleToggle(id) {
    setExpandedEmployeeId((prev) => (prev === id ? null : id));
  }

  // No employees match the year/quarter/category filters at all
  const noFilterResults = topThree.length === 0;
  // Search is active but matched no one (filters have results, search does not)
  const noSearchResults = !noFilterResults && rankedEmployees.length === 0;

  return (
    <div className={styles.page}>
      <div className={styles.container}>
        <Header />

        <div className={styles.content}>
          <Filters
            year={year}
            quarter={quarter}
            category={category}
            search={search}
            yearOptions={yearOptions}
            onYearChange={setYear}
            onQuarterChange={setQuarter}
            onCategoryChange={setCategory}
            onSearchChange={setSearch}
            onSearchClear={() => setSearch('')}
          />

          {noFilterResults ? (
            <EmptyState />
          ) : (
            <>
              <Podium topThree={topThree} />
              {noSearchResults ? (
                <EmptyState />
              ) : (
                <LeaderboardList
                  employees={rankedEmployees}
                  expandedEmployeeId={expandedEmployeeId}
                  onToggle={handleToggle}
                />
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

export default App;
