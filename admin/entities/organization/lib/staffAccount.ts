import type { StaffAccountPayload } from '../model/types';

export const MIN_PASSWORD_LENGTH = 8;

export const EMPTY_STAFF_ACCOUNT: StaffAccountPayload = { login: '', password: '', display_name: '', email: '' };

export function isStaffAccountComplete(account: StaffAccountPayload): boolean {
  return (
    Boolean(account.login.trim()) &&
    Boolean(account.display_name.trim()) &&
    account.password.length >= MIN_PASSWORD_LENGTH
  );
}
