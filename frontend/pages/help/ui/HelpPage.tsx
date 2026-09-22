import { CellHeader, CellList, CellSimple, Typography } from '@maxhub/max-ui';

import { PageLayout } from '@/shared/ui';

const FAQ = [
  {
    question: 'Как сообщить о проблеме?',
    answer: 'Откройте раздел «Сообщить о проблеме» на главном экране, опишите ситуацию и отправьте обращение.',
  },
  {
    question: 'Как узнать статус моего обращения?',
    answer: 'Статус виден в разделе «Мои обращения». Как только обращение свяжут с инцидентом, вы получите уведомление.',
  },
  {
    question: 'Что делать, если проблему не решили?',
    answer:
      'Когда инцидент переходит в статус «Ожидает подтверждения», в карточке инцидента появится кнопка — вы сможете подтвердить решение или оспорить его.',
  },
  {
    question: 'Как войти в приложение?',
    answer: 'Вход происходит через бота Max Smart City в мессенджере MAX — отдельного логина и пароля не требуется.',
  },
];

export function HelpPage() {
  return (
    <PageLayout title="Помощь и обратная связь">
      <CellList mode="island" header={<CellHeader>Частые вопросы</CellHeader>}>
        {FAQ.map((item) => (
          <CellSimple key={item.question} title={item.question} subtitle={item.answer} subtitleMode="secondary" separator />
        ))}
      </CellList>

      <Typography.Text variant="description" color="secondary">
        Не нашли ответ? Напишите об этом прямо боту Max Smart City в MAX — сообщение увидит служба поддержки.
      </Typography.Text>
    </PageLayout>
  );
}
