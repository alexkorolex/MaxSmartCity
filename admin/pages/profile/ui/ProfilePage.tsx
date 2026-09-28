import { primaryRole, roleLabel, useMe, useProfile } from '@/entities/session';
import { ChangePasswordForm, MaxAccountForm, ProfileDetailsForm } from '@/features/staff-profile';
import { AsyncState } from '@/shared/ui';

import './ProfilePage.css';

export function ProfilePage() {
  const { data: principal } = useMe();
  const profile = useProfile();
  const role = primaryRole(principal);

  return (
    <AsyncState isLoading={profile.isLoading} error={profile.error}>
      {profile.data && (
        <>
          <section className="card profile-summary">
            <div className="profile-summary__avatar" aria-hidden="true">
              {profile.data.display_name.trim().charAt(0).toUpperCase()}
            </div>
            <div className="profile-summary__copy">
              <h1 className="profile-summary__name">{profile.data.display_name}</h1>
              <div className="profile-summary__meta">
                {[role && roleLabel(role), profile.data.organization_name, profile.data.department_name]
                  .filter(Boolean)
                  .join(' · ')}
              </div>
            </div>
          </section>

          <div className="profile-grid">
            <section className="card profile-grid__wide">
              <div className="card__header">
                <div>
                  <div className="card__title">Личные данные</div>
                  <div className="card__meta">Имя видят коллеги и жители в переписке по обращениям</div>
                </div>
              </div>
              <div className="card__body">
                <ProfileDetailsForm key={`${profile.data.display_name}|${profile.data.email}`} profile={profile.data} />
              </div>
            </section>

            <section className="card">
              <div className="card__header">
                <div>
                  <div className="card__title">Пароль</div>
                  <div className="card__meta">Смените временный пароль из письма на свой</div>
                </div>
              </div>
              <div className="card__body">
                <ChangePasswordForm />
              </div>
            </section>

            <section className="card">
              <div className="card__header">
                <div>
                  <div className="card__title">Уведомления в MAX</div>
                  <div className="card__meta">Новые заявки по вашим домам будут приходить вам лично</div>
                </div>
              </div>
              <div className="card__body">
                <MaxAccountForm profile={profile.data} />
              </div>
            </section>
          </div>
        </>
      )}
    </AsyncState>
  );
}
