const MONTH_MAP = {
  Jan: 1, Feb: 2, Mar: 3, Apr: 4, May: 5, Jun: 6,
  Jul: 7, Aug: 8, Sep: 9, Oct: 10, Nov: 11, Dec: 12,
};

export function filterActivities(activities, { year, quarter, category }) {
  return activities.filter((activity) => {
    if (year !== 'all' && activity.year !== Number(year)) return false;
    if (quarter !== 'all' && activity.quarter !== Number(quarter)) return false;
    if (category !== 'all' && activity.category !== category) return false;
    return true;
  });
}

export function sortByPoints(employees) {
  return [...employees].sort(
    (a, b) => b.filteredTotal - a.filteredTotal || a.id.localeCompare(b.id)
  );
}

export function matchesSearch(employee, query) {
  if (!query) return true;
  return employee.name.toLowerCase().includes(query.toLowerCase());
}

export function parseDateToTimestamp(dateStr) {
  const [day, monthAbbr, year] = dateStr.split('-');
  const month = MONTH_MAP[monthAbbr] ?? 1;
  return new Date(Number(year), month - 1, Number(day)).getTime();
}

export function sortActivitiesByDateDesc(activities) {
  return [...activities].sort(
    (a, b) => parseDateToTimestamp(b.date) - parseDateToTimestamp(a.date)
  );
}
