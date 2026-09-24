import { Typography } from '@maxhub/max-ui';

import { HouseInfoCard, useHouseInfo } from '@/entities/geo';
import { AsyncState } from '@/shared/ui';

interface HouseInfoSectionProps {
  houseId: string;
  title?: string;
}

/** "Кто обслуживает дом": the management company and its contacts for `houseId`. */
export function HouseInfoSection({ houseId, title = 'Кто обслуживает дом' }: HouseInfoSectionProps) {
  const info = useHouseInfo(houseId);

  return (
    <section className="app-section">
      <div className="section-title">
        <Typography.Text variant="body-strong" color="primary">
          {title}
        </Typography.Text>
      </div>
      <AsyncState isLoading={info.isLoading} error={info.error} onRetry={() => info.refetch()}>
        {info.data && <HouseInfoCard info={info.data} />}
      </AsyncState>
    </section>
  );
}
