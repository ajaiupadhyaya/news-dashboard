import { MotionConfig } from 'motion/react';
import { spring } from './design/motion';

export default function App() {
  return (
    <MotionConfig reducedMotion="user" transition={spring.smooth}>
      <div>News &amp; Markets Dashboard</div>
    </MotionConfig>
  );
}
