import { render, screen } from '@testing-library/react';
import { ReleaseCalendar } from './ReleaseCalendar';
import type { ReleaseEvent } from '../lib/types';

const events: ReleaseEvent[] = [
  { date: '2026-05-13', release_name: 'Consumer Price Index' },
  { date: '2026-05-02', release_name: 'Employment Situation' },
];

test('lists each release with its name', () => {
  render(<ReleaseCalendar events={events} />);
  expect(screen.getByText('Consumer Price Index')).toBeInTheDocument();
  expect(screen.getByText('Employment Situation')).toBeInTheDocument();
});

test('shows an empty-state message when there are no releases', () => {
  render(<ReleaseCalendar events={[]} />);
  expect(screen.getByText(/no releases/i)).toBeInTheDocument();
});
