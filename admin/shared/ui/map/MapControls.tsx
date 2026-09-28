import { Maximize, Minus, Plus } from 'lucide-react';
import { useEffect, useRef, type ReactNode } from 'react';

import { cn } from '@/shared/lib';

import { useMap } from './context';

const ANIMATION_MS = 300;

function ControlGroup({ children }: { children: ReactNode }) {
  return (
    <div className="border-border bg-background [&>button:not(:last-child)]:border-border flex flex-col overflow-hidden rounded-md border shadow-sm [&>button:not(:last-child)]:border-b">
      {children}
    </div>
  );
}

function ControlButton({ onClick, label, children }: { onClick: () => void; label: string; children: ReactNode }) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={label}
      title={label}
      className={cn(
        'flex size-8 items-center justify-center transition-colors',
        'first:rounded-t-md last:rounded-b-md',
        'hover:bg-accent dark:hover:bg-accent/40',
        'focus-visible:ring-ring focus-visible:ring-2 focus-visible:outline-none focus-visible:ring-inset',
      )}
    >
      {children}
    </button>
  );
}

function CompassIcon() {
  const { map } = useMap();
  const iconRef = useRef<SVGSVGElement>(null);

  useEffect(() => {
    const icon = iconRef.current;
    if (!map || !icon) return;
    const rotate = () => {
      icon.style.transform = `rotateX(${map.getPitch()}deg) rotateZ(${-map.getBearing()}deg)`;
    };
    map.on('rotate', rotate);
    map.on('pitch', rotate);
    rotate();
    return () => {
      map.off('rotate', rotate);
      map.off('pitch', rotate);
    };
  }, [map]);

  return (
    <svg ref={iconRef} viewBox="0 0 24 24" className="size-5" style={{ transformStyle: 'preserve-3d' }}>
      <path d="M12 2L16 12H12V2Z" className="fill-red-500" />
      <path d="M12 2L8 12H12V2Z" className="fill-red-300" />
      <path d="M12 22L16 12H12V22Z" className="fill-muted-foreground/60" />
      <path d="M12 22L8 12H12V22Z" className="fill-muted-foreground/30" />
    </svg>
  );
}

export function MapControls({ className }: { className?: string }) {
  const { map } = useMap();

  const zoomBy = (delta: number) => map?.zoomTo(map.getZoom() + delta, { duration: ANIMATION_MS });
  const resetNorth = () => map?.resetNorthPitch({ duration: ANIMATION_MS });
  const toggleFullscreen = () => {
    if (document.fullscreenElement) {
      void document.exitFullscreen();
    } else {
      void map?.getContainer().requestFullscreen();
    }
  };

  return (
    <div className={cn('absolute right-2 bottom-10 z-10 flex flex-col gap-1.5', className)}>
      <ControlGroup>
        <ControlButton onClick={() => zoomBy(1)} label="Приблизить">
          <Plus className="size-4" />
        </ControlButton>
        <ControlButton onClick={() => zoomBy(-1)} label="Отдалить">
          <Minus className="size-4" />
        </ControlButton>
      </ControlGroup>
      <ControlGroup>
        <ControlButton onClick={resetNorth} label="Повернуть на север">
          <CompassIcon />
        </ControlButton>
      </ControlGroup>
      <ControlGroup>
        <ControlButton onClick={toggleFullscreen} label="Во весь экран">
          <Maximize className="size-4" />
        </ControlButton>
      </ControlGroup>
    </div>
  );
}
