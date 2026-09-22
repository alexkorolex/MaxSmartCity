import type { PropsWithChildren } from 'react';

export function ListCard({ children }: PropsWithChildren) {
  return <div className="content-card list-card">{children}</div>;
}
