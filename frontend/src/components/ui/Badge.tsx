import type { SkinStatus } from '@/types';
import { statusClasses, statusLabel } from '@/lib/utils';

interface StatusBadgeProps {
  status: SkinStatus;
}

export function StatusBadge({ status }: StatusBadgeProps) {
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border ${statusClasses(status)}`}
    >
      {statusLabel(status)}
    </span>
  );
}
