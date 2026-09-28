
import type { ChannelType } from '../model/types';

interface ChannelMeta {
  label: string;
  description: string;
  targetLabel: string | null;
  placeholder: string;
  adminOnly: boolean;
}

export const CHANNEL_META: Record<ChannelType, ChannelMeta> = {
  MAX_MEMBERS: {
    label: 'MAX — лично сотрудникам',
    description: 'Каждому сотруднику организации, который привязал свой MAX, приходит личное сообщение.',
    targetLabel: null,
    placeholder: '',
    adminOnly: false,
  },
  MAX_CHAT: {
    label: 'Чат MAX',
    description: 'Одно сообщение в групповой чат диспетчерской. Добавьте бота в чат администратором и укажите ID чата.',
    targetLabel: 'ID чата',
    placeholder: '-100123456789',
    adminOnly: false,
  },
  EMAIL: {
    label: 'Электронная почта',
    description: 'Письмо на общий адрес диспетчерской или руководителя.',
    targetLabel: 'E-mail',
    placeholder: 'dispatch@uk.ru',
    adminOnly: false,
  },
  WEBHOOK: {
    label: 'Webhook (CRM организации)',
    description: 'JSON-запрос в систему организации. Подпись HMAC-SHA256 в заголовке X-SmartCity-Signature.',
    targetLabel: 'URL',
    placeholder: 'https://crm.uk.ru/smartcity',
    adminOnly: true,
  },
};

export const CHANNEL_TYPES: ChannelType[] = ['MAX_CHAT', 'EMAIL', 'MAX_MEMBERS', 'WEBHOOK'];

export function channelTargetError(type: ChannelType, target: string): string | null {
  const value = target.trim();
  switch (type) {
    case 'MAX_MEMBERS':
      return null;
    case 'MAX_CHAT':
      return /^-?\d+$/.test(value) ? null : 'ID чата — число';
    case 'EMAIL':
      return /^[^\s@]+@[^\s@]+$/.test(value) ? null : 'Укажите адрес электронной почты';
    case 'WEBHOOK':
      return value.startsWith('https://') ? null : 'Адрес должен начинаться с https://';
  }
}
