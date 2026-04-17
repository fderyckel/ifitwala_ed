import type { SnapshotYearOption } from './types';

type AcademicYearScopeContext = {
	currentAcademicYear?: string | null;
	yearOptions?: SnapshotYearOption[];
};

export function academicYearScopeLabel(scope?: string, fallback?: string | null) {
	if (scope === 'current') return 'This academic year';
	if (scope === 'previous' || scope === 'last') return 'Last academic year';
	if (scope === 'two_years') return 'Last two academic years';
	if (scope === 'all') return 'All academic years';
	return fallback || scope || '';
}

export function matchesAcademicYearScope(
	itemYear?: string | null,
	scope?: string,
	context: AcademicYearScopeContext = {}
) {
	if (!scope || scope === 'all') return true;
	if (!itemYear) return true;

	const yearOptions = context.yearOptions || [];

	if (scope === 'current') {
		return context.currentAcademicYear ? itemYear === context.currentAcademicYear : false;
	}

	if (scope === 'previous' || scope === 'last') {
		const previousAcademicYear = yearOptions.find(option => option.key === 'previous')?.academic_year;
		return previousAcademicYear ? itemYear === previousAcademicYear : false;
	}

	if (scope === 'two_years') {
		const academicYears = yearOptions.find(option => option.key === 'two_years')?.academic_years || [];
		return academicYears.includes(itemYear);
	}

	return true;
}
