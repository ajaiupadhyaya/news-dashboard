import { createBrowserRouter } from 'react-router-dom';
import type { RouteObject } from 'react-router-dom';
import { Home } from './routes/Home';
import { FinanceRoute } from './routes/FinanceRoute';
import { InstrumentRoute } from './routes/InstrumentRoute';
import { IndicatorRoute } from './routes/IndicatorRoute';
import { StoryRoute } from './routes/StoryRoute';
import { QuantRoute } from './routes/QuantRoute';
import { StrategyRoute } from './routes/StrategyRoute';

export const routes: RouteObject[] = [
  { path: '/', element: <Home /> },
  { path: '/finance', element: <FinanceRoute /> },
  { path: '/finance/:symbol', element: <InstrumentRoute /> },
  { path: '/economics/:seriesId', element: <IndicatorRoute /> },
  { path: '/news/:clusterId', element: <StoryRoute /> },
  { path: '/quant', element: <QuantRoute /> },
  { path: '/quant/strategy/:slug', element: <StrategyRoute /> },
];

export const router = createBrowserRouter(routes);
