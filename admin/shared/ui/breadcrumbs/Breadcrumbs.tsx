import { Link } from 'react-router-dom';

import { ChevronRightIcon } from '@/shared/ui/icons';

import './Breadcrumbs.css';

export interface BreadcrumbItem {
  label: string;
  to?: string;
}

export function Breadcrumbs({ items }: { items: BreadcrumbItem[] }) {
  return (
    <nav className="breadcrumbs" aria-label="Хлебные крошки">
      <ol>
        {items.map((item, index) => {
          const isCurrent = index === items.length - 1;
          return (
            <li key={`${item.label}-${index}`}>
              {index > 0 && <ChevronRightIcon className="breadcrumbs__separator" width={14} height={14} />}
              {item.to && !isCurrent ? <Link to={item.to}>{item.label}</Link> : <span aria-current={isCurrent ? 'page' : undefined}>{item.label}</span>}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
