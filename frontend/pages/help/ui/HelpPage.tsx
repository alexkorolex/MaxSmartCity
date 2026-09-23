import { Flex, Typography } from '@maxhub/max-ui';

import { ROUTES } from '@/shared/routes';
import { HelpIcon, PageLayout } from '@/shared/ui';

const FAQ = [
  {
    question: 'Как сообщить о проблеме?',
    answer: 'На главной нажмите «Сообщить о проблеме», опишите ситуацию и отправьте обращение.',
  },
  {
    question: 'Где посмотреть статус?',
    answer: 'Все этапы видны в разделе «Обращения». Об изменениях мы сообщим в уведомлениях.',
  },
  {
    question: 'Что делать, если проблему не решили?',
    answer: 'В карточке инцидента можно не подтвердить решение и пояснить, что осталось исправить.',
  },
  {
    question: 'Как войти в приложение?',
    answer: 'Через бота Max Smart City в MAX. Отдельный логин или пароль не нужен.',
  },
];

function FaqItem({ question, answer }: { question: string; answer: string }) {
  return (
    <details className="faq-item">
      <summary>{question}<span aria-hidden="true">+</span></summary>
      <Typography.Text asChild variant="description" color="secondary">
        <p>{answer}</p>
      </Typography.Text>
    </details>
  );
}

export function HelpPage() {
  return (
    <PageLayout title="Помощь" subtitle="Ответы на частые вопросы" backTo={ROUTES.profile} withNavSpacing={false}>
      <section className="surface-card faq-list">
        {FAQ.map((item) => <FaqItem key={item.question} {...item} />)}
      </section>
      <Flex direction="column" align="center" gap="var(--space-2)" className="surface-card support-card">
        <span className="empty-state__icon support-card__icon"><HelpIcon width={24} /></span>
        <Typography.Text variant="body-strong" color="primary">Нужна помощь человека?</Typography.Text>
        <Typography.Text variant="description" color="secondary">
          Напишите боту Max Smart City в MAX — сообщение увидит служба поддержки.
        </Typography.Text>
      </Flex>
    </PageLayout>
  );
}
