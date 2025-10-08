import { useEffect } from 'react'
import { useTranslation } from 'react-i18next'

/**
 * Хук для синхронизации атрибута lang HTML-элемента с текущим языком i18n
 * Обеспечивает правильную работу screen readers и accessibility
 */
export function useDocumentLang() {
  const { i18n } = useTranslation()

  useEffect(() => {
    // Обновляем атрибут lang у HTML элемента при изменении языка
    const htmlElement = document.documentElement
    
    if (htmlElement && i18n.language) {
      htmlElement.setAttribute('lang', i18n.language)
    }

    // Логируем изменение для отладки
    console.log(`[i18n] Document language changed to: ${i18n.language}`)
  }, [i18n.language])
}

