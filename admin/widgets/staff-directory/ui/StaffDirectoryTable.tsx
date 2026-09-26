import { roleLabel } from '@/entities/session';
import { useStaffDirectory } from '@/entities/staff';
import { AsyncState, EmptyState, StaffIcon } from '@/shared/ui';

interface StaffDirectoryTableProps {
  organizationId?: string;
  showOrganization?: boolean;
}

export function StaffDirectoryTable({ organizationId, showOrganization = true }: StaffDirectoryTableProps) {
  const directory = useStaffDirectory(organizationId);
  return (
    <AsyncState isLoading={directory.isLoading} error={directory.error} onRetry={() => void directory.refetch()}>
      {!directory.data || directory.data.length === 0 ? (
        <EmptyState icon={<StaffIcon />} title="Сотрудников не найдено" />
      ) : (
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Сотрудник</th>
                <th>Роль</th>
                {showOrganization && <th>Организация</th>}
              </tr>
            </thead>
            <tbody>
              {directory.data.map((entry) => (
                <tr key={entry.member_id}>
                  <td className="cell-primary" data-label="Сотрудник">{entry.display_name}</td>
                  <td className="cell-secondary" data-label="Роль">{roleLabel(entry.role_code)}</td>
                  {showOrganization && (
                    <td className="cell-secondary" data-label="Организация">{entry.organization_name}</td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </AsyncState>
  );
}
