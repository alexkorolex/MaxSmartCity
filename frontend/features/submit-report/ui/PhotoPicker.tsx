import { Typography } from '@maxhub/max-ui';
import { useRef } from 'react';

import { PlusIcon } from '@/shared/ui';

import type { PendingPhoto } from '../model/usePhotoPicker';

interface PhotoPickerProps {
  photos: PendingPhoto[];
  canAddMore: boolean;
  error: string | null;
  onAdd: (files: FileList | null) => void;
  onRemove: (id: string) => void;
}

export function PhotoPicker({ photos, canAddMore, error, onAdd, onRemove }: PhotoPickerProps) {
  const inputRef = useRef<HTMLInputElement>(null);

  return (
    <div>
      <div className="photo-picker__grid">
        {photos.map((photo) => (
          <div key={photo.id} className="photo-picker__thumb">
            <img src={photo.previewUrl} alt="" />
            <button
              type="button"
              className="photo-picker__remove"
              aria-label="Удалить фото"
              onClick={() => onRemove(photo.id)}
            >
              ✕
            </button>
          </div>
        ))}

        {canAddMore && (
          <button
            type="button"
            className="photo-picker__add"
            aria-label="Добавить фото"
            onClick={() => inputRef.current?.click()}
          >
            <PlusIcon width={22} height={22} />
          </button>
        )}
      </div>

      <input
        ref={inputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        multiple
        hidden
        onChange={(event) => {
          onAdd(event.target.files);
          event.target.value = '';
        }}
      />

      {error ? (
        <Typography.Text variant="note" style={{ color: 'var(--error)' }}>
          {error}
        </Typography.Text>
      ) : (
        <Typography.Text variant="note" className="photo-picker__hint">
          JPEG, PNG или WEBP, до 10 МБ, не более 5 фото
        </Typography.Text>
      )}
    </div>
  );
}
