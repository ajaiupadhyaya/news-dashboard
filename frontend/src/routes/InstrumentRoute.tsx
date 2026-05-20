import { useParams } from 'react-router-dom';

/** Placeholder — the full drill-down page is built in Task 19. */
export function InstrumentRoute() {
  const { symbol = '' } = useParams();
  return <div>Instrument: {symbol}</div>;
}
