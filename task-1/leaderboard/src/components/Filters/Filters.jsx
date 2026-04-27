import { Dropdown } from './Dropdown';
import { SearchInput } from './SearchInput';
import styles from './Filters.module.css';

const QUARTER_OPTIONS = [
  { value: 'all', label: 'All Quarters' },
  { value: '1', label: 'Q1' },
  { value: '2', label: 'Q2' },
  { value: '3', label: 'Q3' },
  { value: '4', label: 'Q4' },
];

const CATEGORY_OPTIONS = [
  { value: 'all', label: 'All Categories' },
  { value: 'Education', label: 'Education' },
  { value: 'Public Speaking', label: 'Public Speaking' },
  { value: 'University Partners', label: 'University Partners' },
];

export function Filters({
  year,
  quarter,
  category,
  search,
  yearOptions,
  onYearChange,
  onQuarterChange,
  onCategoryChange,
  onSearchChange,
  onSearchClear,
}) {
  return (
    <div className={styles.bar}>
      <Dropdown
        label="All Years"
        options={yearOptions}
        value={year}
        onChange={onYearChange}
      />
      <Dropdown
        label="All Quarters"
        options={QUARTER_OPTIONS}
        value={quarter}
        onChange={onQuarterChange}
      />
      <Dropdown
        label="All Categories"
        options={CATEGORY_OPTIONS}
        value={category}
        onChange={onCategoryChange}
      />
      <SearchInput
        value={search}
        onChange={onSearchChange}
        onClear={onSearchClear}
      />
    </div>
  );
}
