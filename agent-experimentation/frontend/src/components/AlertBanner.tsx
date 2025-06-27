import React from 'react';
import classNames from 'classnames';
import {
  ExclamationTriangleIcon,
  InformationCircleIcon,
  CheckCircleIcon,
  XCircleIcon,
  XMarkIcon,
} from '@heroicons/react/24/outline';

interface AlertBannerProps {
  type: 'success' | 'warning' | 'error' | 'info';
  title: string;
  message?: string;
  dismissible?: boolean;
  onDismiss?: () => void;
  action?: {
    label: string;
    onClick: () => void;
  };
}

const alertConfig = {
  success: {
    bgColor: 'bg-success-50',
    borderColor: 'border-success-200',
    textColor: 'text-success-800',
    titleColor: 'text-success-900',
    icon: CheckCircleIcon,
    iconColor: 'text-success-600',
  },
  warning: {
    bgColor: 'bg-warning-50',
    borderColor: 'border-warning-200',
    textColor: 'text-warning-800',
    titleColor: 'text-warning-900',
    icon: ExclamationTriangleIcon,
    iconColor: 'text-warning-600',
  },
  error: {
    bgColor: 'bg-danger-50',
    borderColor: 'border-danger-200',
    textColor: 'text-danger-800',
    titleColor: 'text-danger-900',
    icon: XCircleIcon,
    iconColor: 'text-danger-600',
  },
  info: {
    bgColor: 'bg-primary-50',
    borderColor: 'border-primary-200',
    textColor: 'text-primary-800',
    titleColor: 'text-primary-900',
    icon: InformationCircleIcon,
    iconColor: 'text-primary-600',
  },
};

const AlertBanner: React.FC<AlertBannerProps> = ({
  type,
  title,
  message,
  dismissible = false,
  onDismiss,
  action,
}) => {
  const config = alertConfig[type];
  const Icon = config.icon;

  return (
    <div
      className={classNames(
        'rounded-md border p-4 mb-4',
        config.bgColor,
        config.borderColor
      )}
    >
      <div className="flex">
        <div className="flex-shrink-0">
          <Icon className={classNames('h-5 w-5', config.iconColor)} />
        </div>
        <div className="ml-3 flex-1">
          <h3 className={classNames('text-sm font-medium', config.titleColor)}>
            {title}
          </h3>
          {message && (
            <div className={classNames('mt-2 text-sm', config.textColor)}>
              <p>{message}</p>
            </div>
          )}
          {action && (
            <div className="mt-3">
              <button
                type="button"
                className={classNames(
                  'text-sm font-medium underline hover:no-underline',
                  config.textColor
                )}
                onClick={action.onClick}
              >
                {action.label}
              </button>
            </div>
          )}
        </div>
        {dismissible && onDismiss && (
          <div className="ml-auto pl-3">
            <div className="-mx-1.5 -my-1.5">
              <button
                type="button"
                className={classNames(
                  'inline-flex rounded-md p-1.5 hover:bg-opacity-20 focus:outline-none focus:ring-2 focus:ring-offset-2',
                  config.textColor,
                  `hover:bg-${type}-500`,
                  `focus:ring-${type}-600`
                )}
                onClick={onDismiss}
              >
                <span className="sr-only">Dismiss</span>
                <XMarkIcon className="h-5 w-5" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default AlertBanner;