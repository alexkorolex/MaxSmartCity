export {
  meQueryKey,
  profileQueryKey,
  useChangePassword,
  useLinkMaxAccount,
  useMe,
  useProfile,
  useStaffInitialPassword,
  useStaffLogin,
  useUnlinkMaxAccount,
  useUpdateProfile,
} from './model/queries';
export type { StaffProfile } from './api/staffAuth';
export type { Principal } from './model/types';
export {
  canBrowseOrganizations,
  canSeeResidentData,
  isAdmin,
  isAuthority,
  primaryRole,
  roleLabel,
  STAFF_ROLES,
} from './model/types';
export { clearSession } from './model/tokenStore';
export { useSession } from './model/useSession';
