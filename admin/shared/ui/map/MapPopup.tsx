import { X } from 'lucide-react';
import * as MapLibreGL from 'maplibre-gl';
import { useEffect, useMemo, useRef, type ReactNode } from 'react';
import { createPortal } from 'react-dom';

import { cn } from '@/shared/lib';

import { useMap } from './context';

const POPUP_OFFSET = 16;

type MapPopupProps = {
  longitude: number;
  latitude: number;
  onClose?: () => void;
  className?: string;
  children: ReactNode;
};

export function MapPopup({ longitude, latitude, onClose, className, children }: MapPopupProps) {
  const { map } = useMap();
  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;
  const container = useMemo(() => document.createElement('div'), []);
  const popup = useMemo(
    () => new MapLibreGL.Popup({ offset: POPUP_OFFSET, closeButton: false }).setMaxWidth('none'),
    [],
  );

  useEffect(() => {
    popup.setLngLat([longitude, latitude]);
  }, [popup, longitude, latitude]);

  useEffect(() => {
    if (!map) return;
    const handleClose = () => onCloseRef.current?.();
    popup.on('close', handleClose);
    popup.setDOMContent(container).addTo(map);
    return () => {
      popup.off('close', handleClose);
      popup.remove();
    };
  }, [map, popup, container]);

  return createPortal(
    <div
      className={cn(
        'bg-popover text-popover-foreground relative rounded-md border p-3 shadow-md',
        'animate-in fade-in-0 zoom-in-95 duration-200 ease-out',
        className,
      )}
    >
      <button
        type="button"
        onClick={() => popup.remove()}
        aria-label="Закрыть"
        className="focus-visible:ring-ring hover:bg-muted text-foreground absolute top-1 right-1 z-10 inline-flex size-5 cursor-pointer items-center justify-center rounded-sm transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-inset"
      >
        <X className="size-3.5" />
      </button>
      {children}
    </div>,
    container,
  );
}
