# MAX UI — руководство для разработчика

> Актуальность проверки: **22 сентября 2026**  
> Целевой пакет: **`@maxhub/max-ui` 0.5.0**  
> Основной сайт: https://dev.max.ru/ui  
> Репозиторий: https://github.com/max-messenger/max-ui  
> npm: https://www.npmjs.com/package/@maxhub/max-ui


---

## 1. Главные правила 

1. **MAX UI — React UI-kit, а не Bot API.**
   - MAX UI отвечает за интерфейс React-приложения.
   - Webhook, получение сообщений бота, inline/callback-кнопки Bot API и отправка сообщений относятся к API платформы MAX, а не к `@maxhub/max-ui`.
   - Не пытайся реализовывать обработчик bot callback через React-компоненты MAX UI.

2. **При конфликте документации используй такой приоритет источников:**
   1. установленная в проекте версия `@maxhub/max-ui`;
   2. TypeScript-типы установленного пакета;
   3. исходники соответствующего тега/версии в `max-messenger/max-ui`;
   4. `docs/MIGRATION.md` и `CHANGELOG.md`;
   5. страницы `https://dev.max.ru/ui`.

3. **Не копируй слепо старые примеры с `dev.max.ru/ui`.** Часть страниц сайта содержит API предыдущих версий библиотеки.

4. Перед изменением UI выполни или предложи выполнить:

   ```bash
   npm ls @maxhub/max-ui react react-dom
   ```

   Затем ориентируйся на реально установленную версию.

5. Для нового кода предпочитай **актуальный API 0.5.x**, описанный ниже.

6. Не придумывай отсутствующие компоненты или props. Если TypeScript не подтверждает API — сначала проверь типы пакета.

---

## 2. Установка

```bash
npm install @maxhub/max-ui
```

Альтернативно:

```bash
yarn add @maxhub/max-ui
```

или:

```bash
pnpm add @maxhub/max-ui
```

Обязательно подключить стили:

```tsx
import '@maxhub/max-ui/dist/styles.css';
```

### Важное замечание о React

README библиотеки всё ещё говорит о React 18+, однако metadata пакета версии `0.5.0` в репозитории указывает peer dependencies на:

```json
{
  "react": "19.2.8",
  "react-dom": "19.2.8"
}
```

Поэтому разработчик **не должен автоматически считать React 18 совместимым с установленной версией**. Сначала проверять `package.json`/peer dependencies конкретной версии.

---

## 3. Минимальная инициализация

```tsx
import { createRoot } from 'react-dom/client';
import { MaxUI } from '@maxhub/max-ui';
import '@maxhub/max-ui/dist/styles.css';

import App from './App';

createRoot(document.getElementById('root')!).render(
  <MaxUI resetBody>
    <App />
  </MaxUI>,
);
```

### `MaxUI`

Актуальные основные props:

```ts
type PlatformType = 'ios' | 'android';
type ColorSchemeType = 'light' | 'dark';

interface MaxUIProps {
  children: React.ReactNode;
  className?: string;
  resetBody?: boolean;
  platform?: PlatformType;
  colorScheme?: ColorSchemeType;
}
```

Поведение:

- если `platform` не задан, библиотека определяет iOS/Android самостоятельно;
- если `colorScheme` не задан, используется системная цветовая схема;
- `resetBody` по умолчанию выключен;
- для принудительной темы допустимо:

```tsx
<MaxUI platform="android" colorScheme="dark">
  <App />
</MaxUI>
```

---

## 4. Актуальный набор компонентов 0.5.0

По текущему `src/components/index.ts` публично экспортируются:

| Компонент | Назначение |
|---|---|
| `Avatar` | аватар и связанные части |
| `Button` | основная кнопка |
| `CellAction` | action-строка/ячейка |
| `CellHeader` | заголовок группы ячеек |
| `CellInput` | input в формате cell |
| `CellList` | контейнер списка ячеек |
| `CellSimple` | универсальная строка списка |
| `Counter` | счётчик/бейдж |
| `IconButton` | кнопка только с иконкой |
| `Input` | обычное поле ввода |
| `MaxUI` | корневой provider/container |
| `Radio` | radio input |
| `Spinner` | индикатор загрузки |
| `Switch` | переключатель |
| `Textarea` | многострочное поле |
| `Typography` | типографика |

Также корневой entrypoint сейчас реэкспортирует модуль `internal`, из которого доступны `Container`, `Flex`, `Grid`, `Panel`, `EllipsisText`, `Ripple`, `ClearableInput`, `SvgButton`, `Tappable`. Для нового кода разработчик должен быть осторожен: расположение в `src/internal` означает, что эти сущности потенциально менее стабильны, даже если сейчас импортируются из `@maxhub/max-ui`.

---

# 5. Компоненты: актуальный API

## 5.1 `Button`

```ts
type ButtonSize = 'xsmall' | 'small' | 'medium' | 'large';

type ButtonVariant =
  | 'primary'
  | 'secondary'
  | 'ghost'
  | 'primary-contrast'
  | 'secondary-contrast'
  | 'overlay'
  | 'destructive';
```

Ключевые props:

```ts
interface ButtonProps {
  size?: ButtonSize;
  variant?: ButtonVariant;
  stretched?: boolean;
  iconBefore?: React.ReactNode;
  iconAfter?: React.ReactNode;
  indicator?: React.ReactNode;
  loading?: boolean;
  disabled?: boolean;
  onClick?: React.MouseEventHandler<HTMLButtonElement>;
  asChild?: boolean;
  innerClassNames?: {
    iconBefore?: string;
    iconAfter?: string;
    indicator?: string;
    content?: string;
    spinnerContainer?: string;
    spinner?: string;
  };
}
```

Пример:

```tsx
<Button
  variant="primary"
  size="large"
  stretched
  loading={isSubmitting}
  onClick={handleSubmit}
>
  Сохранить
</Button>
```

### Важно

- В актуальном API используется **`variant`**, а не старые комбинации `mode`/`appearance` из прежней документации.
- При `loading` текущая реализация не должна вызывать пользовательский `onClick`.

---

## 5.2 `IconButton`

```ts
type IconButtonSize = 'xsmall' | 'small' | 'medium' | 'large';
type IconButtonVariant = ButtonVariant;
```

Ключевые props:

```ts
interface IconButtonProps {
  size?: IconButtonSize;
  variant?: IconButtonVariant;
  disabled?: boolean;
  loading?: boolean;
  asChild?: boolean;
  innerClassNames?: {
    content?: string;
    spinnerContainer?: string;
    spinner?: string;
  };
}
```

Для доступности разработчик должен передавать `aria-label`, если смысл кнопки нельзя понять из текста:

```tsx
<IconButton aria-label="Закрыть" variant="ghost">
  <CloseIcon />
</IconButton>
```

---

## 5.3 `Counter`

```ts
type CounterVariant =
  | 'primary'
  | 'primary-contrast'
  | 'attention'
  | 'attention-contrast'
  | 'promo'
  | 'static'
  | 'static-contrast'
  | 'default'
  | 'mute'
  | 'menu';

interface CounterProps {
  value: number;
  variant?: CounterVariant;
  rounded?: boolean;
}
```

Пример:

```tsx
<Counter value={12} variant="attention" rounded />
```

---

## 5.4 `CellList`

```ts
type CellListMode = 'full-width' | 'island';

interface CellListProps {
  mode?: CellListMode;
  filled?: boolean;
  header?: React.ReactNode;
}
```

Пример:

```tsx
<CellList
  mode="island"
  header={<CellHeader>Настройки</CellHeader>}
>
  {/* cells */}
</CellList>
```

`island` относится к новому API ветки 0.5.x.

---

## 5.5 `CellSimple`

```ts
type CellSimpleHeight = 'compact' | 'normal';
type CellSimpleSubtitleMode = 'secondary' | 'tertiary';
type CellSimpleSurface = 'default' | 'island';
```

Ключевые props:

```ts
interface CellSimpleProps {
  height?: CellSimpleHeight;
  surface?: CellSimpleSurface;
  title?: React.ReactNode;
  subtitle?: React.ReactNode;
  subtitleMode?: CellSimpleSubtitleMode;
  overline?: React.ReactNode;
  before?: React.ReactNode;
  after?: React.ReactNode;
  showChevron?: boolean;
  disabled?: boolean;
  separator?: boolean;
  link?: string;
  as?: React.ElementType;
  asChild?: boolean;
}
```

Пример:

```tsx
<CellSimple
  title="Уведомления"
  subtitle="Получать уведомления о новых событиях"
  subtitleMode="tertiary"
  after={<Switch checked={enabled} onChange={handleChange} />}
/>
```

---

## 5.6 `CellAction`

```ts
type CellActionMode =
  | 'primary'
  | 'secondary'
  | 'themed'
  | 'destructive'
  | 'custom';

type CellActionSurface = 'default' | 'island';
type CellActionHeight = 'compact' | 'normal';
```

Ключевые props:

```ts
interface CellActionProps {
  mode?: CellActionMode;
  surface?: CellActionSurface;
  height?: CellActionHeight;
  before?: React.ReactNode;
  showChevron?: boolean;
  asChild?: boolean;
}
```

Пример:

```tsx
<CellAction mode="destructive" onClick={handleLogout}>
  Выйти
</CellAction>
```

---

## 5.7 `CellHeader`

```ts
type CellHeaderTitleStyle = 'caps' | 'normal';

interface CellHeaderProps {
  titleStyle?: CellHeaderTitleStyle;
  fullWidth?: boolean;
  after?: React.ReactNode;
}
```

---

## 5.8 `CellInput`

```ts
type CellInputHeight = 'compact' | 'normal';
type CellInputSurface = 'default' | 'island';
```

Ключевые props:

```ts
interface CellInputProps {
  height?: CellInputHeight;
  surface?: CellInputSurface;
  before?: React.ReactNode;
  // + native input props
}
```

---

## 5.9 `Input`

Актуальный API:

```ts
type InputMode = 'default' | 'contrast';
type InputSize = 'large' | 'medium';
```

Ключевые props:

```ts
interface InputProps {
  mode?: InputMode;
  size?: InputSize;
  iconBefore?: React.ReactNode;
  iconAfter?: React.ReactNode;
  withClearButton?: boolean;
  count?: number;
  hint?: React.ReactNode;
  value?: string | number | readonly string[];
  onChange?: React.ChangeEventHandler<HTMLInputElement>;
}
```

Пример:

```tsx
<Input
  value={query}
  onChange={(event) => setQuery(event.target.value)}
  placeholder="Поиск"
  withClearButton
  hint="Введите название"
/>
```

### Не использовать старый API

Не генерировать:

```tsx
<Input mode="primary" />
```

Для нового API доступны только:

```tsx
<Input mode="default" />
<Input mode="contrast" />
```

---

## 5.10 `Textarea`

```ts
type TextareaMode = 'primary' | 'secondary';

interface TextareaProps {
  mode?: TextareaMode;
  // + native textarea props
}
```

Пример:

```tsx
<Textarea
  value={comment}
  onChange={(event) => setComment(event.target.value)}
  placeholder="Комментарий"
/>
```

---

## 5.11 `Switch`

`Switch` принимает стандартные props HTML `<input>`.

Использовать как controlled input:

```tsx
<Switch
  checked={enabled}
  onChange={(event) => setEnabled(event.target.checked)}
  aria-label="Включить уведомления"
/>
```

---

## 5.12 `Radio`

`Radio` добавлен в актуальный пакет 0.5.0.

Компонент принимает стандартные props `<input>`, кроме `type`: библиотека сама принудительно выставляет `type="radio"`.

```tsx
<Radio
  name="theme"
  value="dark"
  checked={theme === 'dark'}
  onChange={() => setTheme('dark')}
/>
```

Не передавать `type` вручную.

---

## 5.13 `Spinner`

```ts
type SpinnerAppearance =
  | 'primary'
  | 'themed'
  | 'neutral-themed'
  | 'primary-static'
  | 'contrast'
  | 'contrast-static'
  | 'negative';

type SpinnerSize = 20 | 24 | number;
```

Пример:

```tsx
<Spinner size={24} appearance="primary" />
```

---

# 6. `Typography`

## Рекомендуемый API для нового кода

Использовать:

```tsx
<Typography.Text />
```

Актуальные варианты:

```ts
type TypographyTextVariant =
  | 'hero'
  | 'header'
  | 'subheader'
  | 'title'
  | 'body'
  | 'body-strong'
  | 'detail'
  | 'detail-strong'
  | 'description'
  | 'description-strong'
  | 'label'
  | 'label-strong'
  | 'tag'
  | 'tag-strong'
  | 'note'
  | 'note-strong'
  | 'action-large'
  | 'action-medium'
  | 'action-small'
  | 'action-xsmall';

type TypographyTextColor =
  | 'primary'
  | 'secondary'
  | 'tertiary'
  | 'inherit';
```

Пример:

```tsx
<Typography.Text variant="header" color="primary">
  Настройки
</Typography.Text>

<Typography.Text variant="description" color="secondary">
  Управление приложением
</Typography.Text>
```

По умолчанию:

```ts
variant = 'body'
color = 'inherit'
```

### Legacy API

Пока ещё экспортируются:

```tsx
Typography.Display
Typography.Headline
Typography.Title
Typography.Body
Typography.Label
Typography.Action
```

Но для нового кода разработчик должен предпочитать `Typography.Text`.

Примеры миграции:

```tsx
// было
<Typography.Display>Title</Typography.Display>

// актуальный подход
<Typography.Text variant="hero">Title</Typography.Text>
```

```tsx
// было
<Typography.Headline variant="medium">Title</Typography.Headline>

// актуальный подход
<Typography.Text variant="subheader">Title</Typography.Text>
```

---

# 7. `Avatar`

Актуальный namespace:

```ts
Avatar.Container
Avatar.Image
Avatar.Overlay
Avatar.Icon
Avatar.Text
Avatar.CloseButton
```

## `Avatar.Container`

```ts
type AvatarContainerFrom = 'circle' | 'squircle';
```

Ключевые props:

```ts
interface AvatarContainerProps {
  size?: number;
  overlay?: React.ReactNode;
  form?: 'circle' | 'squircle';
  onlineStatus?: boolean;
  rightTopCorner?: React.ReactNode;
  rightBottomCorner?: React.ReactNode;
  asChild?: boolean;
}
```

Пример:

```tsx
<Avatar.Container size={48} onlineStatus>
  <Avatar.Image
    src={user.avatarUrl}
    alt={user.name}
    fallback={user.initials}
  />
</Avatar.Container>
```

## `Avatar.Image`

```ts
interface AvatarImageProps {
  fallback?: React.ReactNode;
  fallbackGradient?:
    | 'red'
    | 'orange'
    | 'green'
    | 'blue'
    | 'purple'
    | 'custom';
}
```

Если изображение не загрузилось, компонент умеет отобразить fallback через `Avatar.Text`.

## Не использовать `Avatar.OnlineDot`

Старый вариант:

```tsx
<Avatar.Container rightBottomCorner={<Avatar.OnlineDot />}>
```

Новый вариант:

```tsx
<Avatar.Container onlineStatus>
```

Стандартный online indicator рассчитан на круглые аватары размером 24–80 px включительно.

---

# 8. Layout-компоненты

> Эти компоненты сейчас доступны из корневого package entrypoint, хотя лежат в `src/internal`. Использовать можно, но не считать их API настолько же стабильным, как компоненты из `src/components`.

## `Container`

```ts
interface ContainerProps {
  fullWidth?: boolean;
  asChild?: boolean;
}
```

## `Flex`

```ts
type FlexDisplay = 'flex' | 'inline-flex';
type FlexDirection = 'row' | 'column' | 'row-reverse' | 'column-reverse';
type FlexAlign = 'flex-start' | 'flex-end' | 'center' | 'baseline' | 'stretch';
type FlexJustify = 'start' | 'center' | 'end' | 'space-between';
type FlexWrap = 'wrap' | 'nowrap' | 'wrap-reverse';
```

Props:

```ts
interface FlexProps {
  display?: FlexDisplay;
  direction?: FlexDirection;
  align?: FlexAlign;
  justify?: FlexJustify;
  wrap?: FlexWrap;
  gap?: number | string;
  gapX?: number | string;
  gapY?: number | string;
  asChild?: boolean;
}
```

Пример:

```tsx
<Flex direction="column" gap={12} align="center">
  ...
</Flex>
```

**Не использовать старое `justify="between"`.** Текущий тип — `justify="space-between"`.

## `Grid`

```ts
type GridDisplay = 'grid' | 'inline-grid';
type GridAlign = 'start' | 'center' | 'end' | 'baseline' | 'stretch';
type GridJustify = 'start' | 'center' | 'end' | 'space-between';
```

Props:

```ts
interface GridProps {
  display?: GridDisplay;
  align?: GridAlign;
  justify?: GridJustify;
  gap?: number | string;
  gapX?: number | string;
  gapY?: number | string;
  cols?: number;
  rows?: number;
  asChild?: boolean;
}
```

## `Panel`

```ts
type PanelMode = 'primary' | 'secondary';

interface PanelProps {
  mode?: PanelMode;
  centeredX?: boolean;
  centeredY?: boolean;
}
```

## `EllipsisText`

```ts
interface EllipsisTextProps {
  maxLines?: number;
  asChild?: boolean;
}
```

По умолчанию `maxLines = 1`.

---

# 9. `asChild`: как разработчик должен использовать полиморфность

MAX UI использует pattern `asChild` через Radix Slot.

Например, не надо вкладывать `<a>` в `<button>`:

```tsx
<Button asChild>
  <a href="/settings">Настройки</a>
</Button>
```

С React Router:

```tsx
import { Link } from 'react-router-dom';

<Button asChild>
  <Link to="/settings">Настройки</Link>
</Button>
```

### Правило конфликтов props

При `asChild`:

- `className` объединяется;
- `style` объединяется;
- обработчики событий `on*` объединяются;
- для остальных конфликтующих props приоритет остаётся за props родительского MAX UI компонента.

Поэтому не создавай противоречивые props одновременно на родителе и ребёнке без необходимости.

---

# 10. Кастомизация

MAX UI поддерживает два основных подхода:

1. CSS-переменные дизайн-системы;
2. `innerClassNames` у составных компонентов.

Пример `innerClassNames`:

```tsx
<Button
  iconBefore={<SomeIcon />}
  innerClassNames={{
    iconBefore: 'myButtonIcon',
    content: 'myButtonContent',
  }}
>
  Продолжить
</Button>
```

Для новых overrides использовать актуальные семантические CSS-token группы:

- `--background-*`
- `--button-*`
- `--states-button-*`
- `--controls-*`
- `--states-controls-*`
- `--counter-*`
- `--states-counter-*`
- `--divider-*`
- `--text-*`
- `--icon-*`
- `--states-text-*`
- `--states-icon-*`

Не привязываться к внутренним CSS class names библиотеки без крайней необходимости: документация прямо предупреждает, что customization API может меняться в major versions.

---

# 11. Критические расхождения старой документации и текущего API

разработчик должен учитывать эту таблицу до генерации кода.

| Старое/устаревшее | Актуально для 0.5.0 |
|---|---|
| `Dot` | удалён из публичного API; использовать `Counter` или свой индикатор |
| `ToolButton` | удалён; использовать `Button` или `IconButton` |
| `Avatar.OnlineDot` | использовать `onlineStatus` на `Avatar.Container` |
| `Typography.Display/Headline/...` как основной API | для нового кода предпочитать `Typography.Text` |
| `<Input mode="primary" />` | `mode="default"` или `mode="contrast"` |
| `Flex justify="between"` | `justify="space-between"` |
| `Grid justify="between"` | `justify="space-between"` |
| `SearchInput` на старой странице сайта | отсутствует в текущем `src/components/index.ts` |
| `Profile` на старой странице сайта | отсутствует в текущем `src/components/index.ts` |
| `Radio` отсутствует в старом меню сайта | присутствует в 0.5.0 и экспортируется публично |
| Button со старым `mode`/`appearance` | использовать актуальный `variant` |

Если существующий проект уже использует legacy API и TypeScript его принимает, не переписывай всё без задачи на миграцию. Для нового кода — использовать актуальный API.

---

# 12. Пример современной страницы

```tsx
import {
  Avatar,
  Button,
  CellHeader,
  CellList,
  CellSimple,
  Container,
  Flex,
  Switch,
  Typography,
} from '@maxhub/max-ui';

interface ProfilePageProps {
  user: {
    name: string;
    avatarUrl?: string;
    initials: string;
  };
  notificationsEnabled: boolean;
  onNotificationsChange: (enabled: boolean) => void;
  onSave: () => void;
}

export function ProfilePage({
  user,
  notificationsEnabled,
  onNotificationsChange,
  onSave,
}: ProfilePageProps) {
  return (
    <Container>
      <Flex direction="column" gap={16}>
        <Flex direction="column" gap={8} align="center">
          <Avatar.Container size={72} onlineStatus>
            <Avatar.Image
              src={user.avatarUrl}
              alt={user.name}
              fallback={user.initials}
              fallbackGradient="blue"
            />
          </Avatar.Container>

          <Typography.Text variant="title" color="primary">
            {user.name}
          </Typography.Text>
        </Flex>

        <CellList
          mode="island"
          header={<CellHeader>Настройки</CellHeader>}
        >
          <CellSimple
            title="Уведомления"
            subtitle="Получать обновления приложения"
            subtitleMode="tertiary"
            after={(
              <Switch
                checked={notificationsEnabled}
                onChange={(event) =>
                  onNotificationsChange(event.target.checked)
                }
                aria-label="Уведомления"
              />
            )}
          />
        </CellList>

        <Button
          variant="primary"
          size="large"
          stretched
          onClick={onSave}
        >
          Сохранить
        </Button>
      </Flex>
    </Container>
  );
}
```

---

# 13. Стандарт работы AI-разработчика с MAX UI

Перед созданием компонента:

```text
1. Определи установленную версию @maxhub/max-ui.
2. Проверь, существует ли нужный компонент в exports этой версии.
3. Проверь TypeScript Props/union types.
4. Используй MAX UI вместо самописного HTML, если подходящий компонент существует.
5. Не используй deprecated/удалённые Dot, ToolButton, Avatar.OnlineDot.
6. Для новой типографики используй Typography.Text.
7. Для навигационного Button используй asChild, а не <button><a /></button>.
8. Формы делай controlled/uncontrolled обычным React-способом — компоненты сохраняют native input props.
9. Не хардкодь платформу или тему без требования продукта.
10. После изменений запусти typecheck и lint проекта.
```

Рекомендуемая проверка:

```bash
npm ls @maxhub/max-ui react react-dom
npm run typecheck
npm run lint
```

Названия scripts могут отличаться; сначала проверить `package.json` проекта.

---

# 14. Что делать, если разработчику нужен компонент, которого нет

Порядок действий:

```text
1. Поискать его в установленном пакете и TypeScript exports.
2. Проверить текущий src/components/index.ts соответствующей версии.
3. Проверить CHANGELOG/MIGRATION.
4. Только после этого смотреть старую страницу dev.max.ru/ui.
5. Если компонента действительно нет — собрать поведение из актуальных примитивов
   Button / IconButton / Input / Cell* / Typography / layout.
6. Не импортировать путь вида @maxhub/max-ui/src/... в прикладном коде.
```

Не использовать deep imports во внутреннюю структуру пакета: это сильнее связывает приложение с реализацией библиотеки.

---

# 15. Граница с MAX Bot API

`@maxhub/max-ui` не заменяет Bot API.

Если проект одновременно содержит MAX-бота и мини-приложение, архитектурно разделяй:

```text
MAX client
   │
   ├── Bot interaction
   │      └── MAX Bot API / webhook / messages / callback events
   │
   └── Mini App
          └── React application
                 └── @maxhub/max-ui
```

То есть:

- React `Button` вызывает frontend `onClick`;
- Bot API inline button отправляет событие на backend/webhook;
- это два разных механизма, даже если визуально обе сущности являются кнопками.

---

# 16. Архитектура frontend: Feature-Sliced Design (FSD)

Для React/Mini App части проекта использовать **Feature-Sliced Design (FSD)**.

Это правило относится к frontend-коду. MAX Bot API, webhook, обработка сообщений и callback events относятся к backend и не должны искусственно переноситься в frontend-слои FSD.

Официальная иерархия FSD содержит слои `app`, `pages`, `widgets`, `features`, `entities`, `shared`. Устаревший слой `processes` в новом коде **не использовать**.

## 16.1. Базовое дерево

Рекомендуемая структура:

```text
src/
├── app/
│   ├── providers/
│   ├── router/
│   ├── styles/
│   │   ├── index.css
│   │   └── max-ui.css
│   ├── config/
│   └── index.ts
│
├── pages/
│   ├── home/
│   │   ├── ui/
│   │   ├── api/
│   │   ├── model/
│   │   └── index.ts
│   └── profile/
│       ├── ui/
│       ├── api/
│       ├── model/
│       └── index.ts
│
├── widgets/
│   ├── header/
│   │   ├── ui/
│   │   ├── model/
│   │   └── index.ts
│   └── navigation/
│       ├── ui/
│       └── index.ts
│
├── features/
│   ├── auth-by-password/
│   │   ├── ui/
│   │   ├── model/
│   │   ├── api/
│   │   ├── lib/
│   │   └── index.ts
│   ├── change-theme/
│   │   ├── ui/
│   │   ├── model/
│   │   └── index.ts
│   └── logout/
│       ├── ui/
│       ├── model/
│       └── index.ts
│
├── entities/
│   ├── user/
│   │   ├── ui/
│   │   ├── model/
│   │   ├── api/
│   │   ├── lib/
│   │   └── index.ts
│   └── notification/
│       ├── ui/
│       ├── model/
│       ├── api/
│       └── index.ts
│
├── shared/
│   ├── api/
│   │   ├── client/
│   │   └── index.ts
│   ├── ui/
│   ├── lib/
│   │   ├── dates/
│   │   ├── validation/
│   │   └── browser/
│   ├── config/
│   ├── routes/
│   ├── i18n/
│   └── assets/
│
└── main.tsx
```

Не создавать пустые слои и сегменты «на будущее». Если проекту не нужен `widgets` или у конкретного slice нет `api`, такой каталог создавать не требуется.

---

## 16.2. Направление зависимостей

Базовое направление:

```text
app
 ↓
pages
 ↓
widgets
 ↓
features
 ↓
entities
 ↓
shared
```

Модуль внутри slice может импортировать другой slice только со слоя, расположенного **строго ниже**.

Разрешено:

```text
pages   -> widgets
pages   -> features
pages   -> entities
pages   -> shared

widgets -> features
widgets -> entities
widgets -> shared

features -> entities
features -> shared

entities -> shared
```

Запрещено:

```text
shared   -> entities
shared   -> features
shared   -> widgets
shared   -> pages
shared   -> app

entities -> features
entities -> widgets
entities -> pages
entities -> app

features -> widgets
features -> pages
features -> app

widgets  -> pages
widgets  -> app

pages    -> app
```

### Соседние slices одного слоя

По умолчанию slices одного слоя должны быть изолированы друг от друга.

Запрещено:

```ts
// features/create-order/... 
import { deleteOrder } from '@/features/delete-order/model/deleteOrder';
```

Также по умолчанию не делать:

```text
entities/user -> entities/organization
features/login -> features/logout
widgets/header -> widgets/sidebar
```

Если нескольким slices нужен общий код, сначала определить его реальную ответственность и переместить его на подходящий нижний слой.

Для редких явно связанных entity допускается официальный FSD-механизм `@x` cross-reference API, но разработчик **не должен вводить `@x` автоматически**. Сначала предпочитать композицию на `features`, `widgets` или `pages`.

---

## 16.3. Назначение слоёв

### `app`

Глобальная инфраструктура приложения:

```text
app/providers
app/router
app/styles
app/config
```

Здесь допустимы:

- инициализация React;
- `MaxUI` provider;
- router;
- глобальные providers;
- глобальная конфигурация store;
- глобальные CSS-файлы;
- глобальная аналитика и инициализация приложения.

Не переносить сюда локальную бизнес-логику feature/entity.

Пример интеграции MAX UI:

```tsx
// src/app/providers/AppProviders.tsx
import type { PropsWithChildren } from 'react';
import { MaxUI } from '@maxhub/max-ui';

export function AppProviders({ children }: PropsWithChildren) {
  return <MaxUI resetBody>{children}</MaxUI>;
}
```

Подключение CSS пакета и глобальных overrides должно выполняться один раз на уровне entrypoint/app:

```tsx
import '@maxhub/max-ui/dist/styles.css';
import '@/app/styles/index.css';
```

### `pages`

Полные экраны приложения, готовые к подключению к router.

Page может собирать нижние слои:

```text
widgets
features
entities
shared
```

Если блок используется только на одной странице и не представляет самостоятельную переиспользуемую feature/widget, его допустимо оставить внутри page.

Не дробить страницу на widgets только ради соблюдения структуры.

### `widgets`

Крупные самостоятельные UI-блоки, обычно объединяющие несколько entities/features.

Примеры:

```text
widgets/header
widgets/navigation
widgets/profile-summary
widgets/notification-panel
```

Widget нужен, когда блок имеет самостоятельный смысл или переиспользуется. Если блок занимает основную часть единственной страницы и больше нигде не нужен, оставить его в `pages`.

### `features`

Значимые пользовательские взаимодействия.

Хорошие названия:

```text
auth-by-password
change-theme
edit-profile
send-message
create-order
delete-order
mark-notification-read
```

Feature должна отвечать на вопрос:

```text
Что пользователь может сделать?
```

Не превращать каждую кнопку или маленький обработчик в отдельную feature. Feature должна представлять значимый сценарий, особенно если он используется в нескольких местах.

### `entities`

Бизнес-сущности приложения.

Примеры:

```text
user
notification
message
organization
order
```

Entity отвечает на вопрос:

```text
Что существует в предметной области приложения?
```

Внутри entity могут находиться:

```text
ui
model
api
lib
```

Например:

```text
entities/user/
├── api/
├── model/
├── ui/
└── index.ts
```

### `shared`

Общая техническая основа приложения и интеграции с внешним миром.

Типичные сегменты:

```text
shared/api
shared/ui
shared/lib
shared/config
shared/routes
shared/i18n
shared/assets
```

Не использовать `shared` как мусорную папку для всего переиспользуемого кода.

В рамках этого проекта действует более строгая договорённость: если модуль выражает конкретную бизнес-сущность или пользовательский сценарий, хранить его в `entities`/`features`, а не переносить в `shared` только потому, что он используется в нескольких местах.

---

## 16.4. Сегменты

Основные сегменты:

```text
ui
api
model
lib
config
```

Смысл:

```text
ui      — отображение, React-компоненты, связанные стили
api     — запросы, DTO, mapper'ы и взаимодействие с backend
model   — состояние, схемы, интерфейсы, stores, бизнес-логика slice
lib     — небольшие внутренние библиотеки slice с понятной областью ответственности
config  — конфигурация и feature flags конкретного slice
```

Названия сегментов должны описывать **назначение**, а не тип файлов.

Не создавать без необходимости сегменты:

```text
components
hooks
types
helpers
utils
common
misc
other
services
```

Например, вместо:

```text
shared/utils/date.ts
```

предпочитать:

```text
shared/lib/dates/formatDate.ts
```

Вместо:

```text
features/auth/hooks/useLogin.ts
```

предпочитать:

```text
features/auth-by-password/model/useLogin.ts
```

если hook является частью модели сценария.

---

## 16.5. Public API каждого slice

Каждый slice должен предоставлять публичный API через `index.ts`.

Пример:

```text
entities/user/
├── ui/
│   └── UserAvatar.tsx
├── model/
│   └── types.ts
└── index.ts
```

```ts
// entities/user/index.ts
export { UserAvatar } from './ui/UserAvatar';
export type { User } from './model/types';
```

Использование снаружи:

```ts
import { UserAvatar, type User } from '@/entities/user';
```

Не делать deep import во внутренности чужого slice:

```ts
import { UserAvatar } from '@/entities/user/ui/UserAvatar';
import type { User } from '@/entities/user/model/types';
```

Внутри самого slice локальные относительные импорты допустимы.

Public API должен экспортировать только то, что реально требуется внешним consumers. Не превращать `index.ts` в экспорт всех внутренних файлов.

---

## 16.6. MAX UI внутри FSD

`@maxhub/max-ui` является внешним UI-kit. FSD не требует копировать его компоненты в `shared/ui`.

Правильно:

```tsx
import { Button, Input, Typography } from '@maxhub/max-ui';
```

Если нужен проектный компонент, построенный поверх MAX UI, определить его ответственность.

### Универсальный проектный primitive

Например единый `AppError`, `EmptyState` или специализированный layout, не знающий бизнес-сущностей:

```text
shared/ui/empty-state
```

### Представление бизнес-сущности

Например:

```text
entities/user/ui/UserAvatar
entities/notification/ui/NotificationItem
```

### Пользовательское действие

Например:

```text
features/logout/ui/LogoutButton
features/change-theme/ui/ThemeSwitch
```

### Крупный блок

Например:

```text
widgets/profile-summary/ui/ProfileSummary
```

### Экран

Например:

```text
pages/profile/ui/ProfilePage
```

разработчик не должен создавать wrapper над каждым компонентом MAX UI без необходимости.

Плохо:

```text
shared/ui/AppButton -> просто возвращает <Button {...props} />
shared/ui/AppInput  -> просто возвращает <Input {...props} />
```

Такой wrapper допустим только при наличии реального проектного контракта: собственные defaults, accessibility-политика, расширенное поведение или стабильная абстракция, которая нужна приложению.

---

## 16.7. Где хранить кастомизацию MAX UI

Глобальные CSS-token overrides MAX UI хранить на уровне приложения, например:

```text
src/app/styles/max-ui.css
```

```css
/* пример расположения; конкретные токены проверять по установленной версии */
:root {
  /* --background-... */
  /* --button-... */
  /* --text-... */
}
```

Не разбрасывать глобальные overrides по `features` и `entities`.

Локальные className/стили, относящиеся только к одному slice, хранить рядом с UI этого slice.

Не использовать внутренние class names MAX UI как стабильный контракт, если этого можно избежать.

---

## 16.8. API и backend

Базовый HTTP-клиент и общую transport-конфигурацию хранить в:

```text
shared/api/client
```

Например:

```text
shared/api/client/http.ts
shared/api/client/errors.ts
shared/api/client/index.ts
```

Запросы конкретной сущности могут находиться в:

```text
entities/user/api
entities/notification/api
```

Запрос, существующий исключительно для пользовательского сценария, допустимо хранить в feature:

```text
features/edit-profile/api
features/logout/api
```

Не создавать единый глобальный файл:

```text
src/services/api.ts
```

со всеми endpoint'ами приложения.

---

## 16.9. Router

Конфигурация router приложения располагается в `app/router` или `app/routes`.

Сами страницы импортируются через их Public API:

```ts
import { HomePage } from '@/pages/home';
import { ProfilePage } from '@/pages/profile';
```

Не импортировать внутренний файл страницы напрямую:

```ts
import { ProfilePage } from '@/pages/profile/ui/ProfilePage';
```

Маршрутные константы, которые нужны во всём приложении, допустимо хранить в:

```text
shared/routes
```

---

## 16.10. Именование

Slices именовать в `kebab-case`:

```text
auth-by-password
change-theme
edit-profile
notification-list
```

React-компоненты:

```text
PascalCase
```

Примеры:

```text
UserAvatar.tsx
ProfilePage.tsx
LogoutButton.tsx
```

Hooks:

```text
useSomething
```

Не использовать бессодержательные имена:

```text
common
misc
other
stuff
helpers
utils
manager
service
```

без чётко определённой области ответственности.

---

## 16.11. Правила для AI-разработчика перед созданием файла

Перед созданием **каждого нового модуля** разработчик должен определить:

```text
1. Какова ответственность кода?
2. Это app, page, widget, feature, entity или shared?
3. Если слой содержит slices — к какому slice относится код?
4. Какой segment соответствует назначению: ui/api/model/lib/config?
5. Не существует ли уже подходящего slice или модуля?
6. Не нарушает ли новый import правило движения только вниз по слоям?
7. Не создаётся ли связь между соседними slices одного слоя?
8. Есть ли у slice Public API?
9. Можно ли использовать существующий MAX UI компонент вместо нового UI primitive?
10. Подтверждён ли API MAX UI TypeScript-типами установленной версии?
```

Если размещение неочевидно, разработчик **не должен автоматически складывать код в `shared`**.

---

## 16.12. Жёсткие запреты для разработчика

Без отдельной архитектурной причины разработчику запрещено создавать в корне `src`:

```text
components/
services/
utils/
helpers/
hooks/
models/
stores/
api/
common/
core/
misc/
types/
```

Запрещено:

- импортировать slice с вышестоящего слоя;
- deep-import'ить внутренние файлы чужого slice;
- напрямую связывать соседние slices одного слоя;
- создавать циклические зависимости;
- переносить бизнес-код в `shared` ради переиспользования;
- создавать wrapper вокруг MAX UI без реальной причины;
- придумывать несуществующие props MAX UI;
- смешивать frontend `onClick` и MAX Bot API callback/webhook;
- проводить массовый рефакторинг структуры без необходимости для текущей задачи;
- создавать абстракции «на будущее»;
- создавать пустые слои/slices/segments только для симметрии дерева.

---

## 16.13. Не создавать абстракции заранее

Не создавать без реальной необходимости:

```text
generic repositories
base services
universal factories
abstract managers
лишние adapters
лишние wrappers
глобальные helpers
глобальные utils
```

Сначала реализовать конкретный сценарий в правильном slice.

Абстракцию выделять после появления фактической общей ответственности, а не предполагаемого будущего переиспользования.

---

## 16.14. Пример декомпозиции страницы профиля

Вместо монолитного:

```text
pages/profile/ui/ProfilePage.tsx
```

с API, logout, theme state и user-моделью внутри одного файла, использовать декомпозицию по ответственности, когда она действительно нужна:

```text
entities/user/
├── model/
│   └── user.ts
├── ui/
│   └── UserAvatar.tsx
└── index.ts

features/change-theme/
├── ui/
│   └── ThemeSwitch.tsx
├── model/
└── index.ts

features/logout/
├── ui/
│   └── LogoutButton.tsx
├── api/
└── index.ts

widgets/profile-summary/
├── ui/
│   └── ProfileSummary.tsx
└── index.ts

pages/profile/
├── ui/
│   └── ProfilePage.tsx
└── index.ts
```

При этом маленький одноразовый блок не нужно насильно выносить из page.

---

## 16.15. Алиас импортов

Для проекта рекомендуется алиас `@/` -> `src/`.

Пример TypeScript:

```json
{
  "compilerOptions": {
    "baseUrl": ".",
    "paths": {
      "@/*": ["src/*"]
    }
  }
}
```

Использовать:

```ts
import { UserAvatar } from '@/entities/user';
import { LogoutButton } from '@/features/logout';
```

Вместо:

```ts
import { UserAvatar } from '../../../../entities/user';
```

Внутри одного slice небольшие относительные импорты допустимы.

---

## 16.16. Проверка перед завершением задачи

Перед завершением изменения frontend разработчик обязан проверить:

```text
[ ] Новый код размещён на корректном FSD-слое.
[ ] Slice имеет понятную бизнес-ответственность.
[ ] Нет импортов вверх по слоям.
[ ] Нет запрещённых импортов между соседними slices.
[ ] Внешние consumers используют Public API slice.
[ ] Нет необоснованного deep import.
[ ] Нет циклической зависимости.
[ ] shared не превратился в dumping ground.
[ ] Не создан лишний wrapper над MAX UI.
[ ] Props MAX UI существуют в установленной версии.
[ ] Для подходящего UI использован MAX UI, а не дублирующий самописный primitive.
[ ] typecheck проходит.
[ ] lint проходит.
```

Если проект содержит тесты, запустить релевантные тесты изменённой области.

---

# 17. Bash-скрипты для создания FSD-структуры

## 17.1. Первичная структура

Файл `scripts/create-fsd.sh`:

```bash
#!/usr/bin/env bash

set -euo pipefail

ROOT="${1:-src}"

echo "Creating FSD structure in: ${ROOT}"

dirs=(
  "${ROOT}/app/providers"
  "${ROOT}/app/router"
  "${ROOT}/app/styles"
  "${ROOT}/app/config"

  "${ROOT}/pages"
  "${ROOT}/widgets"
  "${ROOT}/features"
  "${ROOT}/entities"

  "${ROOT}/shared/api/client"
  "${ROOT}/shared/ui"
  "${ROOT}/shared/lib"
  "${ROOT}/shared/config"
  "${ROOT}/shared/routes"
  "${ROOT}/shared/i18n"
  "${ROOT}/shared/assets"
)

for dir in "${dirs[@]}"; do
  mkdir -p "${dir}"
done

touch "${ROOT}/app/index.ts"
touch "${ROOT}/shared/api/index.ts"
touch "${ROOT}/shared/ui/index.ts"

# Только для сохранения пустых директорий в Git.
find "${ROOT}" -type d -empty -exec touch {}/.gitkeep \;

echo "FSD structure created."

if command -v tree >/dev/null 2>&1; then
  tree "${ROOT}"
else
  find "${ROOT}" -type d | sort
fi
```

Запуск:

```bash
chmod +x scripts/create-fsd.sh
./scripts/create-fsd.sh
```

Или с другим корнем:

```bash
./scripts/create-fsd.sh ./frontend/src
```

> Скрипт создаёт только базовые точки расширения. После появления реального кода ненужные пустые каталоги можно удалить.

## 17.2. Создание slice

Файл `scripts/create-fsd-slice.sh`:

```bash
#!/usr/bin/env bash

set -euo pipefail

if [ "$#" -lt 2 ]; then
  echo "Usage: $0 <layer> <slice> [segments...]"
  echo "Example: $0 features edit-profile ui model api"
  exit 1
fi

LAYER="$1"
SLICE="$2"
shift 2

case "${LAYER}" in
  pages|widgets|features|entities)
    ;;
  *)
    echo "Invalid slice layer: ${LAYER}"
    echo "Allowed: pages, widgets, features, entities"
    exit 1
    ;;
esac

if [[ ! "${SLICE}" =~ ^[a-z0-9]+(-[a-z0-9]+)*$ ]]; then
  echo "Slice name must use kebab-case: ${SLICE}"
  exit 1
fi

BASE="src/${LAYER}/${SLICE}"
mkdir -p "${BASE}"

if [ "$#" -eq 0 ]; then
  SEGMENTS=(ui model)
else
  SEGMENTS=("$@")
fi

for segment in "${SEGMENTS[@]}"; do
  case "${segment}" in
    ui|api|model|lib|config)
      mkdir -p "${BASE}/${segment}"
      touch "${BASE}/${segment}/.gitkeep"
      ;;
    *)
      echo "Unsupported segment: ${segment}"
      echo "Allowed by this generator: ui, api, model, lib, config"
      exit 1
      ;;
  esac
done

touch "${BASE}/index.ts"

echo "Created FSD slice: ${BASE}"

if command -v tree >/dev/null 2>&1; then
  tree "${BASE}"
else
  find "${BASE}" -maxdepth 2 -print | sort
fi
```

Примеры:

```bash
./scripts/create-fsd-slice.sh entities user ui model api
./scripts/create-fsd-slice.sh features logout ui api model
./scripts/create-fsd-slice.sh widgets profile-summary ui
./scripts/create-fsd-slice.sh pages profile ui api
```

---

# 18. Короткий system prompt для coding agent

Можно добавить этот блок в инструкции разработчика проекта:

```text
When working with MAX UI:
- Use @maxhub/max-ui and import @maxhub/max-ui/dist/styles.css once at app entry.
- Detect the installed @maxhub/max-ui version before assuming API compatibility.
- Treat installed TypeScript types and the matching max-messenger/max-ui source tag as the source of truth.
- For 0.5.x prefer Typography.Text over legacy Typography.* groups.
- Never generate Dot, ToolButton, or Avatar.OnlineDot for 0.5.x.
- Use Avatar.Container onlineStatus for online state.
- Use Button variant, not the old mode/appearance API.
- Current Input modes are default and contrast.
- Current Flex/Grid justify value is space-between, not between.
- Radio exists in 0.5.0 and forces type="radio" internally.
- Use asChild for links/router links rendered with MAX UI buttons.
- Do not confuse MAX UI React interactions with MAX Bot API callback/webhook interactions.
- Do not invent props. Verify every uncertain prop against the installed TypeScript declarations.
- Run the project's typecheck/lint after UI changes.

When organizing frontend code with Feature-Sliced Design:
- Use layers app, pages, widgets, features, entities, shared. Do not use the deprecated processes layer for new code.
- A slice may import other slices only from strictly lower layers.
- Do not import neighboring slices on the same layer by default.
- Every slice must expose a Public API through index.ts; external code must not deep-import its internals.
- Put app-wide providers/router/styles in app.
- Put complete routed screens in pages.
- Put large self-contained UI blocks in widgets only when they are meaningful/reused.
- Put meaningful user interactions in features; do not turn every button into a feature.
- Put business concepts in entities.
- Put technical foundation and external integrations in shared; never use shared as a dumping ground.
- Prefer purpose-based segments ui/api/model/lib/config. Avoid generic components/hooks/types/utils/helpers/services folders.
- Do not create wrappers around MAX UI components unless the wrapper provides a real project-level contract.
- Keep global MAX UI token overrides in app/styles; keep slice-specific styles inside the slice.
- Before creating a module, identify layer, slice, segment, dependency direction, and existing Public API.
- Avoid speculative abstractions and mass refactors unrelated to the task.
```

---

# 19. Источники

Официальные источники, использованные при подготовке:

- MAX UI documentation: https://dev.max.ru/ui
- MAX UI GitHub: https://github.com/max-messenger/max-ui
- Current component exports: https://github.com/max-messenger/max-ui/blob/main/src/components/index.ts
- Root exports: https://github.com/max-messenger/max-ui/blob/main/src/index.ts
- Migration guide: https://github.com/max-messenger/max-ui/blob/main/docs/MIGRATION.md
- Changelog: https://github.com/max-messenger/max-ui/blob/main/CHANGELOG.md
- npm package: https://www.npmjs.com/package/@maxhub/max-ui

Feature-Sliced Design:

- Layers and import rule: https://feature-sliced.design/docs/reference/layers
- Slices and segments: https://feature-sliced.design/docs/reference/slices-segments
- Public API: https://feature-sliced.design/docs/reference/public-api

При использовании этого файла позже всегда перепроверяй версию пакета: API UI-kit может измениться после 0.5.0.
