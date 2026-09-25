import { useState, type FormEvent } from 'react';

import {
  CredentialsEmailNotice,
  EMPTY_STAFF_ACCOUNT,
  isStaffAccountComplete,
  StaffAccountFields,
  useCreateOrganizationMemberAccount,
  type CredentialsEmailResult,
  type StaffAccountPayload,
} from '@/entities/organization';
import { apiErrorMessage } from '@/shared/lib';

import './AddOrganizationEmployeeForm.css';

/** Admin creates another employee login directly inside an existing organization. */
export function AddOrganizationEmployeeForm({ organizationId }: { organizationId: string }) {
  const [account, setAccount] = useState<StaffAccountPayload>(EMPTY_STAFF_ACCOUNT);
  const [created, setCreated] = useState<{ login: string; email: CredentialsEmailResult } | null>(null);
  const createAccount = useCreateOrganizationMemberAccount(organizationId);

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!isStaffAccountComplete(account)) return;
    createAccount.mutate(
      { ...account, email: account.email?.trim() || null },
      {
        onSuccess: (result) => {
          setCreated({ login: result.member.login, email: result.credentials_email });
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
          setCreated(null);
        }}
      />
      {createAccount.isError && <div className="form-error">{apiErrorMessage(createAccount.error)}</div>}
      {created && <CredentialsEmailNotice result={created.email} login={created.login} />}
      <div className="form-actions">
        <button type="submit" className="btn" disabled={!isStaffAccountComplete(account) || createAccount.isPending}>
          {createAccount.isPending ? 'Создаём…' : 'Добавить сотрудника'}
        </button>
      </div>
    </form>
  );
}
