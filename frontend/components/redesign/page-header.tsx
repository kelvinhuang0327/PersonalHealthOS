import { ReactNode } from 'react';
import { Card } from '../../app/components/ui/card';
import { cn } from '../../app/components/ui/utils';

export function PageHeader({
  label,
  title,
  description,
  aside,
  className,
}: {
  label: string;
  title: string;
  description: string;
  aside?: ReactNode;
  className?: string;
}) {
  return (
    <Card className={cn('rounded-[28px] p-6 md:p-7', className)}>
      <div className="flex flex-wrap items-start justify-between gap-5">
        <div className="max-w-3xl">
          <p className="section-label">{label}</p>
          <h2 className="section-title mt-2">{title}</h2>
          <p className="section-subtitle mt-3">{description}</p>
        </div>
        {aside ? <div className="min-w-[260px] flex-1 md:max-w-sm">{aside}</div> : null}
      </div>
    </Card>
  );
}
