/**
 * Безопасный экстрактор сообщений об ошибках из различных форматов
 * Поддерживает форматы ошибок от axios и других HTTP-клиентов
 */

/**
 * Извлекает сообщение об ошибке из объекта ошибки
 * Проверяет несколько распространенных форматов:
 * - error.response.data.message
 * - error.response.data.detail
 * - error.message
 * 
 * @param error - Объект ошибки (обычно от axios или fetch)
 * @param fallback - Сообщение по умолчанию, если не удалось извлечь ошибку
 * @returns Извлеченное сообщение об ошибке или fallback
 */
export function extractErrorMessage(error: unknown, fallback: string): string {
  // Проверяем, что error является объектом
  if (!error || typeof error !== 'object') {
    return fallback
  }

  // Проверяем формат axios: error.response.data.message
  if (
    'response' in error &&
    error.response &&
    typeof error.response === 'object' &&
    'data' in error.response &&
    error.response.data &&
    typeof error.response.data === 'object'
  ) {
    const data = error.response.data as Record<string, unknown>
    
    // Проверяем message
    if ('message' in data && typeof data.message === 'string' && data.message) {
      return data.message
    }
    
    // Проверяем detail (используется в некоторых API)
    if ('detail' in data && typeof data.detail === 'string' && data.detail) {
      return data.detail
    }
  }

  // Проверяем прямое свойство message
  if ('message' in error && typeof error.message === 'string' && error.message) {
    return error.message
  }

  return fallback
}

