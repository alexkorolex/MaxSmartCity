import type { ProblemCategory } from '@/entities/report';
import { WarningIcon } from '@/shared/ui';

import './CategoryPicker.css';

const LAST_CATEGORY = 'other';

interface CategoryPickerProps {
  categories: ProblemCategory[];
  value: string | null;
  onChange: (category: ProblemCategory) => void;
}

function CategoryOption({
  category,
  checked,
  onChange,
}: {
  category: ProblemCategory;
  checked: boolean;
  onChange: (category: ProblemCategory) => void;
}) {
  return (
    <label
      className={[
        'category-option',
        category.is_critical && 'category-option--critical',
        checked && 'category-option--selected',
      ]
        .filter(Boolean)
        .join(' ')}
    >
      <input
        className="category-option__input"
        type="radio"
        name="category"
        value={category.code}
        checked={checked}
        onChange={() => onChange(category)}
      />
      {category.is_critical && <WarningIcon className="category-option__icon" width={18} height={18} />}
      <span className="category-option__name">{category.name}</span>
    </label>
  );
}

export function CategoryPicker({ categories, value, onChange }: CategoryPickerProps) {
  const regular = categories
    .filter((category) => !category.is_critical)
    .sort((a, b) => Number(a.code === LAST_CATEGORY) - Number(b.code === LAST_CATEGORY));
  const critical = categories.filter((category) => category.is_critical);

  return (
    <div className="category-picker" role="radiogroup" aria-label="Тип обращения">
      <section className="content-card category-picker__group">
        <div className="category-picker__heading">
          <span className="category-picker__title">Что случилось?</span>
          <span className="category-picker__hint">Выберите, к чему относится проблема</span>
        </div>
        <div className="category-picker__grid">
          {regular.map((category) => (
            <CategoryOption
              key={category.id}
              category={category}
              checked={value === category.code}
              onChange={onChange}
            />
          ))}
        </div>
      </section>

      {critical.length > 0 && (
        <section className="category-picker__group category-picker__group--critical">
          <div className="category-picker__heading">
            <span className="category-picker__title">
              <WarningIcon width={18} height={18} />
              Опасная ситуация
            </span>
            <span className="category-picker__hint">
              Угроза жизни, здоровью или имуществу — обращение уйдёт с наивысшей срочностью. Если опасность прямо
              сейчас, сначала позвоните 112.
            </span>
          </div>
          <div className="category-picker__grid">
            {critical.map((category) => (
              <CategoryOption
                key={category.id}
                category={category}
                checked={value === category.code}
                onChange={onChange}
              />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
