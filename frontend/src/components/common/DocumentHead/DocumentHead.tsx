import { useEffect } from 'react'
import { useTranslation } from 'react-i18next'

/**
 * Компонент для динамического обновления заголовка документа
 * Обновляет <title> в зависимости от текущего языка
 */
export default function DocumentHead() {
  const { t, i18n } = useTranslation()

  useEffect(() => {
    // Обновляем заголовок документа при изменении языка
    const title = t('common.document_title', 'Everis - Система управления продажами')
    document.title = title

    // Логируем изменение для отладки
    console.log(`[i18n] Document title changed to: ${title}`)
  }, [i18n.language, t])

  // Этот компонент не рендерит ничего в DOM
  return null
}

