import { useMemo } from 'react';
import { filterActivities, sortByPoints, matchesSearch } from '../utils/filters';

export function useLeaderboard(employees, { year, quarter, category, search }) {
  return useMemo(() => {
    // Step 1: compute filtered activities, totals, and ranks — search has no effect here
    const withFiltered = employees.map((employee) => {
      const filteredActivities = filterActivities(employee.activities, { year, quarter, category });
      const filteredTotal = filteredActivities.reduce((sum, a) => sum + a.points, 0);
      const { publicSpeakingCount, educationCount, universityPartnersCount } =
        filteredActivities.reduce(
          (acc, a) => {
            if (a.category === 'Public Speaking') acc.publicSpeakingCount++;
            else if (a.category === 'Education') acc.educationCount++;
            else if (a.category === 'University Partners') acc.universityPartnersCount++;
            return acc;
          },
          { publicSpeakingCount: 0, educationCount: 0, universityPartnersCount: 0 }
        );

      return {
        ...employee,
        filteredActivities,
        filteredTotal,
        publicSpeakingCount,
        educationCount,
        universityPartnersCount,
      };
    });

    const withPoints = withFiltered.filter((e) => e.filteredTotal > 0);
    const sorted = sortByPoints(withPoints);

    // Ranks are stable regardless of search; searchVisible drives podium slot visibility
    const rankedEmployees = sorted.map((employee, index) => ({
      ...employee,
      rank: index + 1,
      searchVisible: matchesSearch(employee, search),
    }));

    // Step 2: apply search only as a display filter — ranks and podium are unaffected
    const visibleEmployees = rankedEmployees.filter((e) => e.searchVisible);

    return {
      rankedEmployees: visibleEmployees,
      topThree: rankedEmployees.slice(0, 3),
    };
  }, [employees, year, quarter, category, search]);
}
