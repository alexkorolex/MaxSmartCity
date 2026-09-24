import { useState, type FormEvent } from 'react';

import {
  EMPTY_STAFF_ACCOUNT,
  isStaffAccountComplete,
  StaffAccountFields,
  useCreateOrganizationMemberAccount,
  type StaffAccountPayload,
} from '@/entities/organization';
import { apiErrorMessage } from '@/shared/lib';

import './AddOrganizationEmployeeForm.css';

/** Admin creates another employee login directly inside an existing organization. */
export function AddOrganizationEmployeeForm({ organizationId }: { organizationId: string }) {
  const [account, setAccount] = useState<StaffAccountPayload>(EMPTY_STAFF_ACCOUNT);
  const [createdLogin, setCreatedLogin] = useState('');
  const createAccount = useCreateOrganizationMemberAccount(organizationId);

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!isStaffAccountComplete(account)) return;
    createAccount.mutate(
      { ...account, email: account.email?.trim() || null },
      {
        onSuccess: (member) => {
          setCreatedLogin(member.login);
          setAccount(EMPTY_STAFF_ACCOUNT);
        },
      },
    );
  }

  return (
    <form className="add-employee" onSubmit={handleSubmit}>
      <StaffAccountFields
        idPrefix="new-employee"
        value={account}
        onChange={(value) => {
          setAccount(value);
          setCreatedLogin('');
        }}
      />
      {createAccount.isError && <div className="form-error">{apiErrorMessage(createAccount.error)}</div>}
      {createdLogin && (
        <div className="form-success">Сотрудник «{createdLogin}» создан и может войти в панель.</div>
      )}
      <div className="form-actions">
        <button type="submit" className="btn" disabled={!isStaffAccountComplete(account) || createAccount.isPending}>
          {createAccount.isPending ? 'Создаём…' : 'Добавить сотрудника'}
        </button>
      </div>
    </form>
  );
}
