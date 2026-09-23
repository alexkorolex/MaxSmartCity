import { CellHeader, CellList, CellSimple, Radio } from '@maxhub/max-ui';

import { ListCard } from '@/shared/ui';

import { useTheme, type ThemePreference } from '../model/useTheme';

const OPTIONS: Array<{ value: ThemePreference; label: string }> = [
  { value: 'system', label: 'Как в системе' },
  { value: 'light', label: 'Светлая' },
  { value: 'dark', label: 'Тёмная' },
];

export function ThemeSwitch() {
  const { preference, setPreference } = useTheme();

  return (
    <ListCard>
    <CellList mode="full-width" header={<CellHeader>Тема оформления</CellHeader>}>
      {OPTIONS.map((option) => (
        <CellSimple
          key={option.value}
          title={option.label}
          after={
            <Radio
              name="theme"
              value={option.value}
              checked={preference === option.value}
              onChange={() => setPreference(option.value)}
              aria-label={option.label}
            />
          }
        />
      ))}
    </CellList>
    </ListCard>
  );
}
