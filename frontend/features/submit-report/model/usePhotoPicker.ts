import { useEffect, useRef, useState } from 'react';

const MAX_SIZE_BYTES = 10 * 1024 * 1024;
const ALLOWED_TYPES = ['image/jpeg', 'image/png', 'image/webp'];
const MAX_PHOTOS = 5;

export interface PendingPhoto {
  id: string;
  file: File;
  previewUrl: string;
}

export function usePhotoPicker() {
  const [photos, setPhotos] = useState<PendingPhoto[]>([]);
  const [error, setError] = useState<string | null>(null);
  const photosRef = useRef(photos);
  photosRef.current = photos;

  useEffect(
    () => () => {
      for (const photo of photosRef.current) URL.revokeObjectURL(photo.previewUrl);
    },
    [],
  );

  const addFiles = (fileList: FileList | null) => {
    if (!fileList || fileList.length === 0) return;
    setError(null);

    const accepted: PendingPhoto[] = [];
    let rejectionReason: string | null = null;

    for (const file of Array.from(fileList)) {
      if (photos.length + accepted.length >= MAX_PHOTOS) {
        rejectionReason = `Можно прикрепить не более ${MAX_PHOTOS} фото`;
        break;
      }
      if (!ALLOWED_TYPES.includes(file.type)) {
        rejectionReason = 'Поддерживаются только JPEG, PNG и WEBP';
        continue;
      }
      if (file.size > MAX_SIZE_BYTES) {
        rejectionReason = 'Файл больше 10 МБ — выберите файл поменьше';
        continue;
      }
      accepted.push({ id: crypto.randomUUID(), file, previewUrl: URL.createObjectURL(file) });
    }

    if (accepted.length > 0) setPhotos((prev) => [...prev, ...accepted]);
    if (rejectionReason) setError(rejectionReason);
  };

  const removePhoto = (id: string) => {
    setPhotos((prev) => {
      const target = prev.find((photo) => photo.id === id);
      if (target) URL.revokeObjectURL(target.previewUrl);
      return prev.filter((photo) => photo.id !== id);
    });
  };

  const reset = () => {
    for (const photo of photos) URL.revokeObjectURL(photo.previewUrl);
    setPhotos([]);
  };

  return { photos, addFiles, removePhoto, reset, error, canAddMore: photos.length < MAX_PHOTOS };
}
