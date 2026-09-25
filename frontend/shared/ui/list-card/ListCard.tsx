import type { PropsWithChildren } from 'react';

import './ListCard.css';

export function ListCard({ children }: PropsWithChildren) {
  return <div className="content-card list-card">{children}</div>;
}
