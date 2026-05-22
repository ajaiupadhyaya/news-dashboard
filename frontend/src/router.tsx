import { createBrowserRouter } from 'react-router-dom';
import type { RouteObject } from 'react-router-dom';
import { Home } from './routes/Home';
import { FinanceRoute } from './routes/FinanceRoute';
import { InstrumentRoute } from './routes/InstrumentRoute';
import { IndicatorRoute } from './routes/IndicatorRoute';
import { StoryRoute } from './routes/StoryRoute';

export const routes: RouteObject[] = [
  { path: '/', element: <Home /> },
  { path: '/finance', element: <FinanceRoute /> },
  { path: '/finance/:symbol', element: <InstrumentRoute /> },
  { path: '/economics/:seriesId', element: <IndicatorRoute /> },
  { path: '/news/:clusterId', element: <StoryRoute /> },
];

export const router = createBrowserRouter(routes);
